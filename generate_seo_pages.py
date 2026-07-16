import os
import json
import base64
import re
from datetime import datetime

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRODUCTS_FILE = os.path.join(BASE_DIR, 'products.js')
P_DIR = os.path.join(BASE_DIR, 'p')
SITEMAP_FILE = os.path.join(BASE_DIR, 'sitemap.xml')

# Asegurarse de que el directorio /p/ existe
if not os.path.exists(P_DIR):
    os.makedirs(P_DIR)

def read_products():
    with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extraer el JSON
    json_str = content.replace('const PRODUCTS_DATA = ', '').strip()
    if json_str.endswith(';'):
        json_str = json_str[:-1]
        
    return json.loads(json_str)

def decode_base64(encoded_str):
    try:
        return base64.b64decode(encoded_str).decode('utf-8')
    except:
        return encoded_str

def escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def get_site_base_url():
    base_url = "https://todoparteshorizonte.com/"
    try:
        config_path = os.path.join(os.path.dirname(BASE_DIR), 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if "base_url" in config and config["base_url"].strip():
                    url = config["base_url"].strip()
                    if not url.endswith("/"):
                        url += "/"
                    return url
    except:
        pass
    return base_url

import sqlite3

def load_db_config_and_prices(products):
    db_path = os.path.join(os.path.dirname(BASE_DIR), 'inventario.db')
    if not os.path.exists(db_path):
        return {}, {}
        
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 1. Load active config
    config = {}
    try:
        row = cursor.execute("SELECT tasa_bcv, tasa_usdt, modo_precio, porcentaje_incremento FROM configuracion WHERE id = 1").fetchone()
        if row:
            config = dict(row)
    except Exception as e:
        print(f"Error loading config from DB: {e}")
        
    # 2. Check if normalized
    is_normalized = False
    try:
        cursor.execute("SELECT id FROM repuestos LIMIT 1")
        is_normalized = True
    except sqlite3.OperationalError:
        pass
        
    # 3. Fetch linked items data
    product_db_data = {}
    
    # Collect all linked ids
    all_linked_ids = []
    for p in products:
        linked = p.get('linked_ids', [])
        if linked:
            all_linked_ids.extend([int(x) for x in linked if str(x).isdigit()])
            
    if all_linked_ids:
        placeholders = ",".join(["?"] * len(all_linked_ids))
        if is_normalized:
            query = f"""
                SELECT 
                    r.id AS id,
                    rv.precio_venta_usd AS precio_venta_usd,
                    rv.existencia AS existencia,
                    r.medida_variante AS medida_variante
                FROM repuestos r
                LEFT JOIN repuesto_variantes rv ON rv.id_repuesto = r.id
                WHERE r.id IN ({placeholders})
            """
        else:
            query = f"""
                SELECT 
                    id,
                    precio_venta_usd,
                    existencia,
                    medida_variante
                FROM inventario
                WHERE id IN ({placeholders})
            """
            
        try:
            # We want unique IDs to avoid duplicate parameters
            unique_linked_ids = list(set(all_linked_ids))
            placeholders = ",".join(["?"] * len(unique_linked_ids))
            query = query.replace(f"IN ({','.join(['?'] * len(all_linked_ids))})", f"IN ({placeholders})")
            rows = cursor.execute(query, unique_linked_ids).fetchall()
            for r in rows:
                p_data = dict(r)
                p_id = p_data['id']
                if p_id not in product_db_data:
                    product_db_data[p_id] = []
                product_db_data[p_id].append(p_data)
        except Exception as e:
            print(f"Error loading products details from DB: {e}")
            
    conn.close()
    return config, product_db_data

def calculate_price_bs(base_price_usd, config):
    mode = config.get('modo_precio', 'USDT')
    bcv = config.get('tasa_bcv', 1.0) or 1.0
    usdt = config.get('tasa_usdt', 1.0) or 1.0
    increment = config.get('porcentaje_incremento', 0.0) or 0.0
    base = float(base_price_usd or 0.0)
    
    if mode == 'INCREMENTO':
        final_usd = round(base * (1.0 + (increment / 100.0)), 2)
        price_bs = round(final_usd * bcv, 2)
    elif mode == 'ESTANDAR':
        price_bs = round(base * bcv, 2)
    else:
        price_bs = round(base * usdt, 2)
        
    return price_bs

def generate_pages(data):
    def to_title_case(text):
        if not text:
            return ""
        def cap_word(w):
            if '-' in w:
                return '-'.join(p.capitalize() for p in w.split('-'))
            return w.capitalize()
        return ' '.join(cap_word(w) for w in text.split())

    def extract_compatibility(desc):
        desc_upper = desc.upper()
        
        # 1. Detectar Vehículos
        vehicles = []
        if "D-MAX" in desc_upper or "DMAX" in desc_upper:
            vehicles.append("Chevrolet Luv D-Max")
        elif "LUV" in desc_upper:
            vehicles.append("Chevrolet Luv")
        
        if "CARIBE" in desc_upper:
            vehicles.append("Isuzu Caribe 442")
        if "RODEO" in desc_upper:
            vehicles.append("Isuzu Rodeo")
        if "TROOPER" in desc_upper:
            vehicles.append("Isuzu Trooper")
            
        if not vehicles:
            if "ISUZU" in desc_upper:
                vehicles.append("Isuzu")
            elif "CHEVROLET" in desc_upper:
                vehicles.append("Chevrolet")
            else:
                vehicles.append("Chevrolet / Isuzu")

        # 2. Detectar Motorización
        engines = []
        # Buscar patrones de motores decimales (1.0L a 6.0L)
        motor_matches = re.findall(r'\b([1-5]\.\d|6\.0)\b', desc_upper)
        for m in motor_matches:
            engines.append(f"Motor {m}L")
            
        # Buscar códigos de Caribe/Luv
        if "G-200" in desc_upper or "G200" in desc_upper:
            if "G-2000" not in desc_upper and "G2000" not in desc_upper:
                engines.append("Motor G200 (2.0L)")
        if "G-2000" in desc_upper or "G2000" in desc_upper:
            engines.append("Motor G2000 (2.0L)")
            
        if "2000" in desc_upper and "G-2000" not in desc_upper and "G2000" not in desc_upper:
            if "CARIBE" in desc_upper:
                engines.append("Motor 2.0L (2000 cc)")
        if "2300" in desc_upper:
            engines.append("Motor 2.3L (2300 cc)")
        if "2600" in desc_upper:
            engines.append("Motor 2.6L (2600 cc)")
            
        engine_str = " / ".join(engines) if engines else None

        # 3. Detectar Años
        years = []
        # Rangos de 2 o 4 dígitos (ej. 83-88, 1983-1988, 97-02, 05-14)
        range_match = re.search(r'\b(\d{2,4})-(\d{2,4})\b', desc_upper)
        if range_match:
            y1, y2 = range_match.groups()
            y1_full = y1 if len(y1) == 4 else (f"19{y1}" if int(y1) > 50 else f"20{y1}")
            y2_full = y2 if len(y2) == 4 else (f"19{y2}" if int(y2) > 50 else f"20{y2}")
            years.append(f"{y1_full} - {y2_full}")
        else:
            # Años sueltos de 4 dígitos
            year_matches = re.findall(r'\b(19\d{2}|20\d{2})\b', desc_upper)
            filtered_years = []
            for y in year_matches:
                if y in ["2000", "2300", "2600"] and "CARIBE" in desc_upper:
                    continue
                filtered_years.append(y)
            if filtered_years:
                years.append(", ".join(filtered_years))
                
        year_str = years[0] if years else None
        
        return {
            "vehicles": " / ".join(vehicles),
            "vehicles_list": vehicles,
            "engines": engine_str,
            "years": year_str
        }

    def get_related_products_html(current_product, all_products, base_url):
        import random
        import html
        current_id = current_product.get('id')
        current_cat = current_product.get('category', '')
        current_desc = current_product.get('description', '')
        
        # Extraer compatibilidad del producto actual
        current_compat = extract_compatibility(current_desc)
        current_vehicles = set(current_compat["vehicles_list"])
        
        # Categorizar por prioridad
        priority_1 = [] # Misma Categoría Y Mismo Vehículo
        priority_2 = [] # Misma Categoría
        priority_3 = [] # Mismo Vehículo
        priority_4 = [] # Resto
        
        uuid_pattern = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
        
        for p in all_products:
            p_id = p.get('id')
            if p_id == current_id:
                continue
                
            p_slug = p.get('slug')
            if not p_slug or uuid_pattern.match(p_slug) or p_slug == p_id:
                continue
                
            p_cat = p.get('category', '')
            p_desc = p.get('description', '')
            p_compat = extract_compatibility(p_desc)
            p_vehicles = set(p_compat["vehicles_list"])
            
            same_category = (p_cat == current_cat)
            same_vehicle = not current_vehicles.isdisjoint(p_vehicles)
            
            if same_category and same_vehicle:
                priority_1.append(p)
            elif same_category:
                priority_2.append(p)
            elif same_vehicle:
                priority_3.append(p)
            else:
                priority_4.append(p)
                
        # Barajar de forma determinista usando el ID como semilla
        try:
            seed_val = int(current_id)
        except:
            seed_val = hash(str(current_id))
            
        rng = random.Random(seed_val)
        rng.shuffle(priority_1)
        rng.shuffle(priority_2)
        rng.shuffle(priority_3)
        rng.shuffle(priority_4)
        
        candidates = (priority_1 + priority_2 + priority_3 + priority_4)[:4]
        
        html_cards = []
        for p in candidates:
            p_slug = p.get('slug')
            p_desc = p.get('description', '')
            p_cat = p.get('category', '')
            p_img = p.get('image_path', '').replace('./assets', '/assets')
            p_oem_raw = p.get('oem', '')
            
            p_oem = [part.strip() for part in re.split(r'[/,]', p_oem_raw) if part.strip()]
            oem_text = p_oem[0] if p_oem else ""
            
            oem_badge = f'<div class="related-oem">OEM: {html.escape(oem_text)}</div>' if oem_text else ""
            
            # Escapar valores para HTML
            escaped_desc = html.escape(p_desc)
            escaped_cat = html.escape(p_cat)
            
            card_html = f"""
                <a href="./{p_slug}.html" class="related-card">
                    <div class="related-img-wrapper">
                        <img src="..{p_img}" alt="Repuesto {escaped_desc} original" class="related-img" loading="lazy" width="200" height="170">
                    </div>
                    <div class="related-content">
                        <span class="category-badge" style="margin-bottom: 4px; align-self: flex-start; display: block;"><span style="font-size: 10px; padding: 2px 8px; line-height: 1.2;">{escaped_cat}</span></span>
                        <div class="related-title" title="{escaped_desc}">{escaped_desc}</div>
                        {oem_badge}
                        <div class="related-footer">
                            <span>Ver Detalle</span>
                            <svg viewBox="0 0 24 24" style="width: 14px; height: 14px; fill: currentColor;"><path d="M5 13h11.86l-5.43 5.43 1.42 1.42L21.14 12l-8.29-8.29-1.42 1.42L16.86 11H5v2z"/></svg>
                        </div>
                    </div>
                </a>"""
            html_cards.append(card_html)
            
        return "\n".join(html_cards)

    GOOGLE_REVIEWS = [
        {"author": "Olimpo González", "body": "Gracias por sus servicios. Los recomiendo. Compré los repuestos de mi camioneta luv dmax y todo de calidad."},
        {"author": "Ramon Villarroel", "body": "Excelente atención al cliente son lo máximo en repuestos. Todos los repuestos de mi caribe nuevos, los felicito sigan así confiando en Venezuela."},
        {"author": "Santos Marquez Valera", "body": "Muy buena atención. Repuestos de calidad..."},
        {"author": "Luis Rejon", "body": "Todo para mi dmax a la mano buena atención y rápida respuesta"},
        {"author": "Wences Rodríguez", "body": "Puedo decir que hay mucha responsabilidad en el servicio y buena atención. Excelente."},
        {"author": "José Manuel Madriz Diaz", "body": "Excelente repuestos para vehículos."}
    ]

    products = data.get('products', [])
    whatsapp_encoded = data.get('whatsapp_number', '')
    whatsapp_number = decode_base64(whatsapp_encoded)
    
    instagram_encoded = data.get('instagram_url', '')
    instagram_url = decode_base64(instagram_encoded)
    facebook_encoded = data.get('facebook_url', '')
    facebook_url = decode_base64(facebook_encoded)
    maps_encoded = data.get('maps_url', '')
    maps_url = decode_base64(maps_encoded)
    reviews_encoded = data.get('reviews_url', '')
    reviews_url = decode_base64(reviews_encoded)
    ga_encoded = data.get('google_analytics_id', '')
    ga_id = decode_base64(ga_encoded)
    
    base_url = get_site_base_url()
    
    # Usar logo .webp por defecto con fallback en el HTML
    logo_ext = ".webp"
    logo_type = "image/webp"
        
    ga_script = ""
    if ga_id:
        ga_script = f"""
    <!-- Google Analytics Diferido para TBT -->
    <script>
      window.addEventListener('load', function() {{
        setTimeout(function() {{
          var script = document.createElement('script');
          script.async = true;
          script.src = 'https://www.googletagmanager.com/gtag/js?id={ga_id}';
          document.head.appendChild(script);
          
          window.dataLayer = window.dataLayer || [];
          window.gtag = function() {{ window.dataLayer.push(arguments); }};
          gtag('js', new Date());
          gtag('config', '{ga_id}');
        }}, 1500);
      }});
    </script>"""
    
    template = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://static.cloudflareinsights.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://www.google-analytics.com https://analytics.google.com https://stats.g.doubleclick.net https://cloudflareinsights.com;">
    <title>{title_description}</title>
    <meta name="description" content="{meta_description}">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{base_url}p/{clean_filename}">
    <link rel="shortcut icon" href="../favicon.ico" type="image/x-icon">
    <link rel="icon" href="../favicon.ico" type="image/x-icon">
    <link rel="icon" href="../assets/favicon-32x32.png" type="image/png" sizes="32x32">
    <link rel="icon" href="../assets/favicon-48x48.png" type="image/png" sizes="48x48">
    <link rel="icon" href="../assets/favicon-96x96.png" type="image/png" sizes="96x96">
    <link rel="icon" href="../assets/favicon-192x192.png" type="image/png" sizes="192x192">
    <link rel="apple-touch-icon" href="../assets/apple-touch-icon.png">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{title_description}">
    <meta property="og:site_name" content="Todo Partes Horizonte">
    <meta property="og:description" content="{meta_description}">
    <meta property="og:image" content="{image_url_seo}">
    <meta property="og:url" content="{base_url}p/{clean_filename}">
    <meta property="og:type" content="product">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title_description}">
    <meta name="twitter:description" content="{meta_description}">
    <meta name="twitter:image" content="{image_url_seo}">
    
    <!-- JSON-LD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org/",
      "@type": "Product",
      "name": "{description}",
      "image": "{image_url_seo}",
      "description": "{schema_description}",
      "sku": "{sku}",
      "mpn": {mpn_code},
      "brand": {{
        "@type": "Brand",
        "name": "{brand_schema_name}"
      }},
      "itemCondition": "https://schema.org/NewCondition",
      {schema_compatibility_json}
      "offers": {{
        "@type": "Offer",
        "price": "{price_bs}",
        "priceCurrency": "VES",
        "availability": "{availability}",
        "url": "{base_url}p/{clean_filename}",
        "seller": {{
          "@type": "AutoPartsStore",
          "@id": "{base_url}#store",
          "name": "Todo Partes Horizonte",
          "telephone": "+{whatsapp_number}",
          "url": "{base_url}",
          "image": "{base_url}assets/logo{logo_ext}",
          "priceRange": "$$",
          "address": {{
            "@type": "PostalAddress",
            "streetAddress": "Av. Principal de Boleíta Sur",
            "addressLocality": "Caracas",
            "addressRegion": "Miranda",
            "addressCountry": "VE"
          }}
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
          "merchantReturnDays": 10,
          "returnMethod": "https://schema.org/ReturnByMail",
          "returnFees": "https://schema.org/ReturnShippingFees",
          "returnShippingFeesAmount": {{
            "@type": "MonetaryAmount",
            "value": "5.00",
            "currency": "USD"
          }}
        }}
      }},
      "aggregateRating": {{
        "@type": "AggregateRating",
        "ratingValue": "4.8",
        "reviewCount": "87"
      }},
      "review": {{
        "@type": "Review",
        "author": {{
          "@type": "Person",
          "name": "{review_author}"
        }},
        "reviewRating": {{
          "@type": "Rating",
          "ratingValue": "5"
        }},
        "reviewBody": "{review_body}"
      }}
    }}
    </script>
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
        {{
          "@type": "Question",
          "name": "¿Tienen disponibilidad de este repuesto {description}?",
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": "Sí, contamos con disponibilidad en almacén de {description} en Caracas. Te recomendamos contactarnos por WhatsApp para confirmar stock y coordinar tu entrega o retiro personal."
          }}
        }},
        {{
          "@type": "Question",
          "name": "¿Dónde puedo comprar este repuesto en Caracas?",
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": "Puedes retirar tu repuesto en nuestra sede física ubicada en Boleíta Sur, Caracas. También realizamos envíos nacionales cobro en destino."
          }}
        }},
        {{
          "@type": "Question",
          "name": "¿Hacen envíos al interior de Venezuela?",
          "acceptedAnswer": {{
            "@type": "Answer",
            "text": "Sí, hacemos envíos a nivel nacional a través de agencias de encomienda confiables como Zoom, Tealca y MRW con cobro en destino."
          }}
        }}
      ]
    }}
    </script>
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "BreadcrumbList",
      "itemListElement": [
        {{
          "@type": "ListItem",
          "position": 1,
          "name": "Inicio",
          "item": "{base_url}"
        }},
        {{
          "@type": "ListItem",
          "position": 2,
          "name": "{category}",
          "item": "{base_url}index.html?categoria={category_slug}"
        }},
        {{
          "@type": "ListItem",
          "position": 3,
          "name": "{description}",
          "item": "{base_url}p/{clean_filename}"
        }}
      ]
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

        /* Ocultar flecha nativa de details/summary para el desplegable de OEM */
        .oem-details summary::-webkit-details-marker {{
            display: none !important;
        }}
        .oem-details summary {{
            list-style: none !important;
            outline: none;
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
                align-items: flex-start;
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
            display: block;
        }}
        .category-badge span {{
            display: inline;
            background: rgba(255, 106, 0, 0.1);
            border: 1px solid var(--accent-orange);
            color: var(--accent-orange);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            padding: 6px 14px;
            border-radius: 20px;
            letter-spacing: 0.8px;
            box-decoration-break: clone;
            -webkit-box-decoration-break: clone;
            line-height: 1.2;
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
            background: rgba(255, 255, 255, 0.01);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 14px;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: var(--glass-shadow);
        }}

        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 15px 24px;
            border-radius: 14px;
            font-size: 15px;
            font-weight: 700;
            text-decoration: none;
            transition: var(--transition);
            cursor: pointer;
            text-align: center;
            border: none;
            outline: none;
        }}

        .btn-whatsapp {{
            background: linear-gradient(135deg, #25d366 0%, #128c7e 100%);
            color: #fff;
            box-shadow: 0 4px 15px rgba(37, 211, 102, 0.15);
        }}

        .btn-whatsapp:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(37, 211, 102, 0.3);
            background: linear-gradient(135deg, #2ee070 0%, #179b8d 100%);
        }}

        .btn-whatsapp svg {{
            width: 20px;
            height: 20px;
            fill: currentColor;
        }}

        .btn-secondary {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 106, 0, 0.3);
            color: #fff;
        }}

        .btn-secondary:hover {{
            background: rgba(255, 106, 0, 0.06);
            border-color: var(--accent-orange);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(255, 106, 0, 0.1);
        }}

        .business-info {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
            margin-top: 24px;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: var(--glass-shadow);
        }}

        .business-info h3 {{
            grid-column: 1 / -1;
            font-size: 15px;
            font-weight: 700;
            color: #fff;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            border-left: 3px solid var(--accent-orange);
            padding-left: 10px;
            margin: 0 0 4px 0;
        }}

        @media (min-width: 768px) {{
            .business-info {{
                grid-template-columns: repeat(3, 1fr);
                gap: 28px;
                margin-top: 32px;
            }}
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

        .compatibility-card {{
            background: rgba(255, 255, 255, 0.01);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            margin-bottom: 8px;
            text-align: left;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: var(--glass-shadow);
        }}

        .compatibility-card h3 {{
            font-size: 13.5px;
            font-weight: 700;
            color: #fff;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            border-left: 3px solid var(--accent-orange);
            padding-left: 10px;
            margin: 0 0 4px 0;
        }}

        .comp-item {{
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            font-size: 13px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            padding-bottom: 12px;
            gap: 8px;
        }}

        .comp-item:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}

        .comp-label {{
            color: var(--text-secondary);
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            flex-shrink: 0;
            width: auto;
        }}

        .comp-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: flex-start;
        }}

        .tag-capsule {{
            display: inline-flex;
            align-items: center;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 12.5px;
            font-weight: 600;
            letter-spacing: 0.2px;
            transition: var(--transition);
        }}

        .vehicle-tag {{
            background: rgba(255, 106, 0, 0.04);
            border: 1px solid rgba(255, 106, 0, 0.2);
            color: #ff914d;
        }}

        .vehicle-tag:hover {{
            background: rgba(255, 106, 0, 0.1);
            border-color: rgba(255, 106, 0, 0.4);
            transform: translateY(-1px);
        }}

        .engine-tag {{
            background: rgba(37, 211, 102, 0.04);
            border: 1px solid rgba(37, 211, 102, 0.2);
            color: #4ade80;
        }}

        .engine-tag:hover {{
            background: rgba(37, 211, 102, 0.1);
            border-color: rgba(37, 211, 102, 0.4);
            transform: translateY(-1px);
        }}

        .year-tag {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: var(--text-secondary);
        }}

        .year-tag:hover {{
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(255, 255, 255, 0.15);
            color: #ffffff;
            transform: translateY(-1px);
        }}

        .description-card {{
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            border: 0;
        }}

        .faq-section {{
            background: transparent;
            padding: 0;
            margin-top: 48px;
            margin-bottom: 24px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}

        .faq-section h3 {{
            font-size: 18px;
            font-weight: 800;
            color: #fff;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            border-left: 3px solid var(--accent-orange);
            padding-left: 12px;
            margin: 0;
            text-align: left;
        }}

        .faq-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 16px;
        }}

        @media (min-width: 768px) {{
            .faq-grid {{
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
            }}
        }}

        .faq-item {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            text-align: left;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            transition: var(--transition);
        }}

        .faq-item:hover {{
            transform: translateY(-2px);
            border-color: rgba(255, 106, 0, 0.2);
            box-shadow: 0 8px 30px rgba(255, 106, 0, 0.05);
        }}

        .faq-question {{
            font-size: 14px;
            font-weight: 700;
            color: #fff;
            margin: 0;
            display: flex;
            align-items: flex-start;
            gap: 8px;
            line-height: 1.4;
        }}

        .faq-question::before {{
            content: "?";
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: rgba(255, 106, 0, 0.15);
            color: var(--accent-orange);
            font-size: 11px;
            font-weight: 800;
            flex-shrink: 0;
            margin-top: 1px;
        }}

        .faq-answer {{
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.6;
            margin: 0;
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
            height: 56px;
            border-radius: 28px;
            background: var(--accent-green);
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            box-shadow: 0 6px 20px rgba(37, 211, 102, 0.4);
            cursor: pointer;
            z-index: 90;
            transition: max-width 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), padding 0.4s ease, background-color 0.3s ease, transform 0.3s ease, box-shadow 0.3s ease;
            text-decoration: none;
            max-width: 56px;
            padding: 0 14px;
            box-sizing: border-box;
            overflow: hidden;
            white-space: nowrap;
        }}
        .fab-whatsapp:hover {{
            background: var(--accent-green-hover);
            transform: scale(1.05) translateY(-3px);
            box-shadow: 0 8px 25px rgba(37, 211, 102, 0.5);
        }}
        .fab-whatsapp svg {{
            width: 28px;
            height: 28px;
            fill: #ffffff;
            flex-shrink: 0;
        }}
        .fab-whatsapp-text {{
            margin-left: 8px;
            font-size: 13px;
            font-weight: 700;
            opacity: 0;
            transition: opacity 0.2s ease;
            display: inline-block;
            vertical-align: middle;
        }}
        .fab-whatsapp.expanded {{
            max-width: 280px;
            padding: 0 20px;
        }}
        .fab-whatsapp.expanded .fab-whatsapp-text {{
            opacity: 1;
            transition: opacity 0.3s ease 0.1s;
        }}
        @media (max-width: 768px) {{
            .fab-whatsapp.expanded {{
                max-width: 56px;
                padding: 0 14px;
            }}
            .fab-whatsapp.expanded .fab-whatsapp-text {{
                display: none !important;
                opacity: 0 !important;
            }}
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
        .btn-back-catalog {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            margin-top: 12px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 13.5px;
            font-weight: 600;
            transition: var(--transition);
        }}

        .btn-back-catalog::before {{
            content: "←";
            transition: transform 0.3s ease;
        }}

        .btn-back-catalog:hover {{
            color: var(--accent-orange) !important;
        }}

        .btn-back-catalog:hover::before {{
            transform: translateX(-4px);
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

        /* Repuestos Relacionados */
        .related-section {{
            margin-top: 40px;
            padding-top: 30px;
            border-top: 1px solid var(--border-color);
        }}
        .related-section h3 {{
            font-size: 20px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 24px;
            color: #ffffff;
        }}
        .related-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
        }}
        .related-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: var(--transition);
            text-decoration: none;
            color: inherit;
        }}
        .related-card:hover {{
            transform: translateY(-4px);
            border-color: var(--accent-orange);
            box-shadow: 0 8px 25px rgba(255, 106, 0, 0.1);
        }}
        .related-img-wrapper {{
            position: relative;
            width: 100%;
            padding-top: 85%;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.02);
        }}
        .related-img {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: contain;
            padding: 8px;
            box-sizing: border-box;
            transition: var(--transition);
        }}
        .related-card:hover .related-img {{
            transform: scale(1.03);
        }}
        .related-content {{
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            flex-grow: 1;
        }}
        .related-title {{
            font-size: 14px;
            font-weight: 700;
            color: var(--text-primary);
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            text-overflow: ellipsis;
            height: 38px;
        }}
        .related-oem {{
            font-family: monospace;
            font-size: 11px;
            color: var(--text-secondary);
            background: rgba(255, 106, 0, 0.05);
            padding: 2px 8px;
            border-radius: 4px;
            border: 1px solid rgba(255, 106, 0, 0.15);
            align-self: flex-start;
        }}
        .related-footer {{
            margin-top: auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12px;
            font-weight: 600;
            color: var(--accent-orange);
            padding-top: 8px;
        }}
        @media (max-width: 1024px) {{
            .related-grid {{
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
            }}
        }}
        @media (max-width: 768px) {{
            .related-grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
            }}
            .related-content {{
                padding: 10px;
            }}
            .related-title {{
                font-size: 11.5px;
                height: 32px;
            }}
            .related-oem {{
                font-size: 9px;
                padding: 1px 4px;
            }}
            .related-footer {{
                font-size: 10.5px;
            }}
            .related-content .category-badge span {{
                font-size: 8.5px !important;
                padding: 2px 6px !important;
                line-height: 1.1;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-container">
            <a href="../index.html" class="brand-lockup">
                <img src="../assets/logo{logo_ext}" alt="Logo de TODO PARTES HORIZONTE" class="logo-image" onerror="this.onerror=null; this.src='../assets/logo.png';">
                <div class="brand-text">
                    <div class="logo-title">TODO PARTES <span>HORIZONTE</span></div>
                    <div class="logo-subtitle">Repuestos Isuzu en Caracas</div>
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
                <img src="..{image_path}" alt="{image_alt}" class="product-img">
            </div>

            <div class="details-panel">
                <div class="category-badge"><span>{category}</span></div>
                <h1 class="product-title">{description}</h1>
                <div class="product-rating" style="display: flex; align-items: center; gap: 6px; font-size: 13.5px; color: var(--text-secondary); margin-top: -8px; margin-bottom: 12px;">
                    <span style="color: #ff9800; font-size: 14px;">⭐⭐⭐⭐⭐</span>
                    <strong style="color: #ffffff;">4.8</strong>
                    <span style="color: var(--text-muted);">|</span>
                    <a href="{reviews_url}" target="_blank" rel="noopener noreferrer" style="color: var(--text-secondary); text-decoration: none; border-bottom: 1px dashed rgba(255,255,255,0.2); transition: var(--transition);" onmouseover="this.style.color='var(--accent-orange)'" onmouseout="this.style.color='var(--text-secondary)'">87 valoraciones en Google</a>
                </div>
                {oem_html}
                
                <!-- Ficha de Compatibilidad -->
                {compatibility_card}

                <!-- Ficha Técnica (Medidas) -->
                {specs_card}

                <!-- Descripción del Producto -->
                {description_card}

                <div class="cta-card">
                    <a href="https://wa.me/{whatsapp_number}?text=Hola,%20quisiera%20consultar%20disponibilidad%20y%20precio%20del%20repuesto:%20{url_description}" class="btn btn-whatsapp" target="_blank" rel="noopener noreferrer">
                        <svg viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L0 24l6.335-1.662c1.746.953 3.71 1.455 5.703 1.456h.004c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>
                        Consultar Disponibilidad
                    </a>
                    <button class="btn btn-secondary btn-add" id="btnAddProduct" onclick="addToCart('{id}', '{description}', '{category}', '.{image_path}')">
                        <svg viewBox="0 0 24 24" style="width: 16px; height: 16px; fill: currentColor; margin-right: 8px;"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
                        Añadir a la lista de pedido
                    </button>
                    <a href="../index.html" class="btn-back-catalog">
                        Volver al Catálogo Completo
                    </a>
                </div>

            </div>
        </div>

        <div class="business-info">
            <h3>Información de Venta</h3>
            <div class="info-item">
                <svg viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
                <div>
                    <strong>Ubicación</strong><br>
                    Av. Principal de Boleíta Sur, Caracas, Venezuela.
                </div>
            </div>
            <div class="info-item">
                <svg viewBox="0 0 24 24"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z"/></svg>
                <div>
                    <strong>Horario de Atención</strong><br>
                    Lunes a Viernes: 9:00 AM - 5:00 PM<br>
                    Sábados: 9:00 AM - 1:00 PM
                </div>
            </div>
            <div class="info-item">
                <svg viewBox="0 0 24 24"><path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z"/></svg>
                <div>
                    <strong>Contacto Directo</strong><br>
                    Atención al cliente personalizada y asesoría técnica vía WhatsApp.
                </div>
            </div>
        </div>

        <!-- PREGUNTAS FRECUENTES -->
        <div class="faq-section">
            <h3>Preguntas Frecuentes sobre {description}</h3>
            <div class="faq-grid">
                <div class="faq-item">
                    <h4 class="faq-question">¿Tienen disponibilidad del repuesto {description}?</h4>
                    <p class="faq-answer">Sí, contamos con stock de este repuesto en Caracas. Te sugerimos confirmar disponibilidad exacta de forma rápida haciendo clic en el botón de WhatsApp.</p>
                </div>
                <div class="faq-item">
                    <h4 class="faq-question">¿Dónde puedo retirar la pieza?</h4>
                    <p class="faq-answer">Puedes retirar tu pedido personalmente en nuestra oficina comercial en Boleíta Sur, Caracas. También realizamos envíos a nivel nacional.</p>
                </div>
                <div class="faq-item">
                    <h4 class="faq-question">¿Qué métodos de envío manejan para el interior de Venezuela?</h4>
                    <p class="faq-answer">Realizamos envíos cobro en destino a todo el país a través de agencias de encomienda confiables como Zoom, Tealca y MRW.</p>
                </div>
            </div>
        </div>
        
        <!-- PRODUCTOS RELACIONADOS -->
        <div class="related-section">
            <h3>Repuestos Relacionados</h3>
            <div class="related-grid">
                {related_products}
            </div>
        </div>
    </div>

    <footer>
        <div class="footer-content">
            <div class="footer-col">
                <h4 class="footer-title">TODO PARTES HORIZONTE</h4>
                <p class="footer-text">Somos una tienda de repuestos encargada de vender autopartes de alta calidad para vehículos Chevrolet e Isuzu (Caribe, Trooper, Rodeo, Luv y Luv D-Max) con más de 30 años de trayectoria en Caracas. Brindamos asesoría técnica calificada para asegurar el repuesto correcto para tu vehículo.</p>
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
                <p class="footer-text" style="display: flex; flex-direction: column; gap: 8px;">
                    <span><svg viewBox="0 0 24 24" style="width: 14px; height: 14px; fill: var(--accent-orange); display: inline-block; vertical-align: middle; margin-right: 6px;"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>Boleíta Sur, Caracas</span>
                    <span><svg viewBox="0 0 24 24" style="width: 14px; height: 14px; fill: var(--accent-orange); display: inline-block; vertical-align: middle; margin-right: 6px;"><path d="M6.62 10.79c1.44 2.83 3.76 5.14 6.59 6.59l2.2-2.2c.27-.27.67-.36 1.02-.24 1.12.37 2.33.57 3.57.57.55 0 1 .45 1 1V20c0 .55-.45 1-1 1-9.39 0-17-7.61-17-17 0-.55.45-1 1-1h3.5c.55 0 1 .45 1 1 0 1.25.2 2.45.57 3.57.11.35.03.74-.25 1.02l-2.2 2.2z"/></svg>Teléfono / WhatsApp: +{whatsapp_number}</span>
                    <span><svg viewBox="0 0 24 24" style="width: 14px; height: 14px; fill: var(--accent-orange); display: inline-block; vertical-align: middle; margin-right: 6px;"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>RIF: J-50180765-5</span>
                </p>
            </div>
        </div>
            <p>RIF: J-50180765-5 · Especialistas Isuzu</p>
        </div>
    </footer>
</body>
</html>"""

    # Clean up P_DIR from old html files to prevent orphaned pages
    if os.path.exists(P_DIR):
        print("[INFO] Limpiando paginas huerfanas en /p/...")
        for filename in os.listdir(P_DIR):
            if filename.endswith('.html'):
                try:
                    os.remove(os.path.join(P_DIR, filename))
                except Exception:
                    pass

    db_config, db_products = load_db_config_and_prices(products)

    for product in products:
        p_id = escape_html(product.get('id', ''))
        p_slug = escape_html(product.get('slug', ''))
        
        # Usar el slug para el nombre del archivo si existe, sino fallback al ID
        if p_slug:
            safe_filename = f"{p_slug}.html"
        else:
            safe_filename = p_id.replace(' ', '%20') + '.html'
            if '%' not in safe_filename and ' ' in p_id:
                safe_filename = p_id.replace(' ', '_') + '.html' # Fallback
        desc = to_title_case(escape_html(product.get('description', 'Repuesto')))
        url_desc = desc.replace(' ', '%20')
        cat = escape_html(product.get('category', 'Repuestos'))
        img_path = escape_html(product.get('image_path', ''))
        
        # Clean image path so it is relative from /p/ (image path in js is ./assets/...)
        img_path = img_path.replace('./assets', '/assets')
        cat_slug = re.sub(r'[^a-z0-9]+', '-', cat.lower()).strip('-')
        
        import urllib.parse
        filename = img_path.split('/')[-1]
        image_url_seo = f"{base_url.rstrip('/')}/assets/{urllib.parse.quote(filename)}"
        
        # OEM para SEO (extraer aquí para uso en títulos y metas)
        p_oem_raw = product.get('oem', '').strip()
        
        # Procesar múltiples códigos OEM si están separados por '/' o ','
        oem_list_raw = []
        if p_oem_raw:
            oem_list_raw = [part.strip() for part in re.split(r'[/,]', p_oem_raw) if part.strip()]
            
        # Para el buscador y SEO de Google es mejor indexar sin guiones
        oem_list_seo = [part.replace('-', '').replace(' ', '') for part in oem_list_raw]
        
        # Usar únicamente el primer código OEM (el principal) para los límites rígidos de Título y Meta Descripción
        p_oem_seo_main = oem_list_seo[0] if oem_list_seo else ""
        
        # Consultar variantes del repuesto en la BD para calcular precios en Bs.
        linked_ids = product.get('linked_ids', [])
        variant_prices_bs = []
        medidas = []
        has_stock = False
        
        for lid in linked_ids:
            lid_key = int(lid) if str(lid).isdigit() else lid
            db_vars = db_products.get(lid_key, [])
            for db_var in db_vars:
                precio_usd = db_var.get('precio_venta_usd') or 0.0
                price_bs = calculate_price_bs(precio_usd, db_config)
                variant_prices_bs.append(price_bs)
                
                existencia = db_var.get('existencia') or 0.0
                if existencia > 0:
                    has_stock = True
                    
                medida = db_var.get('medida_variante')
                if medida and str(medida).strip():
                    medidas.append(str(medida).strip())
                    
        # Seleccionar el precio máximo en Bs.
        max_price_bs = max(variant_prices_bs) if variant_prices_bs else 0.0
        price_bs_str = f"{max_price_bs:.2f}"
        availability_str = "https://schema.org/InStock"
        
        # Construcción de textos optimizados para SEO sin marcas
        # --- TÍTULO (30-60 chars) ---
        title_candidates = []
        if p_oem_seo_main:
            title_candidates.append(f"{desc} {p_oem_seo_main} | Repuestos")
            title_candidates.append(f"{desc} {p_oem_seo_main}")
        title_candidates.append(f"{desc} | Repuestos")
        title_candidates.append(desc)
        
        title_description = None
        for candidate in title_candidates:
            if len(candidate) <= 60:
                title_description = candidate
                break
        
        if title_description is None:
            title_description = desc[:56] + "..."
            
        if len(title_description) < 30:
            extras = [" | Todo Partes Horizonte", " | Todo Partes", " | TPH"]
            for extra in extras:
                if len(title_description) + len(extra) <= 60:
                    title_description += extra
                    break
        
        # --- META DESCRIPCIÓN (120-158 chars) ---
        desc_limite = desc[:60] + "..." if len(desc) > 60 else desc
        oem_meta_part = f" Código OEM: {p_oem_seo_main}." if p_oem_seo_main else ""
        
        meta_base_with_oem = f"Compra {desc_limite}.{oem_meta_part} Repuestos originales en Caracas. Envíos nacionales."
        meta_base_no_oem = f"Compra {desc_limite}. Repuestos originales en Caracas. Envíos nacionales."
        schema_description = f"Compra {desc_limite} original en Caracas.{oem_meta_part} Repuestos con envíos nacionales."
        
        if len(meta_base_with_oem) <= 158:
            meta_description = meta_base_with_oem
        else:
            meta_description = meta_base_no_oem
            
        fillers = [
            " Especialistas en autopartes de alta calidad.",
            " Contamos con tienda física y entregas personales.",
            " Consulta disponibilidad y precio vía WhatsApp.",
            " Atención personalizada para tu vehículo."
        ]
        for filler in fillers:
            if len(meta_description) < 120 and len(meta_description) + len(filler) <= 158:
                meta_description += filler
        
        if len(meta_description) > 158:
            meta_description = meta_description[:155] + "..."
            
        image_alt = f"Fotografía de repuesto {desc} original - Todo Partes Horizonte"
        
        compat = extract_compatibility(desc)
        
        # Inteligencia de Marca para SEO
        desc_lower = desc.lower()
        brands = []
        if 'caribe' in desc_lower or 'trooper' in desc_lower or 'rodeo' in desc_lower or 'isuzu' in desc_lower:
            brands.append("Isuzu")
        if 'luv' in desc_lower or 'd-max' in desc_lower or 'chevrolet' in desc_lower:
            brands.append("Chevrolet")
            
        brand_schema_name = " / ".join(brands) if brands else "Original"
        brand_name = " y ".join(brands) if brands else ""
        brand_title = f" para {brand_name}" if brands else ""

        # Construir JSON-LD schema_compatibility_json dinámicamente
        schema_vehicles = []
        for v in compat["vehicles_list"]:
            vehicle_props = [
                f'        "@type": "Vehicle"',
                f'        "name": "{v}"'
            ]
            if compat["engines"]:
                vehicle_props.append(f'        "vehicleEngine": {{\n          "@type": "EngineSpecification",\n          "name": "{compat["engines"]}"\n        }}')
            if compat["years"]:
                vehicle_props.append(f'        "modelDate": "{compat["years"]}"')
                
            schema_vehicles.append(f'{{\n' + ',\n'.join(vehicle_props) + '\n      }')
            
        schema_compatibility_json = '"isAccessoryOrSparePartFor": [\n      ' + ',\n      '.join(schema_vehicles) + '\n    ],'
        
        # Construir Ficha de Compatibilidad HTML dinámicamente
        compat_rows = []
        if compat["vehicles_list"]:
            vehicle_tags = "".join([f'<span class="tag-capsule vehicle-tag">{v}</span>' for v in compat["vehicles_list"]])
            compat_rows.append(f"""                    <div class="comp-item">
                        <span class="comp-label">Vehículo:</span>
                        <div class="comp-tags">{vehicle_tags}</div>
                    </div>""")
        if compat["engines"]:
            compat_rows.append(f"""                    <div class="comp-item">
                        <span class="comp-label">Motor:</span>
                        <span class="tag-capsule engine-tag">{compat["engines"]}</span>
                    </div>""")
        if compat["years"]:
            compat_rows.append(f"""                    <div class="comp-item">
                        <span class="comp-label">Año:</span>
                        <span class="tag-capsule year-tag">{compat["years"]}</span>
                    </div>""")
                    
        compatibility_card_html = f"""<div class="compatibility-card">
                    <h3>Compatibilidad Garantizada</h3>
                    {"\n".join(compat_rows)}
                </div>"""
                
        # Construir Ficha Técnica HTML de Medidas / Variantes
        specs_card_html = ""
        unique_medidas = []
        for m in medidas:
            if m not in unique_medidas:
                unique_medidas.append(m)
                
        if unique_medidas:
            medida_val = escape_html(" / ".join(unique_medidas))
            specs_card_html = f"""<div class="compatibility-card">
                    <h3>Especificaciones Técnicas</h3>
                    <div class="comp-item">
                        <span class="comp-label">Medidas / Variantes:</span>
                        <span class="tag-capsule year-tag" style="color: #fff; background: rgba(255,255,255,0.04);">{medida_val}</span>
                    </div>
                </div>"""
                
        # Generar párrafo de descripción semántico para SEO y motores de IA sin marcas
        desc_paragraph = f"El repuesto <strong>{desc}</strong> está diseñado y fabricado bajo los estándares de rendimiento y acople original para asegurar la durabilidad y correcto funcionamiento de tu vehículo. Esta pieza pertenece a la categoría de <strong>{cat}</strong>."
        if p_oem_raw:
            desc_paragraph += f" Número de parte OEM: <strong>{escape_html(p_oem_raw)}</strong>."
        if unique_medidas:
            desc_paragraph += f" Presenta especificaciones técnicas de: <strong>{escape_html(' / '.join(unique_medidas))}</strong>."
        desc_paragraph += " Puedes retirar este producto personalmente en nuestra sede física ubicada en Boleíta Sur, Caracas, o solicitar un envío nacional a través de agencias de encomienda confiables como Zoom, Tealca o MRW con cobro en destino."
        
        desc_paragraph_clean = desc_paragraph.replace('<strong>', '').replace('</strong>', '')
        
        description_card_html = f"""<div class="description-card">
                    <h3>Descripción del Producto</h3>
                    <p>{desc_paragraph}</p>
                </div>"""
        
        p_oem = escape_html(p_oem_raw)
        oem_parts = [part.strip() for part in p_oem.split('/')] if p_oem else []
        if len(oem_parts) <= 1:
            oem_html = f'<div class="product-oem" style="font-family: monospace; font-size: 13px; color: var(--text-secondary); background: rgba(255, 106, 0, 0.05); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(255, 106, 0, 0.15); align-self: flex-start; margin-top: -8px; margin-bottom: 8px; font-weight: 600;">OEM: {p_oem}</div>' if p_oem else ''
        else:
            primary_oem = oem_parts[0]
            hidden_parts = oem_parts[1:]
            
            grid_items_html = "".join([f'<div style="font-family: monospace; font-size: 12px; color: var(--text-secondary); padding: 4px 8px; background: rgba(255,255,255,0.02); border-radius: 4px; border: 1px solid rgba(255,255,255,0.05); text-align: center; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">{part}</div>' for part in hidden_parts])
            
            oem_html = (
                f'<div class="product-oem" style="font-family: monospace; font-size: 13px; color: var(--text-secondary); '
                f'background: rgba(255, 106, 0, 0.05); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(255, 106, 0, 0.15); '
                f'align-self: stretch; margin-top: -8px; margin-bottom: 8px; font-weight: 600; line-height: 1.5; display: flex; flex-direction: column; gap: 4px;">'
                f'<div>OEM Principal: {primary_oem}</div>'
                f'<details class="oem-details" style="width: 100%; margin-top: 4px;">'
                f'<summary style="cursor: pointer; color: #ff6a00; font-weight: 700; outline: none; list-style: none; user-select: none; transition: opacity 0.2s;" onmouseover="this.style.opacity=0.8" onmouseout="this.style.opacity=1">+ Ver alternativos ({len(hidden_parts)})</summary>'
                f'<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 6px; margin-top: 8px; padding-top: 8px; border-top: 1px dashed rgba(255, 106, 0, 0.15);">'
                f'{grid_items_html}'
                f'</div>'
                f'</details>'
                f'</div>'
            )
        
        import json
        if len(oem_list_seo) > 1:
            mpn_code = json.dumps(oem_list_seo)
        else:
            mpn_code = f'"{oem_list_seo[0]}"' if oem_list_seo else f'"{p_id}"'
 
        # Calcular SKU optimizado para SEO (primer OEM limpio o fallback al slug)
        sku_code = oem_list_seo[0] if oem_list_seo else (p_slug if p_slug else p_id)

        # Seleccionar reseña adecuada
        desc_upper = desc.upper()
        try:
            seed_val = int(product.get('id', '0'))
        except:
            seed_val = hash(str(product.get('id', '')))
            
        if "CARIBE" in desc_upper:
            selected_review = GOOGLE_REVIEWS[1]
        elif "D-MAX" in desc_upper or "DMAX" in desc_upper:
            selected_review = GOOGLE_REVIEWS[0] if seed_val % 2 == 0 else GOOGLE_REVIEWS[3]
        else:
            selected_review = GOOGLE_REVIEWS[seed_val % len(GOOGLE_REVIEWS)]
            
        review_author = selected_review["author"].replace('"', '\\"')
        review_body = selected_review["body"].replace('"', '\\"')

        # Obtener HTML de productos relacionados
        related_products_html = get_related_products_html(product, products, base_url)

        html_content = template.format(
            id=p_id,
            sku=sku_code,
            slug=p_slug if p_slug else p_id,
            safe_filename=safe_filename,
            clean_filename=safe_filename.replace('.html', ''),
            description=desc,
            url_description=url_desc,
            category=cat,
            category_slug=cat_slug,
            image_path=img_path,
            image_url_seo=image_url_seo,
            whatsapp_number=whatsapp_number,
            base_url=base_url,
            ga_script=ga_script,
            logo_ext=logo_ext,
            logo_type=logo_type,
            instagram_url=instagram_url,
            facebook_url=facebook_url,
            maps_url=maps_url,
            reviews_url=reviews_url,
            title_description=title_description,
            meta_description=meta_description,
            schema_description=escape_html(desc_paragraph_clean),
            brand_schema_name=brand_schema_name,
            image_alt=image_alt,
            compatibility_card=compatibility_card_html,
            specs_card=specs_card_html,
            description_card=description_card_html,
            schema_compatibility_json=schema_compatibility_json,
            oem_html=oem_html,
            mpn_code=mpn_code,
            price_bs=price_bs_str,
            availability=availability_str,
            related_products=related_products_html,
            review_author=review_author,
            review_body=review_body
        )
        
        # Guardar archivo
        file_path = os.path.join(P_DIR, safe_filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
    print(f"Se han generado {len(products)} páginas estáticas en la carpeta /p/")

def generate_sitemap(data):
    products = data.get('products', [])
    today = datetime.now().strftime('%Y-%m-%d')
    base_url = get_site_base_url()
    uuid_pattern = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
    
    # Recopilar todas las URLs válidas de productos
    product_urls = []
    import urllib.parse
    import html
    for product in products:
        prod_id = product.get("id")
        p_slug = product.get("slug")
        if prod_id:
            # Omitir si no hay slug, o si el slug es un UUID, o si coincide con el ID
            if not p_slug or uuid_pattern.match(p_slug) or p_slug == prod_id:
                continue
            safe_filename = f"{p_slug}.html"
            
            img_path = product.get('image_path', '')
            filename = img_path.split('/')[-1] if img_path else ''
            image_url = f"{base_url.rstrip('/')}/assets/{urllib.parse.quote(filename)}" if filename else ""
            desc = html.escape(product.get('description', 'Repuesto'))
            
            product_urls.append({
                "url": f"{base_url}p/{safe_filename.replace('.html', '')}",
                "image_url": image_url,
                "title": desc
            })
            
    # Dividir en lotes de 1000 URLs
    BATCH_SIZE = 1000
    batches = [product_urls[i:i + BATCH_SIZE] for i in range(0, len(product_urls), BATCH_SIZE)]
    
    # Limpiar sub-sitemaps anteriores para evitar archivos huérfanos
    for filename in os.listdir(BASE_DIR):
        if filename.startswith("sitemap-") and filename.endswith(".xml"):
            try:
                os.remove(os.path.join(BASE_DIR, filename))
            except Exception:
                pass
                
    # Generar sub-sitemaps
    sitemap_filenames = []
    
    # Sitemap 1: páginas principales
    main_sitemap = os.path.join(BASE_DIR, "sitemap-main.xml")
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
        f.write(f'    <loc>{base_url}informacion</loc>\n')
        f.write(f'    <lastmod>{today}</lastmod>\n')
        f.write('    <changefreq>weekly</changefreq>\n')
        f.write('    <priority>0.9</priority>\n')
        f.write('  </url>\n')
        
        car_pages = [
            "repuestos-isuzu-caribe-442.html",
            "repuestos-chevrolet-luv.html",
            "repuestos-chevrolet-luv-d-max.html",
            "repuestos-isuzu-rodeo.html",
            "repuestos-isuzu-trooper.html"
        ]
        for car_page in car_pages:
            f.write('  <url>\n')
            f.write(f'    <loc>{base_url}{car_page.replace(".html", "")}</loc>\n')
            f.write(f'    <lastmod>{today}</lastmod>\n')
            f.write('    <changefreq>weekly</changefreq>\n')
            f.write('    <priority>0.9</priority>\n')
            f.write('  </url>\n')
        f.write('</urlset>\n')
    sitemap_filenames.append("sitemap-main.xml")
    
    # Sitemaps de productos en lotes de 100
    for idx, batch in enumerate(batches, start=1):
        filename = f"sitemap-productos-{idx}.xml"
        batch_path = os.path.join(BASE_DIR, filename)
        with open(batch_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n')
            for prod in batch:
                f.write('  <url>\n')
                f.write(f'    <loc>{prod["url"]}</loc>\n')
                if prod.get("image_url"):
                    f.write('    <image:image>\n')
                    f.write(f'      <image:loc>{prod["image_url"]}</image:loc>\n')
                    f.write(f'      <image:title>{prod["title"]}</image:title>\n')
                    f.write('    </image:image>\n')
                f.write(f'    <lastmod>{today}</lastmod>\n')
                f.write('    <changefreq>monthly</changefreq>\n')
                f.write('    <priority>0.8</priority>\n')
                f.write('  </url>\n')
            f.write('</urlset>\n')
        sitemap_filenames.append(filename)
        
    # Generar sitemap index principal
    with open(SITEMAP_FILE, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for sm_filename in sitemap_filenames:
            f.write('  <sitemap>\n')
            f.write(f'    <loc>{base_url}{sm_filename}</loc>\n')
            f.write(f'    <lastmod>{today}</lastmod>\n')
            f.write('  </sitemap>\n')
        f.write('</sitemapindex>\n')
        
    total_urls = len(product_urls) + 2
    print(f"Sitemap index generado con {len(sitemap_filenames)} sub-sitemaps ({total_urls} URLs totales)")

def generate_vehicle_pages(base_url):
    try:
        index_path = os.path.join(BASE_DIR, "index.html")
        if os.path.exists(index_path):
            print("[INFO] Generando paginas estaticas por vehiculo a partir de index.html...")
            with open(index_path, "r", encoding="utf-8") as f:
                index_content = f.read()

            vehicles_config = [
                {
                    "filename": "repuestos-isuzu-caribe-442.html",
                    "title": "Repuestos para Isuzu Caribe 442 | Todo Partes Horizonte",
                    "desc": "Encuentra repuestos para Isuzu Caribe 442 en Venezuela. Amortiguadores, partes de motor, embrague y componentes de dirección con envíos a nivel nacional.",
                    "filter": "CARIBE",
                    "card_id": "vehicle-caribe",
                    "h1": "Repuestos para tu Isuzu Caribe 442"
                },
                {
                    "filename": "repuestos-chevrolet-luv.html",
                    "title": "Repuestos para Chevrolet Luv | Todo Partes Horizonte",
                    "desc": "Encuentra repuestos para Chevrolet Luv en Venezuela. Amortiguadores, partes de motor, componentes eléctricos y dirección con envíos a nivel nacional.",
                    "filter": "LUV",
                    "card_id": "vehicle-luv",
                    "h1": "Repuestos para tu Chevrolet Luv"
                },
                {
                    "filename": "repuestos-chevrolet-luv-d-max.html",
                    "title": "Repuestos para Chevrolet Luv D-Max | Todo Partes Horizonte",
                    "desc": "Encuentra repuestos para Chevrolet Luv D-Max en Venezuela. Accesorios de motor, tren delantero, filtros y suspensión con envíos a nivel nacional.",
                    "filter": "D-MAX",
                    "card_id": "vehicle-dmax",
                    "h1": "Repuestos para tu Chevrolet Luv D-Max"
                },
                {
                    "filename": "repuestos-isuzu-rodeo.html",
                    "title": "Repuestos para Isuzu Rodeo | Todo Partes Horizonte",
                    "desc": "Encuentra repuestos para Isuzu Rodeo en Venezuela. Componentes de suspensión, embrague, motor y frenos con envíos a nivel nacional.",
                    "filter": "RODEO",
                    "card_id": "vehicle-rodeo",
                    "h1": "Repuestos para tu Isuzu Rodeo"
                },
                {
                    "filename": "repuestos-isuzu-trooper.html",
                    "title": "Repuestos para Isuzu Trooper | Todo Partes Horizonte",
                    "desc": "Encuentra repuestos para Isuzu Trooper en Venezuela. Tren delantero, bomba de agua, embrague y frenos con envíos a nivel nacional.",
                    "filter": "TROOPER",
                    "card_id": "vehicle-trooper",
                    "h1": "Repuestos para tu Isuzu Trooper"
                }
            ]

            for v in vehicles_config:
                v_path = os.path.join(BASE_DIR, v["filename"])
                v_content = index_content

                # 1. Reemplazar Title
                v_content = re.sub(r'<title>.*?</title>', f'<title>{v["title"]}</title>', v_content)

                # 2. Reemplazar Meta Description
                v_content = re.sub(
                    r'<meta name="description" content="[^"]*"',
                    f'<meta name="description" content="{v["desc"]}"',
                    v_content
                )

                # 3. Reemplazar Meta Canonical
                v_content = re.sub(
                    r'<link rel="canonical" href="[^"]*"',
                    f'<link rel="canonical" href="{base_url}{v["filename"].replace(".html", "")}"',
                    v_content
                )

                # 4. Reemplazar Open Graph Title, Description, Url
                v_content = re.sub(
                    r'<meta property="og:title" content="[^"]*"',
                    f'<meta property="og:title" content="{v["title"]}"',
                    v_content
                )
                v_content = re.sub(
                    r'<meta property="og:description" content="[^"]*"',
                    f'<meta property="og:description" content="{v["desc"]}"',
                    v_content
                )
                v_content = re.sub(
                    r'<meta property="og:url" content="[^"]*"',
                    f'<meta property="og:url" content="{base_url}{v["filename"].replace(".html", "")}"',
                    v_content
                )

                # 5. Reemplazar h1 de cabecera por div
                v_content = re.sub(
                    r'<h1 class="logo-title"([^>]*)>(.*?)</h1>',
                    r'<div class="logo-title"\1>\2</div>',
                    v_content
                )

                # 6. Insertar H1 de SEO para el vehículo (Visible arriba del filtro)
                # Eliminamos el texto "Filtrar por Vehículo" y ponemos el título real
                v_content = v_content.replace(
                    '<h2 class="vehicle-filter-title">Filtrar por Vehículo</h2>',
                    f'<h1 class="vehicle-filter-title" style="text-transform: uppercase;">{v["h1"]}</h1>'
                )

                # 7. Cambiar filtro activo de vehículo en el selector
                v_content = v_content.replace('class="vehicle-card active" id="vehicle-all"', 'class="vehicle-card" id="vehicle-all"')
                v_content = v_content.replace(f'class="vehicle-card" id="{v["card_id"]}"', f'class="vehicle-card active" id="{v["card_id"]}"')

                # 8. Agregar JavaScript de filtro predeterminado al final del body
                control_script = f"""<!-- JAVASCRIPT DE CONTROL -->
    <script defer src="./products.js?v=2"></script>
    <script>window.defaultVehicleFilter = '{v["filter"]}';</script>
    <script defer src="./app.min.js?v=2"></script>"""
                
                v_content = v_content.replace('<!-- JAVASCRIPT DE CONTROL -->\n    <script defer src="./products.js?v=2"></script>\n    <script defer src="./app.min.js?v=2"></script>', control_script)
                v_content = v_content.replace('<!-- JAVASCRIPT DE CONTROL -->\r\n    <script defer src="./products.js?v=2"></script>\r\n    <script defer src="./app.min.js?v=2"></script>', control_script)

                with open(v_path, "w", encoding="utf-8") as out_f:
                    out_f.write(v_content)
                print(f"   [OK] Generada pagina de vehiculo: {v['filename']}")
        else:
            print("[WARN] No se encontro index.html para generar paginas de vehiculos.")
    except Exception as e:
        print(f"[ERROR] Error al generar paginas por vehiculo: {e}")

def update_index_seo_links(products):
    import html
    index_path = os.path.join(BASE_DIR, "index.html")
    if not os.path.exists(index_path):
        return
        
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    start_marker = "<!-- INICIO ENLACES SEO -->"
    end_marker = "<!-- FIN ENLACES SEO -->"
    
    if start_marker in content and end_marker in content:
        start_idx = content.find(start_marker) + len(start_marker)
        end_idx = content.find(end_marker)
        
        links = []
        uuid_pattern = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
        for product in products:
            prod_id = product.get("id")
            p_slug = product.get("slug")
            if prod_id and p_slug and not uuid_pattern.match(p_slug) and p_slug != prod_id:
                safe_filename = f"{p_slug}.html"
                desc = html.escape(product.get('description', 'Repuesto'))
                links.append(f'        <a href="./p/{safe_filename}">{desc}</a>')
                
        new_links_html = "\n" + "\n".join(links) + "\n        "
        new_content = content[:start_idx] + new_links_html + content[end_idx:]
        
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Se actualizaron los enlaces SEO en index.html ({len(links)} enlaces).")

if __name__ == '__main__':
    data = read_products()
    generate_pages(data)
    generate_sitemap(data)
    update_index_seo_links(data.get('products', []))
    base_url = get_site_base_url()
    generate_vehicle_pages(base_url)
