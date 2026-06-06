# Importar torch al inicio para evitar conflictos de DLLs en Windows
try:
    import torch
except Exception:
    pass

import os
import json
import re
import shutil
from pathlib import Path
from PIL import Image

# Lista de palabras vacías (stop words) en español para limpiar palabras clave
STOP_WORDS = {
    'DE', 'EL', 'LA', 'PARA', 'CON', 'DEL', 'LOS', 'LAS', 'UN', 'UNA', 'Y', 'O', 
    'A', 'EN', 'POR', 'AL', 'LO', 'SU', 'SUS', 'DEL', 'E', 'SE', 'ESTE', 'ESTA'
}

def load_config():
    """Carga la configuración desde config.json en la raíz del proyecto."""
    default_config = {
        "catalogo_origen_path": "catalogo_origen",
        "whatsapp_number": "584242116375",
        "logo_path": ""
    }
    config_path = Path("config.json")
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Combinar con los valores predeterminados por si faltan campos
                for k, v in default_config.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception as e:
            print(f"Advertencia: No se pudo leer config.json ({e}). Usando valores por defecto.")
            return default_config
    else:
        # Guardar configuración por defecto
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"No se pudo crear config.json por defecto ({e}).")
        return default_config


OCR_READER = None
TESSERACT_AVAILABLE = False
OCR_INITIALIZED = False

def init_ocr():
    """Inicializa los motores OCR bajo demanda para evitar retrasos al abrir la GUI."""
    global OCR_READER, TESSERACT_AVAILABLE, OCR_INITIALIZED
    if OCR_INITIALIZED:
        return
        
    print("Inicializando motores OCR...")
    
    # 1. Intentar cargar EasyOCR
    try:
        import easyocr
        # Inicializa el lector para español e inglés
        OCR_READER = easyocr.Reader(['es', 'en'])
        print("-> EasyOCR cargado correctamente (recomendado).")
    except Exception as e:
        print(f"-> EasyOCR no disponible o con error de inicializacion ({e}). Intentando cargar pytesseract...")

    # 2. Intentar cargar Pytesseract si EasyOCR no está
    if OCR_READER is None:
        try:
            import pytesseract
            # Rutas comunes de Tesseract en Windows
            tess_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Users\Miguel F\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
            ]
            for path in tess_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break
            
            # Probar si funciona ejecutando una versión simple
            pytesseract.get_tesseract_version()
            TESSERACT_AVAILABLE = True
            print("-> Pytesseract (Tesseract OCR) cargado correctamente.")
        except Exception as e:
            print(f"-> Pytesseract no disponible o no configurado en el sistema ({e}).")

    if OCR_READER is None and not TESSERACT_AVAILABLE:
        print("-> ¡ALERTA! No hay ningún motor OCR disponible. El script usará el nombre del archivo como descripción.")
        
    OCR_INITIALIZED = True

def extract_text_from_image(image_path):
    """Extrae texto de la imagen recortando la franja central (33% a 55% de altura) para aislar el título."""
    init_ocr() # Asegurar que los motores estén listos
    if OCR_READER is not None or TESSERACT_AVAILABLE:
        try:
            # Abrir la imagen en memoria y recortar la zona del título central (33% a 55% de altura)
            with Image.open(image_path) as pil_img:
                width, height = pil_img.size
                crop_box = (0, int(height * 0.33), width, int(height * 0.55))
                cropped_img = pil_img.crop(crop_box)
                img_rgb = cropped_img.convert('RGB')
                
                # Convertir a array de numpy (formato RGB)
                import numpy as np
                img_np = np.array(img_rgb)
            
            # 1. Intentar usar EasyOCR
            if OCR_READER is not None:
                results = OCR_READER.readtext(img_np)
                text = " ".join([res[1] for res in results])
                if text.strip():
                    return text
            
            # 2. Intentar usar Pytesseract
            if TESSERACT_AVAILABLE:
                import pytesseract
                text = pytesseract.image_to_string(img_rgb, lang='spa+eng')
                if text.strip():
                    return text
                    
        except Exception as e:
            print(f"Error procesando OCR en zona central de {image_path.name}: {e}")
            
    # Si todo falla, extraer texto básico del nombre del archivo (removiendo UUIDs o extensiones)
    filename = image_path.stem
    clean_name = re.sub(r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}', '', filename)
    clean_name = clean_name.replace('-', ' ').replace('_', ' ').strip()
    return clean_name if clean_name else filename



