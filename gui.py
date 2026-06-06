# Importar torch y easyocr al inicio en el hilo principal para evitar conflictos de DLLs (WinError 1114) con tkinter/customtkinter
try:
    import easyocr
except Exception:
    pass

import os
import sys
import json
import queue
import threading
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

# Importar el script generator para llamar a sus funciones directamente
import generator

class LogStream:
    """Clase para redirigir la salida estándar de sys.stdout a una cola de Tkinter."""
    def __init__(self, log_queue):
        self.log_queue = log_queue
        
    def write(self, text):
        self.log_queue.put(text)
        
    def flush(self):
        pass

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de Ventana
        self.title("TODO PARTES Horizonte - Gestor de Catálogo")
        self.geometry("750x650")
        self.minsize(700, 600)

        # Establecer apariencia oscura y tema naranja
        ctk.set_appearance_mode("dark")
        
        # Crear la cola para la redirección de logs
        self.log_queue = queue.Queue()
        self.stdout_orig = sys.stdout
        self.stderr_orig = sys.stderr

        # Configurar rejilla principal de la ventana
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # El área del log se expande

        # --- CABECERA ---
        self.header_frame = ctk.CTkFrame(self, height=80, corner_radius=0, fg_color="#121216")
        self.header_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 20))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="TODO PARTES HORIZONTE", 
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#ff6a00"
        )
        self.title_label.grid(row=0, column=0, pady=(15, 2))
        
        self.subtitle_label = ctk.CTkLabel(
            self.header_frame, 
            text="Administración y Sincronización del Catálogo Online", 
            font=ctk.CTkFont(size=12, weight="normal"),
            text_color="#a0a0a8"
        )
        self.subtitle_label.grid(row=1, column=0, pady=(0, 15))

        # --- FORMULARIO DE CONFIGURACIÓN ---
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=0)
        self.config_frame.grid_columnconfigure(0, weight=1) # El input de texto se expande
        self.config_frame.grid_columnconfigure(1, weight=0) # El botón tiene tamaño fijo

        # Campo 1: Carpeta de Origen
        self.lbl_origen = ctk.CTkLabel(self.config_frame, text="Carpeta de Origen (Fotos):", font=ctk.CTkFont(weight="bold"))
        self.lbl_origen.grid(row=0, column=0, columnspan=2, sticky="w", padx=15, pady=(12, 2))
        
        self.entry_origen = ctk.CTkEntry(self.config_frame, placeholder_text="Seleccione la carpeta con las fotos...")
        self.entry_origen.grid(row=1, column=0, sticky="ew", padx=(15, 5), pady=(0, 10))
        
        self.btn_origen = ctk.CTkButton(
            self.config_frame, 
            text="Buscar Carpeta", 
            width=130, 
            fg_color="#ff6a00", 
            hover_color="#e05e00",
            font=ctk.CTkFont(weight="bold"),
            command=self.browse_origen_folder
        )
        self.btn_origen.grid(row=1, column=1, sticky="e", padx=(5, 15), pady=(0, 10))

        # Campo 2: Número de WhatsApp
        self.lbl_whatsapp = ctk.CTkLabel(self.config_frame, text="Número de WhatsApp (ej: 584242116375):", font=ctk.CTkFont(weight="bold"))
        self.lbl_whatsapp.grid(row=2, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 2))
        
        self.entry_whatsapp = ctk.CTkEntry(self.config_frame, placeholder_text="Ej: 584242116375")
        self.entry_whatsapp.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 10))

        # Campo 3: Logotipo de la Empresa
        self.lbl_logo = ctk.CTkLabel(self.config_frame, text="Logotipo de la Empresa (Opcional):", font=ctk.CTkFont(weight="bold"))
        self.lbl_logo.grid(row=4, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 2))
        
        self.entry_logo = ctk.CTkEntry(self.config_frame, placeholder_text="Seleccione el archivo del logo (PNG, JPG)...")
        self.entry_logo.grid(row=5, column=0, sticky="ew", padx=(15, 5), pady=(0, 15))
        
        self.btn_logo = ctk.CTkButton(
            self.config_frame, 
            text="Seleccionar Logo", 
            width=130, 
            fg_color="#ff6a00", 
            hover_color="#e05e00",
            font=ctk.CTkFont(weight="bold"),
            command=self.browse_logo_file
        )
        self.btn_logo.grid(row=5, column=1, sticky="e", padx=(5, 15), pady=(0, 15))


        # --- ÁREA DE CONSOLA / LOGS ---
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=20)
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(1, weight=1)

        self.lbl_log = ctk.CTkLabel(self.log_frame, text="Consola de Sincronización y Salida:", font=ctk.CTkFont(weight="bold"))
        self.lbl_log.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))

        self.txt_log = ctk.CTkTextbox(self.log_frame, fg_color="#0a0a0c", border_color="#1c1c24", border_width=1)
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.txt_log.configure(state="disabled")

        # --- PANEL DE BOTONES ---
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.actions_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_save = ctk.CTkButton(
            self.actions_frame, 
            text="Guardar Ajustes", 
            height=45,
            fg_color="#2b2b36",
            hover_color="#3d3d4d",
            command=self.save_config
        )
        self.btn_save.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.btn_clear = ctk.CTkButton(
            self.actions_frame, 
            text="Eliminar Catálogo Viejo", 
            height=45,
            fg_color="#d9534f",
            hover_color="#c9302c",
            font=ctk.CTkFont(weight="bold"),
            command=self.clear_old_catalog
        )
        self.btn_clear.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.btn_generate = ctk.CTkButton(
            self.actions_frame, 
            text="Generar Catálogo (Procesar)", 
            height=45,
            fg_color="#ff6a00", 
            hover_color="#e05e00",
            font=ctk.CTkFont(weight="bold"),
            command=self.start_catalog_generation
        )
        self.btn_generate.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.btn_publish = ctk.CTkButton(
            self.actions_frame, 
            text="Publicar en GitHub Pages", 
            height=45,
            fg_color="#25d366", 
            hover_color="#1f9c4d",
            font=ctk.CTkFont(weight="bold"),
            command=self.start_github_publish
        )
        self.btn_publish.grid(row=1, column=1, padx=5, pady=5, sticky="ew")


        # Cargar valores guardados al iniciar
        self.load_config_values()

        # Iniciar polling de la cola de logs
        self.update_log_widget()

    # --- CONTROL DE ARCHIVOS Y CARPETAS ---
    def browse_origen_folder(self):
        folder = filedialog.askdirectory(title="Seleccionar Carpeta Origen de Fotos")
        if folder:
            self.entry_origen.delete(0, tk.END)
            self.entry_origen.insert(0, os.path.normpath(folder))

    def browse_logo_file(self):
        file = filedialog.askopenfilename(
            title="Seleccionar Imagen de Logotipo",
            filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
        )
        if file:
            self.entry_logo.delete(0, tk.END)
            self.entry_logo.insert(0, os.path.normpath(file))

    def clear_old_catalog(self):
        from tkinter import messagebox
        if messagebox.askyesno("Eliminar Catálogo Viejo", "¿Estás seguro de que deseas eliminar el catálogo actual?\n\nEsto borrará la base de datos (products.js) y todas las imágenes procesadas (.webp) de la carpeta web, forzando una reconstrucción completa en la próxima generación."):
            try:
                js_path = Path("web/products.js")
                if js_path.exists():
                    os.remove(js_path)
                
                assets_dir = Path("web/assets")
                if assets_dir.exists():
                    for item in assets_dir.iterdir():
                        # Conservar el logo si existe y no borrar la carpeta
                        if item.is_file() and not item.name.startswith("logo."):
                            os.remove(item)
                            
                self.write_to_log("Catálogo viejo eliminado correctamente.\nSe borraron la base de datos y los archivos WebP locales.\nListo para una reconstrucción completa.\n")
                messagebox.showinfo("Éxito", "El catálogo viejo ha sido eliminado correctamente.")
            except Exception as e:
                self.write_to_log(f"Error al limpiar el catálogo: {e}\n")
                messagebox.showerror("Error", f"No se pudo limpiar el catálogo: {e}")

    # --- LECTURA Y ESCRITURA DE AJUSTES ---
    def load_config_values(self):
        config = generator.load_config()
        self.entry_origen.insert(0, config.get("catalogo_origen_path", ""))
        self.entry_whatsapp.insert(0, config.get("whatsapp_number", ""))
        self.entry_logo.insert(0, config.get("logo_path", ""))
        self.write_to_log("Configuración cargada correctamente.\n")

    def save_config(self, show_msg=True):
        config = {
            "catalogo_origen_path": self.entry_origen.get().strip(),
            "whatsapp_number": self.entry_whatsapp.get().strip(),
            "logo_path": self.entry_logo.get().strip()
        }
        
        # Guardar en config.json
        try:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            if show_msg:
                self.write_to_log("Ajustes guardados correctamente en config.json\n")
            return True
        except Exception as e:
            self.write_to_log(f"Error al guardar la configuración: {e}\n")
            return False

    # --- SISTEMA DE LOGS ---
    def write_to_log(self, text):
        self.txt_log.configure(state="normal")
        self.txt_log.insert(tk.END, text)
        self.txt_log.see(tk.END)
        self.txt_log.configure(state="disabled")

    def update_log_widget(self):
        """Pulla la cola de logs y actualiza la interfaz de forma segura."""
        while not self.log_queue.empty():
            try:
                text = self.log_queue.get_nowait()
                self.write_to_log(text)
            except queue.Empty:
                break
        # Volver a llamar a esta función en 100ms
        self.after(100, self.update_log_widget)

    # --- PROCESAMIENTO EN SEGUNDO PLANO ---
    def start_catalog_generation(self):
        # Guardar configuración antes de correr
        if not self.save_config(show_msg=False):
            return

        # Desactivar botones para evitar ejecuciones concurrentes
        self.btn_generate.configure(state="disabled", text="Procesando...")
        self.btn_clear.configure(state="disabled")
        self.btn_publish.configure(state="disabled")
        self.btn_save.configure(state="disabled")

        self.write_to_log("\n===================================================\n")
        self.write_to_log("INICIANDO PROCESAMIENTO DE IMÁGENES Y OCR...\n")
        self.write_to_log("===================================================\n")

        # Redirigir la salida estándar de Python a la interfaz
        sys.stdout = LogStream(self.log_queue)
        sys.stderr = LogStream(self.log_queue)

        # Iniciar el hilo del generador
        thread = threading.Thread(target=self.run_generation)
        thread.daemon = True
        thread.start()

    def run_generation(self):
        try:
            # Ejecutar el generador directamente cargado en memoria
            generator.sync_catalog()
        except Exception as e:
            print(f"\nERROR durante la ejecución: {e}")
        finally:
            # Restaurar salida estándar
            sys.stdout = self.stdout_orig
            sys.stderr = self.stderr_orig
            
            # Reactivar la UI en el hilo principal
            self.after(0, self.finish_generation)

    def finish_generation(self):
        self.btn_generate.configure(state="normal", text="Generar Catálogo (Procesar)")
        self.btn_clear.configure(state="normal")
        self.btn_publish.configure(state="normal")
        self.btn_save.configure(state="normal")
        self.write_to_log("\n===================================================\n")
        self.write_to_log("PROCESO TERMINADO EN LOCAL.\n")
        self.write_to_log("===================================================\n")

    # --- PUBLICACIÓN EN GITHUB EN SEGUNDO PLANO ---
    def start_github_publish(self):
        # Verificar si Git está inicializado
        if not os.path.exists("web/.git"):
            self.write_to_log("\n[ERROR] Git no está inicializado en la carpeta 'web'.\n")
            self.write_to_log("Por favor, realiza la configuración inicial de Git detallada en walkthrough.md antes de subir.\n")
            return

        self.btn_generate.configure(state="disabled")
        self.btn_clear.configure(state="disabled")
        self.btn_publish.configure(state="disabled", text="Publicando...")
        self.btn_save.configure(state="disabled")

        self.write_to_log("\n===================================================\n")
        self.write_to_log("SUBIENDO ACTUALIZACIONES A GITHUB PAGES...\n")
        self.write_to_log("===================================================\n")

        thread = threading.Thread(target=self.run_publish)
        thread.daemon = True
        thread.start()

    def run_publish(self):
        try:
            # Comandos git a ejecutar de forma segura secuencialmente
            # cd web & git add . & git commit -m "..." & git push origin main
            commands = [
                ["git", "add", "."],
                ["git", "commit", "-m", "Actualizacion desde Administrador de Catalogo"],
                ["git", "push", "origin", "main", "--force"]
            ]
            
            web_path = os.path.abspath("web")
            
            for cmd in commands:
                self.log_queue.put(f"Ejecutando: {' '.join(cmd)}\n")
                process = subprocess.Popen(
                    cmd, 
                    cwd=web_path, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True,
                    shell=True # Necesario en Windows para resolver variables y PATH de Git
                )
                stdout, stderr = process.communicate()
                
                if stdout.strip():
                    self.log_queue.put(f"{stdout}\n")
                if stderr.strip() and process.returncode != 0: # Mostrar stderrs solo si hay error
                    self.log_queue.put(f"[Alerta/Error]: {stderr}\n")
                
                if process.returncode != 0:
                    # Si falla un comando (por ejemplo, si no hay cambios que guardar), el push continúa si es posible
                    if cmd[1] == "commit" and "nothing to commit" in stdout + stderr:
                        self.log_queue.put("No hay cambios nuevos para guardar en el commit.\n")
                    else:
                        self.log_queue.put(f"El comando falló con código {process.returncode}\n")
                        
        except Exception as e:
            self.log_queue.put(f"\nERROR al publicar en GitHub: {e}\n")
        finally:
            self.after(0, self.finish_publish)

    def finish_publish(self):
        self.btn_generate.configure(state="normal")
        self.btn_clear.configure(state="normal")
        self.btn_publish.configure(state="normal", text="Publicar en GitHub Pages")
        self.btn_save.configure(state="normal")
        self.write_to_log("\n===================================================\n")
        self.write_to_log("PROCESO DE SUBIDA COMPLETADO.\n")
        self.write_to_log("Tu sitio web tardará 1-2 minutos en actualizarse en internet.\n")
        self.write_to_log("===================================================\n")

if __name__ == "__main__":
    app = App()
    app.mainloop()
