"""
Search through DICOM folders to identify potential cover slides.
Cover slides typically have:
- Image type containing "LOCALIZER", "SCOUT", or "SECONDARY"
- Lower instance numbers (often first in series)
- Different modality characteristics
- Potentially embedded text or annotations
"""

import argparse
import operator
import os
from pathlib import Path
from typing import Dict, List

import pydicom
from rich_argparse import RichHelpFormatter


def is_potential_cover_slide(ds: pydicom.Dataset) -> Dict[str, any]:
    """
    Analyze DICOM metadata to determine if this might be a cover slide.
    Returns a dict with score and reasons.
    """
    score = 0
    reasons = []

    # Check Image Type
    if hasattr(ds, "ImageType"):
        image_type = str(ds.ImageType).upper()
        if "SECONDARY" in image_type:
            score += 3
            reasons.append("Image Type: SECONDARY")
        if "LOCALIZER" in image_type or "SCOUT" in image_type:
            score += 5
            reasons.append(f"Image Type: {image_type}")
        if "SCREEN" in image_type or "SAVE" in image_type:
            score += 4
            reasons.append("Image Type: SCREEN SAVE")

    # Check Instance Number (cover slides often first)
    if hasattr(ds, "InstanceNumber"):
        if ds.InstanceNumber == 1:
            score += 2
            reasons.append("Instance Number: 1 (first in series)")

    # Check for Burned In Annotation
    if hasattr(ds, "BurnedInAnnotation"):
        if ds.BurnedInAnnotation == "YES":
            score += 5
            reasons.append("Burned In Annotation: YES")

    # Check SOP Class UID for Secondary Capture
    if hasattr(ds, "SOPClassUID"):
        # Secondary Capture Image Storage
        if ds.SOPClassUID == "1.2.840.10008.5.1.4.1.1.7":
            score += 4
            reasons.append("SOP Class: Secondary Capture")
        # Grayscale Softcopy Presentation State
        elif "1.2.840.10008.5.1.4.1.1.11" in ds.SOPClassUID:
            score += 3
            reasons.append("SOP Class: Presentation State")

    # Check Conversion Type
    if hasattr(ds, "ConversionType"):
        if ds.ConversionType in ("WSD", "SI", "DV"):
            score += 3
            reasons.append(f"Conversion Type: {ds.ConversionType}")

    # Check for unusual dimensions (screenshots might have different aspect ratios)
    if hasattr(ds, "Rows") and hasattr(ds, "Columns"):
        aspect_ratio = ds.Columns / ds.Rows
        if aspect_ratio > 1.5 or aspect_ratio < 0.6:
            score += 1
            reasons.append(f"Unusual aspect ratio: {aspect_ratio:.2f}")

    return {"score": score, "reasons": reasons, "is_cover_slide": score >= 3}


def analyze_dicom_file(file_path: Path) -> Dict:
    """Analyze a single DICOM file."""
    try:
        ds = pydicom.dcmread(file_path, stop_before_pixels=True)
        analysis = is_potential_cover_slide(ds)

        return {
            "path": str(file_path),
            "score": analysis["score"],
            "is_cover_slide": analysis["is_cover_slide"],
            "reasons": analysis["reasons"],
            "metadata": {
                "PatientID": getattr(ds, "PatientID", "N/A"),
                "StudyDescription": getattr(ds, "StudyDescription", "N/A"),
                "SeriesDescription": getattr(ds, "SeriesDescription", "N/A"),
                "Modality": getattr(ds, "Modality", "N/A"),
                "InstanceNumber": getattr(ds, "InstanceNumber", "N/A"),
                "ImageType": str(getattr(ds, "ImageType", "N/A")),
            },
        }
    except Exception as e:
        return {"path": str(file_path), "error": str(e)}


def find_dicom_files(root_dir: Path, extensions: List[str] = None) -> List[Path]:
    """Recursively find all .dat files in directory."""
    if extensions is None:
        extensions = [".dat"]

    dicom_files = []

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            file_path = Path(root) / file

            # Only match .dat files
            if file_path.suffix.lower() in extensions:
                dicom_files.append(file_path)

    return dicom_files


def main():
    parser = argparse.ArgumentParser(
        description="Search for DICOM cover slides in a directory tree",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        "directory",
        type=str,
        nargs="?",
        default=".",
        help="Root directory to search (default: current directory)",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=3,
        help="Minimum score to consider a file as cover slide (default: 3)",
    )

    args = parser.parse_args()

    root_dir = Path(args.directory).resolve()

    if not root_dir.exists():
        print(f"Error: Directory '{root_dir}' does not exist")
        return

    print(f"Searching for DICOM files in: {root_dir}")
    print("=" * 80)

    dicom_files = find_dicom_files(root_dir)
    print(f"\nFound {len(dicom_files)} DICOM files")
    print("=" * 80)

    results = []
    for file_path in dicom_files:
        result = analyze_dicom_file(file_path)
        if "error" not in result:
            results.append(result)

    # Sort by score (highest first)
    results.sort(key=operator.itemgetter("score"), reverse=True)

    # Display results
    cover_slides = [r for r in results if r["score"] >= args.min_score]

    if cover_slides:
        print(f"\n🎯 COVER SLIDES FOUND ({len(cover_slides)}):")
        print("=" * 80)

        for result in cover_slides:
            print(result["path"])
    else:
        print("\n❌ No cover slides found")


if __name__ == "__main__":
    main()
