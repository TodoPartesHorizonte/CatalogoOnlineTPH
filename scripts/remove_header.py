import os
import re

base_dir = r"c:\Users\Miguel F\.gemini\antigravity\scratch\Catalogo Online\web"
files = [
    'repuestos-chevrolet-luv.html',
    'repuestos-chevrolet-luv-d-max.html',
    'repuestos-isuzu-caribe-442.html',
    'repuestos-isuzu-rodeo.html',
    'repuestos-isuzu-trooper.html'
]

for f_name in files:
    path = os.path.join(base_dir, f_name)
    if not os.path.exists(path): 
        print(f"Not found: {path}")
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove the vehicle-hub-header div and its contents completely
    content = re.sub(r'[ \t]*<div class="vehicle-hub-header"[^>]*>.*?</div>[ \t]*\n?', '', content, flags=re.DOTALL)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Removed header from {f_name}")
