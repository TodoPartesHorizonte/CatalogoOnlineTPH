# Importar torch y easyocr al inicio para evitar conflictos de DLLs en Windows
try:
    import easyocr
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
        "logo_path": "",
        "instagram_url": "",
        "facebook_url": "",
        "maps_url": "",
        "reviews_url": "",
        "ocr_crop_top": 0.33,
        "ocr_crop_bottom": 0.55
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

def generate_crop_preview(image_path, crop_top, crop_bottom, preview_path):
    """Genera una imagen con un recuadro rojo que muestra la zona de recorte de OCR."""
    from PIL import ImageDraw
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            draw_img = img.copy()
            draw = ImageDraw.Draw(draw_img)
            top_y = int(height * crop_top)
            bottom_y = int(height * crop_bottom)
            draw.rectangle([0, top_y, width - 1, bottom_y], outline="red", width=5)
            if width > 800:
                ratio = 800 / width
                draw_img = draw_img.resize((800, int(height * ratio)), Image.Resampling.LANCZOS)
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            draw_img.convert("RGB").save(preview_path, "JPEG", quality=85)
    except Exception as e:
        print(f"Error al generar vista previa de OCR: {e}")

def is_descriptive_filename(image_path):
    """Determina si un archivo tiene un nombre descriptivo en vez de un ID genérico o de cámara/WhatsApp."""
    filename = image_path.stem
    uuid_pattern = r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$'
    if re.match(uuid_pattern, filename):
        return False
    if filename.lower().startswith('whatsapp image'):
        return False
    if filename.lower() in ('thumbs', 'desktop'):
        return False
    if len(filename) < 2:
        return False
    return True

def extract_text_from_image(image_path, crop_top=0.33, crop_bottom=0.55):
    """Extrae texto de la imagen recortando la franja especificada por crop_top y crop_bottom."""
    init_ocr() # Asegurar que los motores estén listos
    if OCR_READER is not None or TESSERACT_AVAILABLE:
        try:
            with Image.open(image_path) as pil_img:
                width, height = pil_img.size
                crop_box = (0, int(height * crop_top), width, int(height * crop_bottom))
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