def clean_text_for_catalog(raw_text, category):
    """Limpia el texto OCR, elimina saltos de línea y normaliza a mayúsculas."""
    if not raw_text:
        return category.upper()
        
    # Reemplazar saltos de línea y tabuladores por espacios
    text = raw_text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # Remover símbolos extraños pero conservar letras, números y guiones/barras
    text = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-\/\.]', ' ', text)
    
    # Colapsar múltiples espacios
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Si contiene un UUID, removerlo. Si la descripción se vuelve vacía, usar la categoría.
    uuid_pattern = r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'
    if re.search(uuid_pattern, text):
        cleaned_from_uuid = re.sub(uuid_pattern, '', text).strip()
        if len(cleaned_from_uuid) < 4:
            return category.upper()
        text = cleaned_from_uuid
    
    # Convertir a mayúsculas
    text = text.upper()
    
    # Si la descripción quedó vacía o es muy corta, usar la categoría
    if len(text) < 4:
        return category.upper()
        
    return text

def generate_keywords(text, category):
    """Genera una lista de palabras clave únicas filtrando stop words."""
    # Unir descripción y categoría
    full_text = f"{text} {category}"
    # Normalizar (eliminar acentos de forma simple para mejor coincidencia de búsqueda)
    a, b = 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN'
    trans = str.maketrans(a, b)
    full_text_normalized = full_text.translate(trans).upper()
    
    # Obtener palabras individuales
    words = re.findall(r'[A-Z0-9\-]+', full_text_normalized)
    
    keywords = set()
    for word in words:
        # Filtrar palabras cortas y stop words
        if len(word) >= 3 and word not in STOP_WORDS:
            keywords.add(word)
            
    return sorted(list(keywords))

def optimize_image(input_path, output_path):
    """Redimensiona la imagen a máx 1000px y la guarda comprimida como WebP."""
    try:
        with Image.open(input_path) as img:
            # Convertir a RGB si tiene transparencia (para guardar en WebP/JPEG sin problemas)
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                # Crear fondo blanco para conservar colores
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.convert("RGBA").split()[3]) # 3 es el canal alpha
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Limitar tamaño a un máximo de 1000px manteniendo la relación de aspecto
            max_size = 1000
            width, height = img.size
            if width > max_size or height > max_size:
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
            # Guardar como WebP comprimido
            img.save(output_path, "WEBP", quality=80)
            return True
    except Exception as e:
        print(f"Error al optimizar imagen {input_path.name}: {e}")
        return False

