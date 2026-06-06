from PIL import Image
import os
from pathlib import Path

img_path = Path(r"C:\Users\Miguel F\OneDrive\Escritorio\Nani-20260604T130212Z-3-001\Nani\Amortiguador Direccion\WhatsApp Image 2026-02-09 at 1.42.47 PM.jpeg")

if img_path.exists():
    with Image.open(img_path) as img:
        width, height = img.size
        
        # 1. Crop
        crop_box = (0, int(height * 0.33), width, int(height * 0.55))
        cropped = img.crop(crop_box)
        
        # 2. Grayscale
        gray = cropped.convert('L')
        
        # 3. Resize 2x
        resized = gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.LANCZOS)
        
        # 4. Threshold (convert to binary black text on white background)
        # We use threshold value 180
        fn = lambda x : 0 if x > 180 else 255
        binary = resized.point(fn, mode='1')
        
        # Save results
        binary.save("preprocessed_binary.png")
        print("Preprocessed image saved successfully.")
else:
    print("Image not found:", img_path)