def apply_ocr_corrections(text, category):
    """Aplica reglas específicas de autocorrecion de OCR para categorías y repuestos."""
    category_upper = category.upper()
    
    # Lista de reemplazos directos de palabras completas
    word_replacements = [
        ('ARANA', 'ARAÑA'),
        ('MUNON', 'MUÑÓN'),
        ('MUNONNFER0R', 'MUÑÓN INFERIOR'),
        ('MUNONNFERIOR', 'MUÑÓN INFERIOR'),
        ('MUNONFER0R', 'MUÑÓN INFERIOR'),
        ('MUNONNFER10R', 'MUÑÓN INFERIOR'),
        ('MUNONINFERIOR', 'MUÑÓN INFERIOR'),
        ('MUNONN', 'MUÑÓN'),
        ('MUNONNFEROR', 'MUÑÓN INFERIOR'),
        ('CIGUEÑAL', 'CIGÜEÑAL'),
        ('CIGÚEÑAL', 'CIGÜEÑAL'),
        ('CICUEÑAL', 'CIGÜEÑAL'),
        ('CIGUEAL', 'CIGÜEÑAL'),
        ('CIGUE\u00d1AL', 'CIGÜEÑAL'),
        ('CIGÚE\u00d1AL', 'CIGÜEÑAL'),
        ('GUAYACAPOT', 'GUAYA CAPOT'),
        ('JUEGODE', 'JUEGO DE'),
        ('FILTROCAJA', 'FILTRO CAJA'),
        ('BOMBADE', 'BOMBA DE'),
        ('BOMBA DEACEITE', 'BOMBA DE ACEITE'),
        ('REGULADORDE', 'REGULADOR DE'),
        ('SENSORTPS', 'SENSOR TPS'),
        ('BASECAJA', 'BASE CAJA'),
        ('BASEFAN', 'BASE FAN'),
        ('AMORTIGUADORDE', 'AMORTIGUADOR DE'),
        ('EMPACADURADE', 'EMPACADURA DE'),
        ('COPAARRANQUE', 'COPA ARRANQUE'),
        ('TERMINAC EXTERN', 'TERMINAL EXTERNO'),
        ('TUBOCALEFACCI\u00d3N', 'TUBO CALEFACCION'),
        ('TUBOCALEFACCION', 'TUBO CALEFACCION'),
        ('VALVULA ADMISION', 'VÁLVULA ADMISION'),
        ('9DALADA V LEVA', 'SENSOR ARBOL DE LEVA'),
        ('1 ZADNDALD', 'TAPA RADIADOR'),
        ('N GAA', 'TAPA RIN'),
        ('1 ADDADALAD', 'TERMINAL'),
        ('DNAD 1L', 'TERMINAL'),
        ('V ZAVUEL', 'VALVULA'),
        ('B0MEAA D AU', 'BOMBA DE AGUA'),
        ('B0MEAA', 'BOMBA'),
        ('ISIABUDUE', 'DISTRIBUIDOR'),
        ('RUADUGBAE9N', 'REGULADOR'),
        ('DUN LA', 'COLLARIN'),
        
        # Normalizaciones de números de modelo comunes
        ('LUV D-MAX 35', 'LUV D-MAX 3.5'),
        ('LUV D-MAX 24', 'LUV D-MAX 2.4'),
        ('LUV D-MAX 25', 'LUV D-MAX 2.5'),
        ('LUV D-MAX 30', 'LUV D-MAX 3.0'),
        ('LUV D-MAX 304X4', 'LUV D-MAX 3.0 4X4'),
        ('LUV D-MAX 304X2', 'LUV D-MAX 3.0 4X2'),
        ('LUV D-MAX 244X2', 'LUV D-MAX 2.4 4X2'),
        ('LUV D-MAX24', 'LUV D-MAX 2.4'),
        ('LUV D-MAX25', 'LUV D-MAX 2.5'),
        
        ('CARIBE G2OO', 'CARIBE G-2000'),
        ('CARIBE G2OOO', 'CARIBE G-2000'),
        ('CARIBE G-20O', 'CARIBE G-200'),
        ('CARIBE G-2000', 'CARIBE G-2000'),
        ('CARIBE23', 'CARIBE 2.3'),
        ('CARIBE26', 'CARIBE 2.6'),
        ('RODEO32', 'RODEO 3.2'),
        ('RODEO 32', 'RODEO 3.2'),
        ('TROOPER 32', 'TROOPER 3.2'),
        ('TROOPER 32SOCH', 'TROOPER 3.2 SOHC'),
        ('TROOPER 32SOCHH', 'TROOPER 3.2 SOHC'),
        ('RODEO 32 SOCH', 'RODEO 3.2 SOHC'),
        ('RODEO 32 SOCHH', 'RODEO 3.2 SOHC'),
        ('LUV 32', 'LUV 3.2'),
        ('LUV 22', 'LUV 2.2'),
        ('LUV 23', 'LUV 2.3'),
        ('CARIBE 26', 'CARIBE 2.6'),
        ('CARIBE 20', 'CARIBE 2.0'),
        ('CARIBE 23', 'CARIBE 2.3'),
        ('CARIBE 2600', 'CARIBE 2600'),
        ('CARIBE 2300', 'CARIBE 2300'),
        ('CARIBE 2000', 'CARIBE 2000'),
        ('CARIBE 200O', 'CARIBE 2000'),
        ('CARIBE G20O', 'CARIBE G-200'),
    ]
    
    # Aplicar reemplazos de palabras completas con límite unicode
    for target, replacement in word_replacements:
        pattern = r'(?<![A-Z0-9\u00c1\u00c9\u00cd\u00d3\u00da\u00d1])' + re.escape(target) + r'(?![A-Z0-9\u00c1\u00c9\u00cd\u00d3\u00da\u00d1])'
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
    # Heurística específica basada en categorías para cuando el OCR falla totalmente
    if category_upper == "TAPA RADIADOR" and "TAPA" not in text:
        text = f"TAPA RADIADOR {text}"
    elif category_upper == "TAPA RIN" and "TAPA" not in text:
        text = f"TAPA RIN {text}"
    elif "MUÑON" in category_upper and "MUÑÓN" not in text and "MUÑON" not in text:
        text = f"MUÑÓN {text}"
    elif "BUJE ARAÑA" in category_upper and "BUJE" not in text:
        text = f"BUJE DE ARAÑA {text}"
    elif category_upper == "ARAÑA" and "ARAÑA" not in text and "ARANA" not in text:
        text = f"ARAÑA {text}"
    elif category_upper == "SENSOR ARBOL DE LEVA" and "SENSOR" not in text:
        text = f"SENSOR ARBOL DE LEVA {text}"
    elif category_upper == "TERMINAL - ROTULA" and "TERMINAL" not in text and "ROTULA" not in text:
        text = f"TERMINAL / ROTULA {text}"
    elif category_upper == "VALVULA TEMPERATURA" and "VALVULA" not in text:
        text = f"VALVULA TEMPERATURA {text}"
    elif category_upper == "BOMBA DE AGUA" and "BOMBA" not in text:
        text = f"BOMBA DE AGUA {text}"
    elif category_upper == "BOMBA DE ACEITE" and "BOMBA" not in text:
        text = f"BOMBA DE ACEITE {text}"
    elif category_upper == "BOMBA DE GASOLINA" and "BOMBA" not in text and "PILA" not in text:
        text = f"BOMBA DE GASOLINA {text}"
    elif category_upper == "BOMBA DE FRENO" and "BOMBA" not in text:
        text = f"BOMBA DE FRENO {text}"
    elif category_upper == "DISTRIBUIDOR" and "DISTRIBUIDOR" not in text:
        text = f"DISTRIBUIDOR {text}"
    elif category_upper == "COLLARIN" and "COLLARIN" not in text and "ROLINERA" not in text:
        text = f"COLLARIN {text}"
    elif category_upper == "REGULADOR PRESION GASOLINA" and "REGULADOR" not in text:
        text = f"REGULADOR DE GASOLINA {text}"
    elif category_upper == "CARBURADOR" and "CARBURADOR" not in text:
        if "GDAN" in text or len(text) < 15:
            text = "CARBURADOR LUV"
        else:
            text = f"CARBURADOR {text}"
    elif category_upper == "KIT DE MOTOR" and "KIT" not in text:
        if "LU" in text:
            text = text.replace("LU", "LUV")
        text = f"KIT DE MOTOR {text}"
        
    return text

