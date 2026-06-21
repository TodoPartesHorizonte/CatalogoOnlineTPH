import os
import sys
import json
import queue
import threading
import subprocess
import time
import webbrowser
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory

# Importar el script generator para llamar a sus funciones directamente
import generator

app = Flask(__name__)

# Búfer de logs hilo-seguro para la consola web
class LogBuffer:
    def __init__(self):
        self.queue = queue.Queue()
        
    def write(self, text):
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        elif not isinstance(text, str):
            text = str(text)
        self.queue.put(text)
        
    def flush(self):
        pass
        
    def read_all(self):
        logs = []
        while not self.queue.empty():
            item = self.queue.get()
            if isinstance(item, bytes):
                item = item.decode('utf-8', errors='replace')
            elif not isinstance(item, str):
                item = str(item)
            logs.append(item)
        return "".join(logs)

log_buffer = LogBuffer()

# Redirección dual para mantener salida en terminal y en la web
class DualWrite:
    def __init__(self, original, buffer):
        self.original = original
        self.buffer = buffer
        
    def write(self, text):
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        elif not isinstance(text, str):
            text = str(text)
        
        try:
            self.original.write(text)
        except Exception:
            pass
        
        try:
            self.buffer.write(text)
        except Exception:
            pass
        
    def flush(self):
        try:
            self.original.flush()
        except Exception:
            pass
        try:
            self.buffer.flush()
        except Exception:
            pass

sys.stdout = DualWrite(sys.stdout, log_buffer)
sys.stderr = DualWrite(sys.stderr, log_buffer)

# Variables de estado para operaciones en segundo plano
bg_lock = threading.Lock()
is_syncing = False
is_publishing = False

# Cargar IDs de la última sincronización al iniciar para que persista el filtro
session_newly_added_ids = []
if os.path.exists("last_sync.json"):
    try:
        with open("last_sync.json", "r", encoding="utf-8") as f:
            session_newly_added_ids = json.load(f)
    except Exception:
        pass

# --- FILTROS DE SEGURIDAD (CSRF LOCAL) ---

@app.before_request
def protect_csrf():
    # Bloquear peticiones cruzadas (cross-origin) no autorizadas de modificación
    if request.method in ['POST', 'PUT', 'DELETE']:
        origin = request.headers.get('Origin')
        referer = request.headers.get('Referer')
        
        # 1. Validar cabecera Origin
        if origin:
            if not (origin.startswith('http://127.0.0.1:') or origin.startswith('http://localhost:')):
                print(f"Intento de ataque CSRF bloqueado. Origin: {origin}")
                return jsonify({"success": False, "message": "Acceso cross-origin bloqueado por políticas de seguridad."}), 403
        # 2. Si no hay Origin pero hay Referer, validar Referer
        elif referer:
            if not (referer.startswith('http://127.0.0.1:') or referer.startswith('http://localhost:')):
                print(f"Intento de ataque CSRF bloqueado. Referer: {referer}")
                return jsonify({"success": False, "message": "Acceso cross-origin bloqueado por políticas de seguridad."}), 403

# --- RUTAS DE LA INTERFAZ WEB ---

@app.route('/admin')
def serve_admin_index():
    return send_from_directory('admin', 'index.html')

@app.route('/admin/<path:path>')
def serve_admin_files(path):
    return send_from_directory('admin', path)

# --- ENDPOINTS DE API ---

