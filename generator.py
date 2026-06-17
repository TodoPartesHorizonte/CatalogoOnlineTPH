# Importar torch y easyocr al inicio para evitar conflictos de DLLs en Windows
try:
    import easyocr
except Exception:
    pass

import os
import json
import re
import shutil
import base64
from pathlib import Path
from PIL import Image

# Lista de palabras vacías (stop words) en español para limpiar palabras clave
STOP_WORDS = {
    'DE', 'EL', 'LA', 'PARA', 'CON', 'DEL', 'LOS', 'LAS', 'UN', 'UNA', 'Y', 'O', 
    'A', 'EN', 'POR', 'AL', 'LO', 'SU', 'SUS', 'DEL', 'E', 'SE', 'ESTE', 'ESTA'
}

def obfuscate_value(value):
    """Codifica un valor en Base64 para evitar raspado de datos simple en el frontend."""
    if value is None:
        return ""
    val_str = str(value).strip()
    return base64.b64encode(val_str.encode('utf-8')).decode('utf-8')


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
        "google_analytics_id": "",
        "looker_studio_url": "",
        "base_url": "https://todoparteshorizonte.com/",
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
        
    print("⚙️ Inicializando motores de lectura OCR...")
    
    # 1. Intentar cargar EasyOCR
    try:
        import easyocr
        # Inicializa el lector para español e inglés
        OCR_READER = easyocr.Reader(['es', 'en'])
        print("   ✅ EasyOCR cargado correctamente (recomendado).")
    except Exception as e:
        print(f"   ⚠️ EasyOCR no disponible ({e}). Intentando cargar Pytesseract...")

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
            print("   ✅ Pytesseract (Tesseract OCR) cargado correctamente.")
        except Exception as e:
            print(f"   ⚠️ Pytesseract no disponible o no configurado ({e}).")

    if OCR_READER is None and not TESSERACT_AVAILABLE:
        print("   🚨 ¡ALERTA! No hay ningún motor OCR disponible. Se usará el nombre de los archivos.")
        
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

def generate_unique_slug(text, used_slugs):
    """Genera un slug SEO amigable y único a partir de la descripción."""
    # Eliminar acentos
    a, b = 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN'
    trans = str.maketrans(a, b)
    slug_base = text.translate(trans).lower()
    
    # Reemplazar caracteres no alfanuméricos por guiones
    slug_base = re.sub(r'[^a-z0-9]+', '-', slug_base).strip('-')
    
    if not slug_base:
        slug_base = "producto"
        
    slug = slug_base
    counter = 2
    while slug in used_slugs:
        slug = f"{slug_base}-{counter}"
        counter += 1
        
    used_slugs.add(slug)
    return slug

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
            if content.startswith("const PRODUCTS_DATA =") or content.startswith("const PRODUCTS_DATA="):
                json_str = content[content.find("{"):].strip()
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

def inject_preload_images(catalog_data):
    """Inyecta etiquetas de precarga en index.html para las 4 fotos más recientes (LCP)."""
    try:
        products = catalog_data.get("products", [])
        if not products:
            return False
            
        index_path = Path("web/index.html")
        if not index_path.exists():
            return False
            
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        import re
        start_marker = "<!-- INICIO PRECARGA -->"
        end_marker = "<!-- FIN PRECARGA -->"
        
        if start_marker in content and end_marker in content:
            preloads = []
            for p in products[:4]:
                if "image_path" in p:
                    preloads.append(f'    <link rel="preload" as="image" href="{p["image_path"]}" fetchpriority="high">')
            
            replacement = f"{start_marker}\n" + "\n".join(preloads) + f"\n    {end_marker}"
            new_content = re.sub(rf"{start_marker}.*?{end_marker}", replacement, content, flags=re.DOTALL)
            
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return True
    except Exception as e:
        print(f"Error inyectando preloads en index.html: {e}")
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

def get_site_base_url():
    """Obtiene el dominio base del catálogo. Busca primero en la configuración y luego usa el dominio oficial."""
    try:
        config = load_config()
        if "base_url" in config and config["base_url"].strip():
            url = config["base_url"].strip()
            if not url.endswith("/"):
                url += "/"
            return url
    except Exception:
        pass
    return "https://todoparteshorizonte.com/"

