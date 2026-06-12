import os
import json
import base64
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

def generate_pages(data):
    products = data.get('products', [])
    whatsapp_encoded = data.get('whatsapp_number', '')
    whatsapp_number = decode_base64(whatsapp_encoded)
    
    template = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self';">
    <title>{description} | Repuestos Isuzu TODO PARTES</title>
    <meta name="description" content="Comprar {description} para vehículos Isuzu. Repuesto especializado en Caracas. Consulta disponibilidad y precio vía WhatsApp.">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://todoparteshorizonte.github.io/CatalogoOnlineTPH/p/{safe_filename}">
    <link rel="icon" href="../assets/logo.png" type="image/png">
    
    <!-- Open Graph -->
    <meta property="og:title" content="{description} | Repuestos Isuzu">
    <meta property="og:description" content="Comprar {description} para Isuzu. Repuesto especializado en Caracas. Consulta disponibilidad vía WhatsApp.">
    <meta property="og:image" content="https://todoparteshorizonte.github.io/CatalogoOnlineTPH/assets/{id}.webp">
    <meta property="og:url" content="https://todoparteshorizonte.github.io/CatalogoOnlineTPH/p/{safe_filename}">
    <meta property="og:type" content="product">
    
    <!-- JSON-LD -->
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org/",
      "@type": "Product",
      "name": "{description}",
      "image": "https://todoparteshorizonte.github.io/CatalogoOnlineTPH/assets/{id}.webp",
      "description": "{description} para vehículos Isuzu. Especialistas en repuestos en Caracas.",
      "brand": {{
        "@type": "Brand",
        "name": "Isuzu"
      }},
      "offers": {{
        "@type": "Offer",
        "availability": "https://schema.org/InStock",
        "priceCurrency": "USD",
        "price": "0.00",
        "url": "https://todoparteshorizonte.github.io/CatalogoOnlineTPH/p/{safe_filename}"
      }}
    }}
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        body {{ background-color: #030304; color: #fff; font-family: 'Outfit', sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; text-align: center; }}
        .product-card {{ background: #0a0a0e; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 30px; max-width: 500px; width: 100%; box-shadow: 0 15px 35px rgba(0,0,0,0.5); }}
        .product-img {{ max-width: 100%; border-radius: 8px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.05); }}
        .product-title {{ font-size: 24px; font-weight: 800; color: #fff; margin-bottom: 10px; line-height: 1.2; }}
        .product-category {{ color: #ff6a00; font-weight: 600; text-transform: uppercase; margin-bottom: 24px; font-size: 14px; letter-spacing: 1px; }}
        .btn {{ display: inline-flex; align-items: center; justify-content: center; gap: 10px; background: #ff6a00; color: #fff; padding: 16px 30px; border-radius: 4px; text-decoration: none; font-weight: 800; text-transform: uppercase; margin-top: 10px; transition: all 0.3s ease; width: 100%; box-sizing: border-box; }}
        .btn:hover {{ background: #ff8a00; transform: translateY(-2px); box-shadow: 0 10px 20px rgba(255,106,0,0.3); }}
        .btn-secondary {{ background: transparent; border: 1px solid rgba(255, 106, 0, 0.4); color: #fff; }}
        .btn-secondary:hover {{ background: rgba(255, 106, 0, 0.1); }}
        .logo {{ margin-bottom: 30px; width: 90px; border-radius: 16px; box-shadow: 0 10px 20px rgba(0,0,0,0.5); }}
        svg {{ width: 24px; height: 24px; fill: currentColor; }}
    </style>
</head>
<body>
    <img src="../assets/logo.png" alt="TODO PARTES HORIZONTE" class="logo">
    <div class="product-card">
        <img src=".{image_path}" alt="{description}" class="product-img">
        <h1 class="product-title">{description}</h1>
        <div class="product-category">Categoría: {category}</div>
        
        <a href="https://wa.me/{whatsapp_number}?text=Hola,%20quisiera%20consultar%20disponibilidad%20y%20precio%20del%20repuesto:%20{url_description}" class="btn" target="_blank" rel="noopener noreferrer">
            <svg viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L0 24l6.335-1.662c1.746.953 3.71 1.455 5.703 1.456h.004c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/></svg>
            Consultar por WhatsApp
        </a>
        <a href="../index.html?producto={slug}" class="btn btn-secondary">
            Ver en Catálogo Completo
        </a>
    </div>
</body>
</html>"""

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
            
        desc = escape_html(product.get('description', 'Repuesto Isuzu'))
        url_desc = desc.replace(' ', '%20')
        cat = escape_html(product.get('category', 'Repuestos'))
        img_path = escape_html(product.get('image_path', ''))
        
        # Clean image path so it is relative from /p/ (image path in js is ./assets/...)
        img_path = img_path.replace('./assets', '/assets')
        
        html_content = template.format(
            id=p_id,
            slug=p_slug if p_slug else p_id,
            safe_filename=safe_filename,
            description=desc,
            url_description=url_desc,
            category=cat,
            image_path=img_path,
            whatsapp_number=whatsapp_number
        )
        
        # Guardar archivo
        file_path = os.path.join(P_DIR, safe_filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
    print(f"Se han generado {len(products)} páginas estáticas en la carpeta /p/")

def generate_sitemap(data):
    products = data.get('products', [])
    today = datetime.now().strftime('%Y-%m-%d')
    
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://todoparteshorizonte.github.io/CatalogoOnlineTPH/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://todoparteshorizonte.github.io/CatalogoOnlineTPH/informacion.html</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
'''
    
    for product in products:
        p_id = escape_html(product.get('id', ''))
        p_slug = escape_html(product.get('slug', ''))
        
        if p_slug:
            safe_filename = f"{p_slug}.html"
        else:
            safe_filename = p_id.replace(' ', '%20') + '.html'
        
        xml += f'''  <url>
    <loc>https://todoparteshorizonte.github.io/CatalogoOnlineTPH/p/{safe_filename}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>\n'''
  
    xml += "</urlset>"
    
    with open(SITEMAP_FILE, 'w', encoding='utf-8') as f:
        f.write(xml)
        
    print(f"Sitemap generado con éxito. ({len(products) + 2} URLs)")

if __name__ == '__main__':
    data = read_products()
    generate_pages(data)
    generate_sitemap(data)
