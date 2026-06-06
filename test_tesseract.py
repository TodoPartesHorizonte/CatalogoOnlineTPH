import pytesseract
from PIL import Image
from pathlib import Path

# Configurar tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

images = [
    r"C:\Users\Miguel F\OneDrive\Escritorio\Nani-20260604T130212Z-3-001\Nani\Amortiguador Direccion\WhatsApp Image 2026-02-09 at 1.42.47 PM.jpeg",
    r"C:\Users\Miguel F\OneDrive\Escritorio\Nani-20260604T130212Z-3-001\Nani\Amortiguador Direccion\WhatsApp Image 2026-02-09 at 1.42.48 PM.jpeg"
]

for img_path in images:
    p = Path(img_path)
    if not p.exists():
        print("Not found:", img_path)
        continue
        
    with Image.open(p) as img:
        width, height = img.size
        print(f"\n====================================")
        print(f"Image: {p.name} ({width}x{height})")
        print(f"====================================")
        
        # 1. Test original crop directly
        crop_box = (0, int(height * 0.33), width, int(height * 0.55))
        cropped = img.crop(crop_box)
        txt = pytesseract.image_to_string(cropped, lang='eng+spa')
        print(f"Original Crop (eng+spa) output:\n{repr(txt.strip())}")
        
        # 2. Test preprocessed crop (grayscale + 2x resize + threshold)
        gray = cropped.convert('L')
        resized = gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.LANCZOS)
        fn = lambda x : 0 if x > 180 else 255
        binary = resized.point(fn, mode='1')
        
        txt_pre = pytesseract.image_to_string(binary, lang='eng+spa')
        print(f"\nPreprocessed Crop (eng+spa) output:\n{repr(txt_pre.strip())}")
        
        # 3. Test preprocessed crop with different PSMs
        for psm in [3, 4, 6, 11, 12]:
            custom_config = f'--psm {psm}'
            txt_psm = pytesseract.image_to_string(binary, lang='eng+spa', config=custom_config)
            print(f"Preprocessed PSM {psm} output: {repr(txt_psm.strip())}")