def clean_text_for_catalog(raw_text, category, image_path=None):
    """Limpia el texto OCR, elimina saltos de línea y normaliza a mayúsculas."""
    if image_path and is_descriptive_filename(image_path):
        filename_clean = image_path.stem.replace('-', ' ').replace('_', ' ').strip()
        if category.upper() in filename_clean.upper():
            text = filename_clean
        else:
            text = f"{category} {filename_clean}"
    else:
        if not raw_text:
            return category.upper()
        text = raw_text
        
    # Reemplazar saltos de línea y tabuladores por espacios
    text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # Remover símbolos extraños pero conservar letras, números y guiones/barras/puntos
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
    
    # Aplicar calibraciones y correcciones de OCR específicas
    text = apply_ocr_corrections(text, category)
    
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
            
            img.save(output_path, "WEBP", quality=85)
        return True
    except Exception as e:
        print(f"Error optimizando imagen {input_path}: {e}")
        return False

def read_catalog_js():
    """Lee y decodifica la base de datos JSON de products.js para evitar redundancias."""
    js_path = Path("web/products.js")
    if not js_path.exists():
        return None
    try:
        with open(js_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.startswith("const PRODUCTS_DATA ="):
                json_str = content[len("const PRODUCTS_DATA ="):].strip()
                if json_str.endswith(";"):
                    json_str = json_str[:-1].strip()
                return json.loads(json_str)
    except Exception as e:
        print(f"Error al leer products.js: {e}")
    return None

def write_catalog_js(catalog_data):
    """Escribe el diccionario en products.js en el formato adecuado."""
    js_path = Path("web/products.js")
    try:
        js_path.parent.mkdir(parents=True, exist_ok=True)
        with open(js_path, "w", encoding="utf-8") as f:
            f.write("const PRODUCTS_DATA = ")
            json.dump(catalog_data, f, indent=2, ensure_ascii=False)
            f.write(";\n")
        return True
    except Exception as e:
        print(f"Error al escribir products.js: {e}")
        return False

def get_first_product_image():
    """Busca la primera imagen de repuesto en las subcarpetas del catálogo."""
    config = load_config()
    source_dir = Path(config["catalogo_origen_path"])
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    if source_dir.exists():
        for root, dirs, files in os.walk(source_dir, followlinks=True):
            if root == str(source_dir):
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_extensions:
                    return Path(root) / file
    return None

def sync_catalog(progress_callback=None):
    """Ejecuta el escaneo, OCR y generación de catálogo de forma incremental."""
    config = load_config()
    source_dir = Path(config["catalogo_origen_path"])
    web_dir = Path("web")
    assets_dir = web_dir / "assets"
    js_path = web_dir / "products.js"
    
    crop_top = float(config.get("ocr_crop_top", 0.33))
    crop_bottom = float(config.get("ocr_crop_bottom", 0.55))

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
        if progress_callback:
            progress_callback(0, 1, f"Error: Carpeta de origen no existe.")
        return
        
    # Cargar base de datos existente si existe
    existing_products = {}
    whatsapp_number = config["whatsapp_number"]
    
    data = read_catalog_js()
    if data:
        if isinstance(data, dict) and "products" in data:
            existing_list = data["products"]
            existing_products = {p["id"]: p for p in existing_list}
            whatsapp_number = config.get("whatsapp_number", data.get("whatsapp_number", whatsapp_number))

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
    
    # Generar vista previa de calibración de OCR con la primera imagen encontrada
    if found_files:
        first_file_path, _ = found_files[0]
        preview_file_path = assets_dir / "ocr_crop_preview.jpg"
        generate_crop_preview(first_file_path, crop_top, crop_bottom, preview_file_path)
        print(f"Vista previa de calibración de OCR generada en: {preview_file_path.name}")
        
    # Procesar imágenes de forma incremental
    updated_products = []
    processed_ids = set()
    new_count = 0
    skipped_count = 0
    newly_processed_ids = []
    
    total_files = len(found_files)
    if progress_callback:
        progress_callback(0, total_files or 1, "Iniciando procesamiento de imágenes...")

    for idx, (file_path, category) in enumerate(found_files):
        # Usar el nombre de archivo sin extensión como ID único
        product_id = file_path.stem
        processed_ids.add(product_id)
        
        webp_filename = f"{product_id}.webp"
        output_image_path = assets_dir / webp_filename
        relative_image_path = f"./assets/{webp_filename}"
        
        # Reportar progreso
        if progress_callback:
            progress_callback(idx, total_files, f"Procesando [{category}] -> {file_path.name}")

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
        raw_text = extract_text_from_image(file_path, crop_top=crop_top, crop_bottom=crop_bottom)
        description = clean_text_for_catalog(raw_text, category, file_path)
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
            newly_processed_ids.append(product_id)
        else:
            print(f"Error al procesar la imagen {file_path.name}. Se omitió.")

    # Ordenar los productos finales alfabéticamente por categoría y luego por descripción
    updated_products.sort(key=lambda x: (x["category"].lower(), x["description"].lower()))

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
        "instagram_url": config.get("instagram_url", ""),
        "facebook_url": config.get("facebook_url", ""),
        "maps_url": config.get("maps_url", ""),
        "reviews_url": config.get("reviews_url", ""),
        "total_products": len(updated_products),
        "products": updated_products
    }

    write_success = write_catalog_js(catalog_data)
    if write_success:
        print(f"¡Catálogo JS guardado con éxito en: {js_path}!")
        if progress_callback:
            progress_callback(total_files, total_files, "Catálogo generado y guardado con éxito.")
    else:
        print(f"Error al guardar products.js")
        if progress_callback:
            progress_callback(total_files, total_files, "Error al guardar el catálogo JS.")
            
    return newly_processed_ids

