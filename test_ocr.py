import sys
from pathlib import Path
from PIL import Image
import numpy as np
import easyocr

img_path = Path(r"C:\Users\Miguel F\OneDrive\Escritorio\Nani-20260604T130212Z-3-001\Nani\Abrazadera Barra Estabilizadora\b3cb7097-6502-499b-9a68-41ab28bfa8cd.jpg")
print("Image exists:", img_path.exists())

with Image.open(img_path) as img:
    width, height = img.size
    print(f"Size: {width}x{height}")
    
    # Test 1: cropped image as in generator.py
    crop_box = (0, int(height * 0.33), width, int(height * 0.55))
    cropped_img = img.crop(crop_box)
    cropped_img.save("cropped_test.jpg")
    
    # Load easyocr reader
    reader = easyocr.Reader(['es', 'en'])
    
    print("Running OCR on cropped image...")
    cropped_np = np.array(cropped_img.convert('RGB'))
    results_crop = reader.readtext(cropped_np)
    for res in results_crop:
        print("Cropped result:", res[1], "Confidence:", res[2])
        
    print("\nRunning OCR on full image...")
    full_np = np.array(img.convert('RGB'))
    results_full = reader.readtext(full_np)
    for res in results_full:
        print("Full result:", res[1], "Confidence:", res[2])