def sync_catalog():
    """Ejecuta el escaneo, OCR y generación de catálogo de forma incremental."""
    config = load_config()
    source_dir = Path(config["catalogo_origen_path"])
    web_dir = Path("web")
    assets_dir = web_dir / "assets"
    js_path = web_dir / "products.js"

    
    # Crear directorios de destino si no existen
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Manejar copia de logo si está configurado y existe
    logo_path_str = config.get("logo_path", "")
    use_custom_logo = ""
    if logo_path_str:
        logo_file_path = Path(logo_path_str)
        if logo_file_path.exists() and logo_file_path.is_file():
            try:
                logo_ext = logo_file_path.suffix.lower()
                dest_logo_path = assets_dir / f"logo{logo_ext}"
                shutil.copy2(logo_file_path, dest_logo_path)
                use_custom_logo = f"./assets/logo{logo_ext}"
                print(f"Logo copiado exitosamente a: {dest_logo_path.name}")
            except Exception as e:
                print(f"Error al copiar el logo: {e}")
        else:
            print(f"Advertencia: El archivo de logo en '{logo_path_str}' no existe.")
            
    print(f"Escaneando carpeta de origen: {source_dir.absolute()}")

    
    if not source_dir.exists():
        print(f"Error: La carpeta de origen '{source_dir}' no existe.")
        print("Por favor, crea la carpeta o edita config.json con la ruta correcta.")
        return
        
    # Cargar base de datos existente si existe
    existing_products = {}
    whatsapp_number = config["whatsapp_number"]
    
    if js_path.exists():
        try:
            with open(js_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content.startswith("const PRODUCTS_DATA ="):
                    json_str = content[len("const PRODUCTS_DATA ="):].strip()
                    if json_str.endswith(";"):
                        json_str = json_str[:-1].strip()
                    data = json.loads(json_str)
                    # Extraer lista de productos
                    if isinstance(data, dict) and "products" in data:
                        existing_list = data["products"]
                        existing_products = {p["id"]: p for p in existing_list}
                        # Usar el whatsapp_number configurado en config.json
                        whatsapp_number = config.get("whatsapp_number", data.get("whatsapp_number", whatsapp_number))
        except Exception as e:
            print(f"No se pudo cargar products.js anterior ({e}). Se generará uno nuevo.")

    # Escanear archivos en catalogo_origen
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    found_files = []
    
    # Recorrer subcarpetas (usando followlinks=True para seguir carpetas de OneDrive)
    for root, dirs, files in os.walk(source_dir, followlinks=True):
        category = os.path.basename(root)
        # Si estamos en la raíz del catálogo, saltar
        if root == str(source_dir):
            continue
            
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_extensions:
                file_path = Path(root) / file
                found_files.append((file_path, category))
                
    print(f"Se encontraron {len(found_files)} imágenes de repuestos en las subcarpetas.")
    
    # Procesar imágenes de forma incremental
    updated_products = []
    processed_ids = set()
    new_count = 0
    skipped_count = 0
    
    for file_path, category in found_files:
        # Usar el nombre de archivo sin extensión como ID único
        product_id = file_path.stem
        processed_ids.add(product_id)
        
        webp_filename = f"{product_id}.webp"
        output_image_path = assets_dir / webp_filename
        relative_image_path = f"./assets/{webp_filename}"
        
        # Verificar si ya existe en la base de datos y la imagen optimizada está física
        is_uuid = False
        if product_id in existing_products:
            old_desc = existing_products[product_id].get("description", "")
            uuid_pattern = r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
            if re.match(uuid_pattern, old_desc) or not old_desc.strip():
                is_uuid = True
        
        if product_id in existing_products and output_image_path.exists() and not is_uuid:
            # Conservar registro anterior (actualizando categoría por si cambió de carpeta)
            old_prod = existing_products[product_id]
            # Si cambió de carpeta, refrescar categoría y palabras clave
            if old_prod["category"] != category:
                old_prod["category"] = category
                old_prod["keywords"] = generate_keywords(old_prod["description"], category)
            updated_products.append(old_prod)
            skipped_count += 1
            continue
            
        # Si no existe, es una imagen nueva o fue modificada
        print(f"Procesando [{category}] -> {file_path.name}...")
        
        # 1. Ejecutar OCR
        raw_text = extract_text_from_image(file_path)
        description = clean_text_for_catalog(raw_text, category)
        keywords = generate_keywords(description, category)
        
        # 2. Optimizar imagen y guardarla como WebP
        success = optimize_image(file_path, output_image_path)
        
        if success:
            new_prod = {
                "id": product_id,
                "category": category,
                "image_path": relative_image_path,
                "description": description,
                "keywords": keywords
            }
            updated_products.append(new_prod)
            new_count += 1
        else:
            print(f"Error al procesar la imagen {file_path.name}. Se omitió.")

    # 3. Limpieza de bajas (eliminar archivos físicos de productos que ya no existen)
    deleted_count = 0
    for old_id, old_prod in existing_products.items():
        if old_id not in processed_ids:
            # El producto ya no está en la carpeta de origen
            old_webp = assets_dir / f"{old_id}.webp"
            if old_webp.exists():
                try:
                    os.remove(old_webp)
                except Exception as e:
                    print(f"No se pudo eliminar archivo obsoleto {old_webp.name}: {e}")
            deleted_count += 1
            
    print(f"Resumen de Sincronización:")
    print(f"  - Omitidas (ya procesadas): {skipped_count}")
    print(f"  - Nuevas procesadas: {new_count}")
    print(f"  - Eliminadas del catálogo: {deleted_count}")
    print(f"  - Total actual en catálogo: {len(updated_products)}")
    
    # Guardar base de datos JSON
    catalog_data = {
        "whatsapp_number": whatsapp_number,
        "use_custom_logo": use_custom_logo,
        "total_products": len(updated_products),
        "products": updated_products
    }

    
    try:
        with open(js_path, "w", encoding="utf-8") as f:
            f.write("const PRODUCTS_DATA = ")
            json.dump(catalog_data, f, indent=2, ensure_ascii=False)
            f.write(";\n")
        print(f"¡Catálogo JS guardado con éxito en: {js_path}!")
    except Exception as e:
        print(f"Error al guardar products.js: {e}")

if __name__ == "__main__":
    sync_catalog()