def update_js_links(config):
    """Actualiza únicamente los enlaces de contacto en products.js sin escanear imágenes."""
    try:
        data = read_catalog_js()
        if not data:
            return False
            
        data["whatsapp_number"] = config.get("whatsapp_number", "")
        data["instagram_url"] = config.get("instagram_url", "")
        data["facebook_url"] = config.get("facebook_url", "")
        data["maps_url"] = config.get("maps_url", "")
        data["reviews_url"] = config.get("reviews_url", "")
        
        # Copiar el logo si existe y está configurado
        logo_path_str = config.get("logo_path", "")
        if logo_path_str:
            logo_file_path = Path(logo_path_str)
            if logo_file_path.exists() and logo_file_path.is_file():
                assets_dir = Path("web/assets")
                assets_dir.mkdir(parents=True, exist_ok=True)
                logo_ext = logo_file_path.suffix.lower()
                dest_logo_path = assets_dir / f"logo{logo_ext}"
                shutil.copy2(logo_file_path, dest_logo_path)
                data["use_custom_logo"] = f"./assets/logo{logo_ext}"
        
        success = write_catalog_js(data)
        if success:
            print("Enlaces y logo actualizados rápidamente en products.js.")
            return True
    except Exception as e:
        print(f"Error al actualizar enlaces rápidos en products.js: {e}")
        
    return False

def delete_product(product_id, category):
    """Elimina un producto del catálogo web y también intenta borrar la foto de origen."""
    try:
        # 1. Borrar la imagen optimizada WebP
        assets_dir = Path("web/assets")
        webp_path = assets_dir / f"{product_id}.webp"
        if webp_path.exists():
            os.remove(webp_path)
            print(f"Imagen WebP optimizada eliminada: {webp_path}")
            
        # 2. Borrar la foto original de la carpeta origen
        config = load_config()
        source_dir = Path(config.get("catalogo_origen_path", ""))
        if source_dir.exists():
            category_dir = source_dir / category
            if category_dir.exists():
                valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
                for ext in valid_extensions:
                    orig_path = category_dir / f"{product_id}{ext}"
                    if orig_path.exists():
                        try:
                            os.remove(orig_path)
                            print(f"Foto de origen eliminada: {orig_path}")
                        except Exception as e:
                            print(f"Error al eliminar foto de origen {orig_path}: {e}")
                
        # 3. Leer products.js, remover de la lista y escribir
        data = read_catalog_js()
        if data and "products" in data:
            old_products = data["products"]
            new_products = [p for p in old_products if p["id"] != product_id]
            data["products"] = new_products
            data["total_products"] = len(new_products)
            write_catalog_js(data)
            
        return True, "Producto eliminado correctamente."
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    sync_catalog()
