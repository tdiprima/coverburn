# Minimal test script, very "engineer prototyping at 2 a.m." energy

import warnings

import numpy as np
import pydicom
import pytesseract
from paddleocr import PaddleOCR
from PIL import Image

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Path to one DICOM file
dcm_path = "sample.dat"

# Read the DICOM file
ds = pydicom.dcmread(dcm_path)

# Extract image array
pixel_array = ds.pixel_array

# Normalize and convert to uint8 for image processing
pixel_array = (pixel_array - np.min(pixel_array)) / (
    np.max(pixel_array) - np.min(pixel_array)
)
pixel_array = (pixel_array * 255).astype(np.uint8)

# Save or convert to PIL Image
img = Image.fromarray(pixel_array)

# --- PaddleOCR ---
ocr = PaddleOCR(use_angle_cls=True, lang="en")
paddle_results = ocr.predict(np.array(img))

print("=== PaddleOCR Results ===")
for line in paddle_results[0]:
    text, conf = line[1][0], line[1][1]
    print(f"{text} (conf: {conf:.2f})")

# --- Optional: Tesseract comparison ---
try:
    tess_result = pytesseract.image_to_string(img)
    print("\n=== Tesseract Results ===")
    print(tess_result.strip())
except Exception as e:
    print(f"Tesseract failed: {e}")