def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def generate_seo_files(products, web_dir):
    """Genera automáticamente sitemap.xml, robots.txt y páginas estáticas de productos en la carpeta web/p/."""
    import re
    
    def to_title_case(text):
        if not text:
            return ""
        def cap_word(w):
            if '-' in w:
                return '-'.join(p.capitalize() for p in w.split('-'))
            return w.capitalize()
        return ' '.join(cap_word(w) for w in text.split())

    uuid_pattern = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
    web_path = Path(web_dir)
    base_url = get_site_base_url()
    
    # 1. Generar robots.txt
    robots_path = web_path / "robots.txt"
    try:
        with open(robots_path, "w", encoding="utf-8") as f:
            f.write("# /robots.txt para TODO PARTES Horizonte\n")
            f.write("User-agent: *\n")
            f.write("Allow: /\n")
            f.write("Disallow: /admin/\n")
            f.write(f"\nSitemap: {base_url}sitemap.xml\n")
        print(f"🤖 robots.txt generado exitosamente en: {robots_path.name}")
    except Exception as e:
        print(f"❌ Error al generar robots.txt: {e}")
        
    # 2. Generar Páginas Estáticas (Programmatic SEO)
    p_dir = web_path / "p"
    p_dir.mkdir(parents=True, exist_ok=True)
    
    # Limpiar archivos HTML obsoletos que no correspondan a los productos actuales
    expected_filenames = set()
    for prod in products:
        p_id = prod.get('id', '')
        p_slug = prod.get('slug', '')
        # Omitir si no hay slug, o si el slug es un UUID, o si coincide con el ID
        if not p_slug or uuid_pattern.match(p_slug) or p_slug == p_id:
            continue
        safe_filename = f"{p_slug}.html"
        expected_filenames.add(safe_filename)
        
    for item in p_dir.iterdir():
        if item.is_file() and item.suffix == ".html" and item.name not in expected_filenames:
            try:
                os.remove(item)
                print(f"🧹 Eliminado archivo SEO obsoleto: {item.name}")
            except Exception as e:
                print(f"❌ Error al eliminar archivo SEO obsoleto {item.name}: {e}")
                
    config = load_config()
    whatsapp_number = config.get("whatsapp_number", "")
    ga_id = config.get("google_analytics_id", "")
    instagram_url = config.get("instagram_url", "https://www.instagram.com/todopartes_horizonte?igsh=c3F0ZDJ3aXF0ejdv")
    facebook_url = config.get("facebook_url", "https://www.facebook.com/todoparteshorizonte493/")
    maps_url = config.get("maps_url", "https://share.google/3jXZ44CMybUut4NUb")
    reviews_url = config.get("reviews_url", "https://g.page/r/CXMpkN_I_0jiEBM/review")
    
    # Extraer la extensión correcta del logo
    logo_path_str = config.get("logo_path", "")
    logo_ext = ".png" # por defecto
    if logo_path_str:
        logo_file_path = Path(logo_path_str)
        if logo_file_path.exists():
            logo_ext = logo_file_path.suffix.lower()
            
    ga_script = ""
    if ga_id:
        ga_script = f"""
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{ga_id}');
    </script>"""
    
    template = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://www.googletagmanager.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://www.google-analytics.com https://analytics.google.com https://stats.g.doubleclick.net;">
    <title>{description} | Repuestos TODO PARTES</title>
    <meta name="description" content="Comprar {description} al mejor precio. Repuesto especializado en Caracas. Consulta disponibilidad y precio vía WhatsApp.">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{base_url}p/{safe_filename}">
    <link rel="icon" href="../assets/logo{logo_ext}" type="{logo_type}">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{description} | Repuestos">
    <meta property="og:description" content="Comprar {description}. Repuesto especializado en Caracas. Consulta disponibilidad vía WhatsApp.">
    <meta property="og:image" content="{base_url}assets/{id}.webp">
    <meta property="og:url" content="{base_url}p/{safe_filename}">
    <meta property="og:type" content="product">
    
    <!-- JSON-LD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org/",
      "@type": "Product",
      "name": "{description}",
      "image": "{base_url}assets/{id}.webp",
      "description": "{description}. Especialistas en repuestos en Caracas.",
      "brand": {{
        "@type": "Brand",
        "name": "Original"
      }},
      "offers": {{
        "@type": "Offer",
        "price": "0.00",
        "priceCurrency": "USD",
        "priceValidUntil": "2027-12-31",
        "availability": "https://schema.org/InStock",
        "url": "{base_url}p/{safe_filename}",
        "seller": {{
          "@type": "AutoPartsStore",
          "@id": "{base_url}#store"
        }},
        "shippingDetails": {{
          "@type": "OfferShippingDetails",
          "shippingRate": {{
            "@type": "MonetaryAmount",
            "value": "0.00",
            "currency": "USD"
          }},
          "shippingDestination": {{
            "@type": "DefinedRegion",
            "addressCountry": "VE"
          }},
          "deliveryTime": {{
            "@type": "ShippingDeliveryTime",
            "handlingTime": {{
              "@type": "QuantitativeValue",
              "minValue": 0,
              "maxValue": 1,
              "unitCode": "DAY"
            }},
            "transitTime": {{
              "@type": "QuantitativeValue",
              "minValue": 1,
              "maxValue": 3,
              "unitCode": "DAY"
            }}
          }}
        }},
        "hasMerchantReturnPolicy": {{
          "@type": "MerchantReturnPolicy",
          "applicableCountry": "VE",
          "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
          "merchantReturnDays": 7,
          "returnMethod": "https://schema.org/ReturnInStore",
          "returnFees": "https://schema.org/FreeReturn"
        }}
      }},
      "aggregateRating": {{
        "@type": "AggregateRating",
        "ratingValue": "5.0",
        "reviewCount": "24"
      }},
      "review": {{
        "@type": "Review",
        "author": {{
          "@type": "Person",
          "name": "Cliente de Todo Partes"
        }},
        "reviewRating": {{
          "@type": "Rating",
          "ratingValue": "5"
        }},
        "reviewBody": "Excelente atención y variedad de repuestos."
      }}
    }}
    </script>{ga_script}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
    <script defer src="../cart.js"></script>
    <style>
        :root {{
            --bg-primary: #0a0a0c;
            --bg-secondary: #111116;
            --bg-card: rgba(17,17,22,0.7);
            --accent-orange: #ff6a00;
            --accent-orange-hover: #f05a18;
            --accent-green: #25d366;
            --accent-green-hover: #128c7e;
            --text-primary: #ffffff;
            --text-secondary: #9ea0a8;
            --text-muted: #5e6068;
            --border-color: rgba(255,255,255,0.05);
            --border-glow: rgba(255,106,0,0.15);
            --glass-shadow: 0 8px 32px 0 rgba(0,0,0,0.37);
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', sans-serif;
            -webkit-tap-highlight-color: transparent;
        }}

        body {{
            background-color: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
            background-image: 
                radial-gradient(circle at 50% 50%, transparent 30%, var(--bg-primary) 85%),
                linear-gradient(rgba(255, 106, 0, 0.015) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 106, 0, 0.015) 1px, transparent 1px);
            background-size: 100% 100%, 32px 32px, 32px 32px;
            padding-top: 100px;
            padding-bottom: 40px;
            position: relative;
            display: flex;
            flex-direction: column;
        }}

        body::before, body::after {{
            content: "";
            position: fixed;
            width: 60vw;
            height: 60vw;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(255, 106, 0, 0.035) 0%, rgba(255, 106, 0, 0) 70%);
            filter: blur(80px);
            z-index: -1;
            pointer-events: none;
            will-change: transform;
            transform: translate3d(0, 0, 0);
        }}

        body::before {{
            top: -15vw;
            left: -15vw;
            animation: driftFirst 25s infinite alternate ease-in-out;
        }}

        body::after {{
            bottom: -15vw;
            right: -15vw;
            background: radial-gradient(circle, rgba(255, 106, 0, 0.025) 0%, rgba(255, 106, 0, 0) 70%);
            animation: driftSecond 30s infinite alternate ease-in-out;
        }}

        @keyframes driftFirst {{
            0% {{ transform: translate3d(0, 0, 0) scale(1); }}
            50% {{ transform: translate3d(8vw, 12vw, 0) scale(1.1); }}
            100% {{ transform: translate3d(-4vw, 6vw, 0) scale(0.9); }}
        }}

        @keyframes driftSecond {{
            0% {{ transform: translate3d(0, 0, 0) scale(1.1); }}
            50% {{ transform: translate3d(-10vw, -8vw, 0) scale(0.95); }}
            100% {{ transform: translate3d(5vw, -12vw, 0) scale(1.05); }}
        }}

        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: var(--bg-primary);
        }}
        ::-webkit-scrollbar-thumb {{
            background: #22222a;
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: var(--accent-orange);
        }}

        header {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
            background: linear-gradient(to right, rgba(10, 10, 12, 0.92) 35%, rgba(10, 10, 12, 0.75) 100%);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 24px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.25);
        }}

        .header-container {{
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
        }}

        .brand-lockup {{
            display: flex;
            align-items: center;
            gap: 14px;
            text-decoration: none;
            color: inherit;
        }}

        .logo-image {{
            height: 52px;
            width: 52px;
            border-radius: 50%;
            border: 2px solid rgba(255, 106, 0, 0.4);
            background: rgba(10, 10, 12, 0.85);
            box-shadow: 0 4px 15px rgba(255, 106, 0, 0.2);
            object-fit: cover;
            padding: 2px;
        }}

        .brand-text {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }}

        .logo-title {{
            font-size: 20px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #ffffff;
            line-height: 1.15;
            margin: 0;
        }}

        .logo-title span {{
            color: var(--accent-orange);
            background: linear-gradient(135deg, #ffaa00 0%, #ff6a00 50%, #ff3c00 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 900;
        }}

        .logo-subtitle {{
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
        }}

        .social-links {{
            display: flex;
            gap: 8px;
        }}

        .social-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            transition: var(--transition);
            text-decoration: none;
        }}

        .social-btn svg {{
            width: 16px;
            height: 16px;
            fill: currentColor;
        }}

        .social-btn:hover {{
            color: #fff;
            transform: translateY(-2px);
        }}

        .social-btn.instagram:hover {{
            background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%);
            border-color: transparent;
            box-shadow: 0 0 10px rgba(225, 48, 108, 0.4);
        }}

        .social-btn.facebook:hover {{
            background: #1877f2;
            border-color: transparent;
            box-shadow: 0 0 10px rgba(24, 119, 242, 0.4);
        }}

        .social-btn.maps:hover {{
            background: #ea4335;
            border-color: transparent;
            box-shadow: 0 0 10px rgba(234, 67, 53, 0.4);
        }}

        .social-btn.reviews:hover {{
            background: #f4b400;
            border-color: transparent;
            box-shadow: 0 0 10px rgba(244, 180, 0, 0.4);
            color: #0c0c0e;
        }}

        .container {{
            max-width: 1100px;
            width: 100%;
            margin: 0 auto;
            padding: 24px;
            flex-grow: 1;
        }}

        .breadcrumbs {{
            display: flex;
            align-items: center;
            gap: 8px;
            list-style: none;
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 24px;
            flex-wrap: wrap;
            padding: 0;
        }}

        .breadcrumbs a {{
            color: var(--text-secondary);
            text-decoration: none;
            transition: var(--transition);
        }}

        .breadcrumbs a:hover {{
            color: var(--accent-orange);
        }}

        .breadcrumbs li:not(:last-child)::after {{
            content: "/";
            margin-left: 8px;
            color: var(--text-muted);
        }}

        .breadcrumbs li:last-child {{
            color: var(--text-primary);
            font-weight: 600;
        }}

        .product-layout {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 32px;
            margin-bottom: 40px;
        }}

        @media (min-width: 768px) {{
            .product-layout {{
                grid-template-columns: 1.1fr 1.2fr;
                gap: 48px;
            }}
        }}

        .image-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 16px;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: var(--glass-shadow);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
            aspect-ratio: 1;
        }}

        .image-card::after {{
            content: '';
            position: absolute;
            inset: 0;
            border-radius: 20px;
            padding: 1px;
            background: linear-gradient(135deg, rgba(255, 106, 0, 0.3), transparent 60%);
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
            -webkit-mask-composite: xor;
            mask-composite: exclude;
            pointer-events: none;
        }}

        .product-img {{
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
            border-radius: 12px;
            transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
        }}

        .image-card:hover .product-img {{
            transform: scale(1.04);
        }}

        .details-panel {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .category-badge {{
            align-self: flex-start;
            background: rgba(255, 106, 0, 0.1);
            border: 1px solid var(--accent-orange);
            color: var(--accent-orange);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            padding: 6px 14px;
            border-radius: 20px;
            letter-spacing: 0.8px;
        }}

        .product-title {{
            font-size: 28px;
            font-weight: 800;
            color: var(--text-primary);
            line-height: 1.3;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        @media (min-width: 768px) {{
            .product-title {{
                font-size: 34px;
            }}
        }}



        .cta-card {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 16px 24px;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 700;
            text-decoration: none;
            transition: var(--transition);
            cursor: pointer;
            text-align: center;
        }}

        .btn-whatsapp {{
            background: linear-gradient(135deg, #25d366 0%, #128c7e 100%);
            color: #fff;
            box-shadow: 0 4px 15px rgba(37, 211, 102, 0.3);
        }}

        .btn-whatsapp:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(37, 211, 102, 0.4);
            background: linear-gradient(135deg, #2ee070 0%, #179b8d 100%);
        }}

        .btn-whatsapp svg {{
            width: 20px;
            height: 20px;
            fill: currentColor;
        }}

        .btn-secondary {{
            background: transparent;
            border: 1px solid rgba(255, 106, 0, 0.4);
            color: #fff;
        }}

        .btn-secondary:hover {{
            background: rgba(255, 106, 0, 0.1);
            border-color: var(--accent-orange);
            transform: translateY(-2px);
        }}

        .business-info {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .business-info h3 {{
            font-size: 15px;
            font-weight: 700;
            color: #fff;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            border-left: 3px solid var(--accent-orange);
            padding-left: 10px;
            margin: 0 0 4px 0;
        }}

        .info-item {{
            display: flex;
            gap: 12px;
            font-size: 13.5px;
            line-height: 1.5;
            color: var(--text-secondary);
            text-align: left;
        }}

        .info-item svg {{
            width: 18px;
            height: 18px;
            fill: var(--accent-orange);
            flex-shrink: 0;
            margin-top: 2px;
        }}

        .info-item strong {{
            color: #fff;
        }}

        footer {{
            background: #060608;
            border-top: 1px solid var(--border-color);
            padding: 40px 24px 20px 24px;
            margin-top: auto;
            text-align: left;
        }}

        .footer-content {{
            max-width: 1100px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr;
            gap: 32px;
            padding-bottom: 30px;
            border-bottom: 1px solid var(--border-color);
        }}

        @media (min-width: 768px) {{
            .footer-content {{
                grid-template-columns: 1.2fr 1fr 1fr;
                gap: 48px;
            }}
        }}

        .footer-col {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .footer-title {{
            font-size: 14px;
            font-weight: 700;
            text-transform: uppercase;
            color: #fff;
            letter-spacing: 1px;
            margin: 0;
        }}

        .footer-text {{
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.6;
        }}

        .footer-links {{
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 0;
        }}

        .footer-links a {{
            font-size: 13px;
            color: var(--text-secondary);
            text-decoration: none;
            transition: var(--transition);
        }}

        .footer-links a:hover {{
            color: var(--accent-orange);
            padding-left: 4px;
        }}

        .footer-bottom {{
            max-width: 1100px;
            margin: 20px auto 0 auto;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            font-size: 12px;
            color: var(--text-muted);
            text-align: center;
        }}

        @media (min-width: 768px) {{
            .footer-bottom {{
                flex-direction: row;
                text-align: left;
            }}
        }}

        /* Responsive styling for Header */
        @media (max-width: 768px) {{
            header {{
                padding: 12px 16px;
            }}
            .header-container {{
                flex-direction: column;
                gap: 12px;
                align-items: center;
            }}
            .brand-lockup {{
                flex-direction: column;
                gap: 6px;
                text-align: center;
                align-items: center;
            }}
            .brand-text {{
                align-items: center;
            }}
            body {{
                padding-top: 150px;
            }}
        }}

        /* Cart drawer styles */
        .cart-drawer {{
            position: fixed;
            top: 0;
            right: 0;
            width: 420px;
            height: 100%;
            background: rgba(10, 10, 12, 0.75);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border-left: 1px solid var(--border-color);
            box-shadow: -10px 0 30px rgba(0, 0, 0, 0.6);
            z-index: 999;
            transform: translateX(100%);
            transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            flex-direction: column;
        }}
        .cart-drawer.active {{
            transform: translateX(0);
        }}
        .cart-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            z-index: 998;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }}
        .cart-overlay.active {{
            opacity: 1;
            pointer-events: auto;
        }}
        .cart-header {{
            padding: 24px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .cart-header h3 {{
            font-size: 16px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text-primary);
            margin: 0;
        }}
        .cart-close {{
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 28px;
            cursor: pointer;
            line-height: 1;
            transition: var(--transition);
        }}
        .cart-close:hover {{
            color: var(--accent-orange);
            transform: rotate(90deg);
        }}
        .cart-clear-btn {{
            background: rgba(217, 83, 79, 0.1);
            border: 1px solid rgba(217, 83, 79, 0.3);
            color: #d9534f;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            cursor: pointer;
            transition: var(--transition);
            margin-left: auto;
            margin-right: 12px;
        }}
        .cart-clear-btn:hover {{
            background: #d9534f;
            color: #ffffff;
            border-color: transparent;
            box-shadow: 0 0 8px rgba(217, 83, 79, 0.4);
        }}
        .cart-body {{
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .cart-item {{
            display: flex;
            gap: 12px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 12px;
            align-items: center;
            position: relative;
            transition: var(--transition);
        }}
        .cart-item:hover {{
            border-color: rgba(255, 106, 0, 0.2);
            background: rgba(255, 255, 255, 0.03);
        }}
        .cart-item-img {{
            width: 60px;
            height: 60px;
            border-radius: 8px;
            object-fit: cover;
            background: #0d0d12;
            border: 1px solid var(--border-color);
        }}
        .cart-item-info {{
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .cart-item-title {{
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            color: var(--text-primary);
            line-height: 1.3;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            text-align: left;
        }}
        .cart-item-category {{
            font-size: 9px;
            font-weight: 600;
            text-transform: uppercase;
            color: var(--accent-orange);
            letter-spacing: 0.5px;
            text-align: left;
        }}
        .cart-item-controls {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 6px;
        }}
        .cart-qty-btn {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border: 1px solid var(--border-color);
            background: rgba(255, 255, 255, 0.03);
            color: var(--text-primary);
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: var(--transition);
        }}
        .cart-qty-btn:hover {{
            background: var(--accent-orange);
            border-color: transparent;
            color: #ffffff;
        }}
        .cart-item-qty {{
            font-size: 13px;
            font-weight: 700;
            width: 20px;
            text-align: center;
        }}
        .cart-item-remove {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 4px;
            transition: var(--transition);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-left: auto;
        }}
        .cart-item-remove:hover {{
            color: #d9534f;
            transform: scale(1.1);
        }}
        .cart-item-remove svg {{
            width: 18px;
            height: 18px;
            fill: currentColor;
        }}
        .cart-footer {{
            padding: 24px;
            border-top: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            gap: 16px;
            background: rgba(10, 10, 12, 0.5);
        }}
        .cart-summary {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
            color: var(--text-secondary);
        }}
        .cart-summary strong {{
            font-size: 18px;
            color: var(--text-primary);
        }}
        .cart-submit-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            width: 100%;
            padding: 16px;
            border-radius: 16px;
            border: none;
            background: var(--accent-green);
            color: #ffffff;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            transition: var(--transition);
            box-shadow: 0 4px 15px rgba(37, 211, 102, 0.3);
        }}
        .cart-submit-btn:hover {{
            background: var(--accent-green-hover);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(37, 211, 102, 0.4);
        }}
        .cart-empty {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            text-align: center;
            gap: 12px;
            color: var(--text-muted);
            padding: 40px 20px;
        }}
        .fab-whatsapp {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: var(--accent-green);
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 6px 20px rgba(37, 211, 102, 0.4);
            cursor: pointer;
            z-index: 90;
            transition: var(--transition);
            text-decoration: none;
        }}
        .fab-whatsapp:hover {{
            background: var(--accent-green-hover);
            transform: scale(1.1) translateY(-3px);
            box-shadow: 0 8px 25px rgba(37, 211, 102, 0.5);
        }}
        .fab-whatsapp svg {{
            width: 28px;
            height: 28px;
            fill: #ffffff;
        }}
        .fab-cart-badge {{
            position: absolute;
            top: -4px;
            right: -4px;
            background: var(--accent-orange);
            color: #ffffff;
            font-size: 11px;
            font-weight: 800;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 2px solid var(--bg-primary);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
            transform: scale(0);
            transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }}
        .fab-cart-badge.active {{
            transform: scale(1);
        }}
        .btn-back-catalog:hover {{
            color: var(--accent-orange) !important;
        }}
        @media (max-width: 768px) {{
            .cart-drawer {{
                width: 100%;
                height: 82vh;
                top: auto;
                bottom: 0;
                border-left: none;
                border-top: 1px solid var(--border-color);
                border-radius: 20px 20px 0 0;
                transform: translateY(100%);
            }}
            .cart-drawer.active {{
                transform: translateY(0);
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-container">
            <a href="../index.html" class="brand-lockup">
                <img src="../assets/logo{logo_ext}" alt="Logo de TODO PARTES HORIZONTE" class="logo-image">
                <div class="brand-text">
                    <h2 class="logo-title">TODO PARTES <span>HORIZONTE</span></h2>
                    <div class="logo-subtitle">Repuestos de las mejores marcas</div>
                </div>
            </a>
            <div class="social-links">
                <a href="{instagram_url}" class="social-btn instagram" target="_blank" rel="noopener noreferrer" title="Síguenos en Instagram">
                    <svg viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.051.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z"/></svg>
                </a>
                <a href="{facebook_url}" class="social-btn facebook" target="_blank" rel="noopener noreferrer" title="Síguenos en Facebook">
                    <svg viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
                </a>
                <a href="{maps_url}" class="social-btn maps" target="_blank" rel="noopener noreferrer" title="Ubicación en Google Maps">
                    <svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
                </a>
                <a href="{reviews_url}" class="social-btn reviews" target="_blank" rel="noopener noreferrer" title="Nuestras Calificaciones en Google">
                    <svg viewBox="0 0 24 24"><path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></svg>
                </a>
            </div>
        </div>
    </header>

    <div class="container">
        <nav aria-label="Breadcrumb">
            <ul class="breadcrumbs">
                <li><a href="../index.html">Inicio</a></li>
                <li><a href="../index.html?categoria={category_slug}">{category}</a></li>
                <li>{description}</li>
            </ul>
        </nav>

        <div class="product-layout">
            <div class="image-card">
                <img src="..{image_path}" alt="{description}" class="product-img">
            </div>

            <div class="details-panel">
                <div class="category-badge">{category}</div>
                <h1 class="product-title">{description}</h1>
                


                <div class="cta-card">
                    <a href="https://wa.me/{whatsapp_number}?text=Hola,%20quisiera%20consultar%20disponibilidad%20y%20precio%20del%20repuesto:%20{url_description}" class="btn btn-whatsapp" target="_blank" rel="noopener noreferrer">
                        <svg viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L0 24l6.335-1.662c1.746.953 3.71 1.455 5.703 1.456h.004c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>
                        Consultar Disponibilidad
                    </a>
                    <button class="btn btn-secondary btn-add" id="btnAddProduct" onclick="addToCart('{id}', '{description}', '{category}', '.{image_path}')">
                        <svg viewBox="0 0 24 24" style="width: 16px; height: 16px; fill: currentColor; margin-right: 8px;"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                        Añadir a la lista de pedido
                    </button>
                    <a href="../index.html" class="btn-back-catalog" style="display: block; text-align: center; margin-top: 10px; color: var(--text-secondary); text-decoration: none; font-size: 13.5px; font-weight: 600; transition: var(--transition);">
                        Volver al Catálogo Completo
                    </a>
                </div>

                <div class="business-info">
                    <h3>Información de Venta</h3>
                    <div class="info-item">
                        <svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
                        <div>
                            <strong>Ubicación:</strong><br>
                            Av. Principal de Boleíta Sur, Caracas, Venezuela.
                        </div>
                    </div>
                    <div class="info-item">
                        <svg viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z"/></svg>
                        <div>
                            <strong>Horario de Atención:</strong><br>
                            Lunes a Viernes: 9:00 AM - 5:00 PM<br>
                            Sábados: 9:00 AM - 1:00 PM
                        </div>
                    </div>
                    <div class="info-item">
                        <svg viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
                        <div>
                            <strong>Contacto Directo:</strong><br>
                            Atención al cliente personalizada y asesoría técnica vía WhatsApp.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <footer>
        <div class="footer-content">
            <div class="footer-col">
                <h4 class="footer-title">TODO PARTES HORIZONTE</h4>
                <p class="footer-text">Somos especialistas en repuestos e importación directa con más de 30 años de trayectoria en Caracas. Brindamos asesoría técnica calificada para asegurar el repuesto correcto para tu vehículo.</p>
            </div>
            <div class="footer-col">
                <h4 class="footer-title">Enlaces Rápidos</h4>
                <ul class="footer-links">
                    <li><a href="../index.html">Catálogo Principal</a></li>
                    <li><a href="../index.html?categoria={category_slug}">Categoría: {category}</a></li>
                    <li><a href="https://wa.me/{whatsapp_number}">Asistencia Técnica</a></li>
                </ul>
            </div>
            <div class="footer-col">
                <h4 class="footer-title">Nuestra Oficina</h4>
                <p class="footer-text">
                    📍 Boleíta Sur, Caracas<br>
                    📞 Teléfono / WhatsApp: +{whatsapp_number}<br>
                    ✉️ RIF: J-50180765-5
                </p>
            </div>
        </div>
        <div class="footer-bottom">
            <p>&copy; 2026 TODO PARTES HORIZONTE. Todos los derechos reservados.</p>
            <p>RIF: J-50180765-5</p>
        </div>
    </footer>
</body>
</html>"""

    generated_pages = 0
    import urllib.parse
    for prod in products:
        try:
            p_id = escape_html(prod.get('id', ''))
            p_slug = escape_html(prod.get('slug', ''))
            
            # Omitir si no hay slug, o si el slug es un UUID, o si coincide con el ID (nombre de foto)
            if not p_slug or uuid_pattern.match(p_slug) or p_slug == p_id:
                continue
                
            safe_filename = f"{p_slug}.html"
                
            desc = to_title_case(escape_html(prod.get('description', 'Repuesto')))
            url_desc = desc.replace(' ', '%20')
            cat = escape_html(prod.get('category', 'Repuestos'))
            img_path = escape_html(prod.get('image_path', ''))
            img_path = img_path.replace('./assets', '/assets')
            cat_slug = re.sub(r'[^a-z0-9]+', '-', cat.lower()).strip('-')
            
            logo_type = "image/png"
            if logo_ext == ".jpg" or logo_ext == ".jpeg":
                logo_type = "image/jpeg"
            elif logo_ext == ".webp":
                logo_type = "image/webp"
            elif logo_ext == ".svg":
                logo_type = "image/svg+xml"
            
            html_content = template.format(
                id=p_id,
                slug=p_slug if p_slug else p_id,
                description=desc,
                url_description=url_desc,
                category=cat,
                category_slug=cat_slug,
                image_path=img_path,
                whatsapp_number=whatsapp_number,
                base_url=base_url,
                safe_filename=safe_filename,
                ga_script=ga_script,
                logo_ext=logo_ext,
                logo_type=logo_type,
                instagram_url=instagram_url,
                facebook_url=facebook_url,
                maps_url=maps_url,
                reviews_url=reviews_url
            )
            
            file_path = p_dir / safe_filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            generated_pages += 1
        except Exception as e:
            print(f"❌ Error al generar pagina para {prod.get('id')}: {e}")
            
    print(f"📄 Páginas estáticas SEO generadas: {generated_pages}")

    # 3. Generar sitemaps divididos (máximo 100 URLs por archivo) + sitemap index
    try:
        from datetime import datetime
        today = datetime.today().strftime('%Y-%m-%d')
        
        # Recopilar todas las URLs válidas de productos
        product_urls = []
        for prod in products:
            prod_id = prod.get("id")
            p_slug = prod.get("slug")
            if prod_id:
                if not p_slug or uuid_pattern.match(p_slug) or p_slug == prod_id:
                    continue
                safe_filename = f"{p_slug}.html"
                product_urls.append(f"{base_url}p/{safe_filename}")
        
        # Dividir en lotes de 100 URLs
        BATCH_SIZE = 100
        batches = [product_urls[i:i + BATCH_SIZE] for i in range(0, len(product_urls), BATCH_SIZE)]
        
        # Limpiar sub-sitemaps anteriores para evitar archivos huérfanos
        for old_file in web_path.glob("sitemap-*.xml"):
            try:
                os.remove(old_file)
            except Exception:
                pass
        
        # Generar sub-sitemaps
        sitemap_filenames = []
        
        # Sitemap 1: páginas principales
        main_sitemap = web_path / "sitemap-main.xml"
        with open(main_sitemap, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
            f.write('  <url>\n')
            f.write(f'    <loc>{base_url}</loc>\n')
            f.write(f'    <lastmod>{today}</lastmod>\n')
            f.write('    <changefreq>daily</changefreq>\n')
            f.write('    <priority>1.0</priority>\n')
            f.write('  </url>\n')
            f.write('  <url>\n')
            f.write(f'    <loc>{base_url}informacion.html</loc>\n')
            f.write(f'    <lastmod>{today}</lastmod>\n')
            f.write('    <changefreq>weekly</changefreq>\n')
            f.write('    <priority>0.9</priority>\n')
            f.write('  </url>\n')
            f.write('</urlset>\n')
        sitemap_filenames.append("sitemap-main.xml")
        
        # Sitemaps de productos en lotes de 100
        for idx, batch in enumerate(batches, start=1):
            filename = f"sitemap-productos-{idx}.xml"
            batch_path = web_path / filename
            with open(batch_path, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
                for prod_url in batch:
                    f.write('  <url>\n')
                    f.write(f'    <loc>{prod_url}</loc>\n')
                    f.write(f'    <lastmod>{today}</lastmod>\n')
                    f.write('    <changefreq>monthly</changefreq>\n')
                    f.write('    <priority>0.8</priority>\n')
                    f.write('  </url>\n')
                f.write('</urlset>\n')
            sitemap_filenames.append(filename)
        
        # Generar sitemap index principal
        sitemap_index_path = web_path / "sitemap.xml"
        with open(sitemap_index_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
            for sm_filename in sitemap_filenames:
                f.write('  <sitemap>\n')
                f.write(f'    <loc>{base_url}{sm_filename}</loc>\n')
                f.write(f'    <lastmod>{today}</lastmod>\n')
                f.write('  </sitemap>\n')
            f.write('</sitemapindex>\n')
        
        total_urls = len(product_urls) + 2
        print(f"🗺️ Sitemap index generado con {len(sitemap_filenames)} sub-sitemaps ({total_urls} URLs totales)")
    except Exception as e:
        print(f"❌ Error al generar sitemaps: {e}")

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
    
    # Manejar copia de logo si está configurado y existe (optimizado)
    logo_path_str = config.get("logo_path", "")
    use_custom_logo = ""
    if logo_path_str:
        logo_file_path = Path(logo_path_str)
        if logo_file_path.exists() and logo_file_path.is_file():
            try:
                logo_ext = logo_file_path.suffix.lower()
                dest_logo_path = assets_dir / f"logo{logo_ext}"
                
                # Optimizar logo para reducir su peso en red
                try:
                    with Image.open(logo_file_path) as img:
                        img.thumbnail((300, 300))
                        img.save(dest_logo_path, optimize=True)
                    print(f"🎨 Logo optimizado y copiado exitosamente a: {dest_logo_path.name}")
                except Exception as img_err:
                    print(f"⚠️ Advertencia: No se pudo optimizar el logo ({img_err}). Copiando archivo original...")
                    shutil.copy2(logo_file_path, dest_logo_path)
                
                use_custom_logo = f"./assets/logo{logo_ext}"
            except Exception as e:
                print(f"❌ Error al copiar el logo: {e}")
        else:
            print(f"⚠️ Advertencia: El archivo de logo en '{logo_path_str}' no existe.")
            
    print(f"🔍 Escaneando carpeta de origen: {source_dir.absolute()}")

    if not source_dir.exists():
        print(f"❌ Error: La carpeta de origen '{source_dir}' no existe.")
        print("💡 Por favor, crea la carpeta o edita config.json con la ruta correcta.")
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
                
    print(f"📂 Se encontraron {len(found_files)} imágenes de repuestos en las subcarpetas.")
    
    # Generar vista previa de calibración de OCR con la primera imagen encontrada
    if found_files:
        first_file_path, _ = found_files[0]
        preview_file_path = assets_dir / "ocr_crop_preview.jpg"
        generate_crop_preview(first_file_path, crop_top, crop_bottom, preview_file_path)
        print(f"👁️ Vista previa de calibración de OCR generada en: {preview_file_path.name}")
        
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
        print(f"⏳ Procesando [{category}] -> {file_path.name}...")
        
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
            print(f"❌ Error al procesar la imagen {file_path.name}. Se omitió.")

    # 2.5 Asegurar slugs únicos para todos los productos
    used_slugs = set()
    # Primero reservamos los slugs existentes para mantener la estabilidad (SEO)
    for prod in updated_products:
        if prod.get("slug"):
            if prod["slug"] not in used_slugs:
                used_slugs.add(prod["slug"])
            else:
                prod["slug"] = None # Colisión, se regenerará
                
    # Generar slugs para los que no tienen
    for prod in updated_products:
        if not prod.get("slug"):
            prod["slug"] = generate_unique_slug(prod["description"], used_slugs)

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
                    print(f"❌ No se pudo eliminar archivo obsoleto {old_webp.name}: {e}")
            deleted_count += 1
            
    print(f"\n📊 Resumen de Sincronización:")
    print(f"  🔹 Omitidas (ya procesadas): {skipped_count}")
    print(f"  🔸 Nuevas procesadas: {new_count}")
    print(f"  🗑️ Eliminadas del catálogo: {deleted_count}")
    print(f"  📦 Total actual en catálogo: {len(updated_products)}")
    
    # Guardar base de datos JSON
    catalog_data = {
        "whatsapp_number": obfuscate_value(whatsapp_number),
        "use_custom_logo": use_custom_logo,
        "instagram_url": obfuscate_value(config.get("instagram_url", "")),
        "facebook_url": obfuscate_value(config.get("facebook_url", "")),
        "maps_url": obfuscate_value(config.get("maps_url", "")),
        "reviews_url": obfuscate_value(config.get("reviews_url", "")),
        "google_analytics_id": obfuscate_value(config.get("google_analytics_id", "")),
        "total_products": len(updated_products),
        "products": updated_products
    }

    write_success = write_catalog_js(catalog_data)
    if write_success:
        print(f"💾 ¡Catálogo JS guardado con éxito en: {js_path}!")
        # Generar sitemap y robots.txt para SEO
        generate_seo_files(updated_products, web_dir)
        inject_preload_images(catalog_data)
        if progress_callback:
            progress_callback(total_files, total_files, "Catálogo generado y guardado con éxito.")
    else:
        print(f"❌ Error al guardar products.js")
        if progress_callback:
            progress_callback(total_files, total_files, "Error al guardar el catálogo JS.")
            
    return newly_processed_ids

def update_js_links(config):
    """Actualiza únicamente los enlaces de contacto en products.js sin escanear imágenes."""
    try:
        data = read_catalog_js()
        if not data:
            return False
            
        data["whatsapp_number"] = obfuscate_value(config.get("whatsapp_number", ""))
        data["instagram_url"] = obfuscate_value(config.get("instagram_url", ""))
        data["facebook_url"] = obfuscate_value(config.get("facebook_url", ""))
        data["maps_url"] = obfuscate_value(config.get("maps_url", ""))
        data["reviews_url"] = obfuscate_value(config.get("reviews_url", ""))
        data["google_analytics_id"] = obfuscate_value(config.get("google_analytics_id", ""))
        
        # Copiar el logo si existe y está configurado (optimizado)
        logo_path_str = config.get("logo_path", "")
        if logo_path_str:
            logo_file_path = Path(logo_path_str)
            if logo_file_path.exists() and logo_file_path.is_file():
                assets_dir = Path("web/assets")
                assets_dir.mkdir(parents=True, exist_ok=True)
                logo_ext = logo_file_path.suffix.lower()
                dest_logo_path = assets_dir / f"logo{logo_ext}"
                try:
                    with Image.open(logo_file_path) as img:
                        img.thumbnail((300, 300))
                        img.save(dest_logo_path, optimize=True)
                    print(f"Logo optimizado y copiado exitosamente a: {dest_logo_path.name}")
                except Exception as img_err:
                    print(f"Advertencia: No se pudo optimizar el logo ({img_err}). Copiando archivo original...")
                    shutil.copy2(logo_file_path, dest_logo_path)
                data["use_custom_logo"] = f"./assets/logo{logo_ext}"
        
        success = write_catalog_js(data)
        if success:
            print("Enlaces y logo actualizados rápidamente en products.js.")
            # Generar sitemap y robots.txt para SEO
            generate_seo_files(data.get("products", []), "web")
            inject_preload_images(data)
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
