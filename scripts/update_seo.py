import os
import re

base_dir = r"c:\Users\Miguel F\.gemini\antigravity\scratch\Catalogo Online\web"
files = [
    'index.html',
    'repuestos-chevrolet-luv.html',
    'repuestos-chevrolet-luv-d-max.html',
    'repuestos-isuzu-caribe-442.html',
    'repuestos-isuzu-rodeo.html',
    'repuestos-isuzu-trooper.html'
]

desc_old = 'Catálogo online especializado en repuestos Chevrolet e Isuzu en Venezuela. Encuentra autopartes para Caribe 442, Luv, D-Max, Trooper y Rodeo con envíos nacionales y asesoría técnica especializada.'
desc_new = 'Somos tienda de repuestos encargada de vender autopartes de vehículos Isuzu y Chevrolet (Caribe, Trooper, Rodeo, Luv, Luv D-Max). Envíos nacionales y asesoría técnica especializada.'

og_old = 'Catálogo online especializado en repuestos y autopartes. Consulta disponibilidad para modelos Caribe 442, Trooper, Rodeo, Luv y D-Max vía WhatsApp.'
og_new = 'Somos tienda de repuestos encargada de vender autopartes de vehículos Isuzu y Chevrolet (Caribe, Trooper, Rodeo, Luv, Luv D-Max) vía WhatsApp.'

for f_name in files:
    path = os.path.join(base_dir, f_name)
    if not os.path.exists(path): 
        print(f"Not found: {path}")
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replacements for description
    content = content.replace(desc_old, desc_new)
    content = content.replace(og_old, og_new)
    
    # Also replace in keywords, removing 'importador' or any unwanted stuff if any, but the keywords are fine.
    
    if f_name != 'index.html':
        # Replace h1 with div for logo-title
        # <h1 class="logo-title" id="logoTitleText">TODO PARTES <span>HORIZONTE</span></h1>
        content = re.sub(
            r'<h1 class="logo-title"([^>]*)>(.*?)</h1>',
            r'<div class="logo-title"\1>\2</div>',
            content
        )
        
        # Replace active vehicle filter class
        content = content.replace('class="vehicle-card active" id="vehicle-all"', 'class="vehicle-card" id="vehicle-all"')
        
        mapping = {
            'repuestos-chevrolet-luv.html': 'id="vehicle-luv"',
            'repuestos-chevrolet-luv-d-max.html': 'id="vehicle-dmax"',
            'repuestos-isuzu-caribe-442.html': 'id="vehicle-caribe"',
            'repuestos-isuzu-rodeo.html': 'id="vehicle-rodeo"',
            'repuestos-isuzu-trooper.html': 'id="vehicle-trooper"'
        }
        
        target_id = mapping[f_name]
        content = content.replace(f'class="vehicle-card" {target_id}', f'class="vehicle-card active" {target_id}')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated {f_name}")