@app.route('/api/config', methods=['GET'])
def get_config():
    config = generator.load_config()
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def save_config():
    try:
        new_config = request.json
        # Asegurar tipos flotantes para los márgenes OCR
        new_config["ocr_crop_top"] = float(new_config.get("ocr_crop_top", 0.33))
        new_config["ocr_crop_bottom"] = float(new_config.get("ocr_crop_bottom", 0.55))
        
        # Guardar en config.json
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)
            
        # Actualizar rápidamente products.js con los nuevos enlaces
        generator.update_js_links(new_config)
        return jsonify({"success": True, "message": "Ajustes guardados y aplicados directamente en el catálogo."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al guardar configuración: {str(e)}"}), 500

@app.route('/api/browse/folder', methods=['POST'])
def browse_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # Diálogo nativo ejecutado de forma aislada
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        path = filedialog.askdirectory(parent=root, title="Seleccionar Carpeta Origen de Fotos")
        root.destroy()
        
        if path:
            return jsonify({"success": True, "path": os.path.normpath(path)})
        return jsonify({"success": False, "message": "Selección cancelada."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al abrir diálogo: {str(e)}"}), 500

@app.route('/api/browse/file', methods=['POST'])
def browse_file():
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        path = filedialog.askopenfilename(
            parent=root, 
            title="Seleccionar Imagen de Logotipo",
            filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
        )
        root.destroy()
        
        if path:
            return jsonify({"success": True, "path": os.path.normpath(path)})
        return jsonify({"success": False, "message": "Selección cancelada."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al abrir diálogo: {str(e)}"}), 500

@app.route('/api/sync', methods=['POST'])
def run_sync():
    global is_syncing
    with bg_lock:
        if is_syncing:
            return jsonify({"success": False, "message": "Ya se está ejecutando una sincronización."}), 400
        is_syncing = True
        
    print("\n==================================================================")
    print("INICIANDO PROCESAMIENTO DE IMÁGENES Y LECTURA OCR...")
    print("==================================================================\n")
    
    def sync_task():
        global is_syncing, session_newly_added_ids
        try:
            new_ids = generator.sync_catalog()
            with bg_lock:
                session_newly_added_ids = new_ids or []
            try:
                with open("last_sync.json", "w", encoding="utf-8") as f:
                    json.dump(session_newly_added_ids, f)
            except Exception as e:
                print(f"Error al guardar persistencia de nuevos IDs: {e}")
        except Exception as e:
            print(f"\nERROR durante la ejecución: {e}\n")
        finally:
            with bg_lock:
                is_syncing = False
            print("\n==================================================================")
            print("PROCESO LOCAL TERMINADO CORRECTAMENTE.")
            print("==================================================================\n")
            
    threading.Thread(target=sync_task).start()
    return jsonify({"success": True, "message": "Sincronización iniciada."})

@app.route('/api/publish', methods=['POST'])
def run_publish():
    global is_publishing
    with bg_lock:
        if is_publishing:
            return jsonify({"success": False, "message": "Ya se está ejecutando una publicación."}), 400
        is_publishing = True
        
    # Verificar si Git está inicializado
    if not os.path.exists("web/.git"):
        with bg_lock:
            is_publishing = False
        return jsonify({"success": False, "message": "Git no está inicializado en la carpeta 'web'. Revisa la configuración de Git en tu consola."}), 400

    print("\n==================================================================")
    print("SUBIENDO ACTUALIZACIONES A LA NUBE (CLOUDFLARE/GITHUB)...")
    print("==================================================================\n")

    def publish_task():
        global is_publishing
        try:
            commands = [
                ["git", "add", "."],
                ["git", "commit", "-m", "Actualizacion desde Administrador de Catalogo"],
                ["git", "push", "origin", "HEAD:main", "--force"]
            ]
            web_path = os.path.abspath("web")
            
            for cmd in commands:
                print(f"Ejecutando: {' '.join(cmd)}")
                process = subprocess.Popen(
                    cmd, 
                    cwd=web_path, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True
                )
                stdout, stderr = process.communicate()
                
                if stdout.strip():
                    print(stdout)
                if stderr.strip() and process.returncode != 0:
                    print(f"[Error]: {stderr}")
                    
                if process.returncode != 0:
                    if cmd[1] == "commit" and "nothing to commit" in (stdout + stderr):
                        print("No hay cambios nuevos para guardar en el commit.")
                    else:
                        print(f"El comando falló con código {process.returncode}")
                        break
        except Exception as e:
            print(f"\nERROR al publicar en GitHub: {e}\n")
        finally:
            with bg_lock:
                is_publishing = False
            print("\n==================================================================")
            print("PROCESO DE SUBIDA COMPLETADO CON ÉXITO.")
            print("El nuevo catálogo se ha cargado en GitHub. Cloudflare Pages lo actualizará en 1-2 minutos.")
            print("==================================================================\n")

    threading.Thread(target=publish_task).start()
    return jsonify({"success": True, "message": "Publicación iniciada."})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({
        "is_syncing": is_syncing,
        "is_publishing": is_publishing,
        "newly_added_ids": session_newly_added_ids
    })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    return jsonify({"logs": log_buffer.read_all()})

@app.route('/api/products', methods=['GET'])
def get_products():
    data = generator.read_catalog_js()
    products = data.get("products", []) if data else []
    return jsonify({
        "products": products,
        "newly_added_ids": session_newly_added_ids
    })

@app.route('/api/products/save', methods=['POST'])
def save_products():
    try:
        updated_products = request.json
        data = generator.read_catalog_js()
        if not data:
            return jsonify({"success": False, "message": "No se pudo leer la base de datos de productos."}), 400
            
        # Actualizar datos
        data["products"] = updated_products
        data["total_products"] = len(updated_products)
        
        # Re-indexar keywords por si cambiaron las descripciones
        for product in data["products"]:
            product["keywords"] = generator.generate_keywords(product["description"], product["category"])
            
        success = generator.write_catalog_js(data)
        if success:
            return jsonify({"success": True, "message": "Cambios guardados con éxito en products.js."})
        return jsonify({"success": False, "message": "Error al guardar el archivo de catálogo."}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route('/api/products/delete', methods=['POST'])
def delete_product():
    try:
        req = request.json
        product_id = req.get("id")
        category = req.get("category")
        if not product_id or not category:
            return jsonify({"success": False, "message": "Faltan datos del producto."}), 400
            
        success, message = generator.delete_product(product_id, category)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route('/api/clear', methods=['POST'])
def clear_catalog():
    try:
        js_path = Path("web/products.js")
        if js_path.exists():
            os.remove(js_path)
            
        assets_dir = Path("web/assets")
        if assets_dir.exists():
            for item in assets_dir.iterdir():
                # Conservar el logo y no borrar la carpeta
                if item.is_file() and not item.name.startswith("logo."):
                    os.remove(item)
                    
        # Resetear vista previa de ocr
        preview_path = assets_dir / "ocr_crop_preview.jpg"
        if preview_path.exists():
            os.remove(preview_path)
            
        print("Catálogo viejo eliminado correctamente en local.")
        return jsonify({"success": True, "message": "Base de datos y archivos WebP del catálogo eliminados."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al limpiar catálogo: {str(e)}"}), 500

@app.route('/api/preview-ocr', methods=['POST'])
def preview_ocr():
    try:
        config = request.json
        crop_top = float(config.get("ocr_crop_top", 0.33))
        crop_bottom = float(config.get("ocr_crop_bottom", 0.55))
        
        first_img = generator.get_first_product_image()
        if not first_img:
            return jsonify({"success": False, "message": "No se encontraron imágenes en la carpeta origen para la previsualización."})
            
        assets_dir = Path("web/assets")
        assets_dir.mkdir(parents=True, exist_ok=True)
        preview_path = assets_dir / "ocr_crop_preview.jpg"
        
        generator.generate_crop_preview(first_img, crop_top, crop_bottom, preview_path)
        
        # Devolver timestamp para evitar caché del navegador al recargar imagen
        return jsonify({
            "success": True, 
            "url": f"/web-assets/ocr_crop_preview.jpg?t={int(time.time())}"
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Error al generar vista previa: {str(e)}"}), 500

# Servir recursos del catálogo web (para el visor OCR y el editor)
@app.route('/web-assets/<path:path>')
def serve_web_assets(path):
    return send_from_directory('web/assets', path)

# --- AUTO INICIO DEL NAVEGADOR ---
def launch_browser():
    # Pequeño retraso para dar tiempo al servidor Flask a arrancar
    time.sleep(1.0)
    print("\n---------------------------------------------------")
    print("Abriendo Panel de Administración en tu navegador...")
    print("Dirección: http://127.0.0.1:5000/admin")
    print("---------------------------------------------------\n")
    webbrowser.open("http://127.0.0.1:5000/admin")

if __name__ == '__main__':
    # Iniciar el navegador en un hilo separado
    threading.Thread(target=launch_browser, daemon=True).start()
    
    # Iniciar servidor Flask local
    app.run(host='127.0.0.1', port=5000, debug=False)
