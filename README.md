# 🩻 coverburn

OCR showdown for pathology and radiology cover slides — PaddleOCR vs Tesseract 🔥

**coverburn** is a lightweight tool to test how different OCR engines (like [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) and [Tesseract](https://github.com/tesseract-ocr/tesseract)) perform on DICOM cover slides.

It was born from frustration with traditional OCR tools fumbling text on medical images (looking at you, `$` vs `S` 👀).

## 🚀 Features
- Reads **DICOM** or `.dat` files directly (even if renamed)
- Extracts pixel data with `pydicom`
- Runs both **PaddleOCR** and **Tesseract** for side-by-side comparison
- Prints results (and confidence scores) to the terminal
- Drop-in ready any DICOM folder

## 🧰 Requirements
Python 3.9+ and a few dependencies:

```bash
pip install paddleocr paddlepaddle pydicom numpy pillow opencv-python pytesseract
```

🧠 If you're on macOS, you'll also need Tesseract installed:

```bash
brew install tesseract
```

## 📜 Usage

Run OCR on one file (DICOM or `.dat`):

```bash
python ocr_probe.py /path/to/file.dcm
```

or if you just wanna test the first file it finds in a folder:

```bash
python ocr_probe.py /path/to
```

Example output:

```
=== PaddleOCR Results ===
Patient Name: J DOE (conf: 0.96)
Accession #: 1234567 (conf: 0.92)

=== Tesseract Results ===
Patient Name: J DOE
Accession #: 1234567
```

## 🧪 Future Plans

* Batch mode: scan entire directories
* JSON/CSV output for easier diffing
* Comparison metrics between OCR engines
* Preprocessing tweaks for rotation, blur, and low contrast

## 🧑‍💻 Author

**Bear** — DevOps engineer, slide whisperer, and Tesseract survivor.

## ⚖️ License

MIT License © 2025 Bear

<br>
