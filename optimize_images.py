import os
from PIL import Image

assets_dir = r"c:\Users\Miguel F\.gemini\antigravity\scratch\Catalogo Online\web\assets"
images = [
    "bp_front.png", "bp_rear.png", "bp_side.png", "bp_top.png",
    "bp_dmax_front.png", "bp_dmax_rear.png", "bp_dmax_side.png", "bp_dmax_top.png",
    "map_preview.png"
]

for img_name in images:
    path = os.path.join(assets_dir, img_name)
    if os.path.exists(path):
        with Image.open(path) as img:
            out_path = path.replace(".png", ".webp")
            img.save(out_path, "WEBP", quality=80, method=6)
            print(f"Converted {img_name} to WEBP")
