import pytesseract
from PIL import Image
from pathlib import Path

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img_path = Path(r"C:\Users\Miguel F\OneDrive\Escritorio\Nani-20260604T130212Z-3-001\Nani\Abrazadera Barra Estabilizadora\b3cb7097-6502-499b-9a68-41ab28bfa8cd.jpg")

if img_path.exists():
    with Image.open(img_path) as img:
        width, height = img.size
        print(f"Image: {img_path.name} ({width}x{height})")
        
        # Test full image
        txt = pytesseract.image_to_string(img, lang='eng+spa')
        print(f"Full image text:\n{repr(txt)}")
        
        # Test crop 33% to 55%
        crop_box = (0, int(height * 0.33), width, int(height * 0.55))
        cropped = img.crop(crop_box)
        txt_crop = pytesseract.image_to_string(cropped, lang='eng+spa')
        print(f"Cropped image text:\n{repr(txt_crop)}")
        
        # Test preprocessing (grayscale, scale 2x, threshold)
        gray = cropped.convert('L')
        resized = gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.LANCZOS)
        fn = lambda x : 0 if x > 180 else 255
        binary = resized.point(fn, mode='1')
        binary.save("abrazadera_binary.png")
        
        txt_pre = pytesseract.image_to_string(binary, lang='eng+spa')
        print(f"Preprocessed image text:\n{repr(txt_pre)}")
else:
    print("Not found:", img_path)
