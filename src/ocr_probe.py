# Enhanced DICOM OCR test script with preprocessing
# uv run ocr_probe.py path/to/file.dat

import sys
import warnings

import cv2
import numpy as np
import pydicom
import pytesseract
from paddleocr import PaddleOCR
from PIL import Image

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Path to one DICOM file
dcm_path = sys.argv[1] if len(sys.argv) > 1 else "sample.dat"

print(f"Processing: {dcm_path}")
print("=" * 80)

# Read the DICOM file
ds = pydicom.dcmread(dcm_path)

# Extract image array
pixel_array = ds.pixel_array

# Normalize to 0-255
pixel_array = (pixel_array - np.min(pixel_array)) / (
    np.max(pixel_array) - np.min(pixel_array)
)
pixel_array = (pixel_array * 255).astype(np.uint8)

# Save original normalized version
if len(pixel_array.shape) == 2:
    original_rgb = np.stack([pixel_array] * 3, axis=-1)
else:
    original_rgb = pixel_array

Image.fromarray(original_rgb).save("01_original.png")

# Try multiple preprocessing approaches
preprocessed_images = []

# 1. Original (no preprocessing)
preprocessed_images.append(("Original", original_rgb))

# 2. Contrast enhancement (CLAHE)
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
enhanced = clahe.apply(pixel_array)
enhanced_rgb = np.stack([enhanced] * 3, axis=-1)
preprocessed_images.append(("CLAHE Enhanced", enhanced_rgb))
Image.fromarray(enhanced_rgb).save("02_clahe.png")

# 3. Binary threshold (Otsu's method)
_, binary = cv2.threshold(pixel_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
binary_rgb = np.stack([binary] * 3, axis=-1)
preprocessed_images.append(("Binary Threshold", binary_rgb))
Image.fromarray(binary_rgb).save("03_binary.png")

# 4. Inverted binary (for white text on black background)
inverted = cv2.bitwise_not(binary)
inverted_rgb = np.stack([inverted] * 3, axis=-1)
preprocessed_images.append(("Inverted Binary", inverted_rgb))
Image.fromarray(inverted_rgb).save("04_inverted.png")

# 5. Morphological operations to clean up noise
kernel = np.ones((2, 2), np.uint8)
morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
morph_rgb = np.stack([morph] * 3, axis=-1)
preprocessed_images.append(("Morphological", morph_rgb))
Image.fromarray(morph_rgb).save("05_morphological.png")

print(f"Saved {len(preprocessed_images)} preprocessed versions")
print("=" * 80)

# Test OCR on all preprocessed versions
print("\nTesting OCR on all preprocessed images...")
print("=" * 80)

ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

all_results = []

for name, img_array in preprocessed_images:
    print(f"\n--- {name} ---")

    # PaddleOCR
    paddle_results = ocr.predict(img_array)
    paddle_text = []

    if paddle_results and len(paddle_results) > 0:
        for result in paddle_results:
            if result.get("rec_text"):
                text = result.get("rec_text", "")
                conf = result.get("rec_score", 0)
                paddle_text.append(f"{text} ({conf:.2f})")

    # Tesseract
    try:
        img_pil = Image.fromarray(img_array)
        tess_result = pytesseract.image_to_string(img_pil).strip()
    except Exception:
        tess_result = ""

    # Display results
    if paddle_text or tess_result:
        if paddle_text:
            print(f"  PaddleOCR: {' | '.join(paddle_text)}")
        if tess_result:
            print(f"  Tesseract: {tess_result[:100]}...")  # Truncate long results

        all_results.append({
            "method": name,
            "paddle": paddle_text,
            "tesseract": tess_result
        })
    else:
        print("  No text detected")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

if all_results:
    print(f"\nText found in {len(all_results)} out of {len(preprocessed_images)} preprocessing methods:")
    for result in all_results:
        print(f"\n✓ {result['method']}")
        if result['paddle']:
            print(f"  PaddleOCR: {len(result['paddle'])} text regions")
        if result['tesseract']:
            print(f"  Tesseract: {len(result['tesseract'])} characters")
else:
    print("\n❌ No text detected in any preprocessing method")
    print("\nPossible reasons:")
    print("  - This is a diagnostic image without text overlays")
    print("  - Text is embedded in DICOM metadata, not pixel data")
    print("  - Image is a cover slide candidate that needs different handling")
