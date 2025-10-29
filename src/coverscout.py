# Heuristic finder for likely "cover slides" inside giant DICOM dirs.

import argparse
import csv
import re
from pathlib import Path

import pydicom
from pydicom.misc import is_dicom

# Keywords that often hint "cover/label/title" style images
SERIES_HINTS = [
    "cover",
    "label",
    "slide",
    "title",
    "front",
    "burn",
    "debug",
    "deid",
    "doc",
    "scan doc",
    "scanned",
    "report",
]

# Modalities that are more likely to be non-body-slice images
NON_CT_MODALITIES = {"OT", "SC", "SM", "XC", "DOC", "PR"}


def safe_get(ds, name, default=None):
    try:
        return getattr(ds, name)
    except Exception:
        return default


def ratio(rows, cols):
    try:
        r = float(rows)
        c = float(cols)
        if r == 0 or c == 0:
            return 1.0
        return max(r, c) / min(r, c)
    except Exception:
        return 1.0


def score_dicom(ds):
    """
    Return (score, reasons[]) — higher = more likely a cover slide.
    We keep it additive and explainable.
    """
    score = 0
    reasons = []

    modality = str(safe_get(ds, "Modality", "")).upper()
    photometric = str(safe_get(ds, "PhotometricInterpretation", "")).upper()
    samples = safe_get(ds, "SamplesPerPixel", None)
    series_desc = str(safe_get(ds, "SeriesDescription", "")).lower()
    image_type = " ".join(map(str, safe_get(ds, "ImageType", []))).lower()
    burned = str(safe_get(ds, "BurnedInAnnotation", "")).upper()
    rows = safe_get(ds, "Rows", None)
    cols = safe_get(ds, "Columns", None)

    # 1) Non-CT modalities are strong signals
    if modality in NON_CT_MODALITIES:
        score += 4
        reasons.append(f"modality={modality}")

    # 2) RGB / color-ish photometric or SamplesPerPixel==3 suggests a scanned/cover image
    if photometric in {"RGB", "PALETTE COLOR", "YBR_FULL", "YBR_FULL_422"}:
        score += 3
        reasons.append(f"photometric={photometric}")
    if samples == 3:
        score += 2
        reasons.append("samples_per_pixel=3")

    # 3) SeriesDescription hints
    for kw in SERIES_HINTS:
        if kw in series_desc:
            score += 2
            reasons.append(f"series_desc~{kw}")
            break

    # 4) ImageType contains "SECONDARY" or "DERIVED" often for captures/scans
    if "secondary" in image_type or "derived" in image_type:
        score += 1
        reasons.append("image_type=secondary/derived")

    # 5) Burned-in annotation might indicate label/cover captures
    if burned == "YES":
        score += 1
        reasons.append("burned_in_annotation=YES")

    # 6) Aspect ratio not 1:1 (CT is commonly square 512x512; covers vary)
    if rows and cols:
        ar = ratio(rows, cols)
        if ar >= 1.3:
            score += 1
            reasons.append(f"aspect_ratio≈{ar:.2f}")

        # Big square grayscale 512-ish screams CT body slice → downweight
        if modality == "CT" and photometric.startswith("MONOCHROME"):
            # Typical CT traits; push score down
            if rows in (512, 1024) and cols in (512, 1024):
                score -= 3
                reasons.append("ct_like_square_slice")
            else:
                score -= 1
                reasons.append("ct_grayscale")

    # Gentle nudge if modality is empty but color-ish signals exist
    if not modality and (photometric in {"RGB", "PALETTE COLOR"} or samples == 3):
        score += 1
        reasons.append("unknown_modality_but_colorish")

    return score, reasons


def iter_candidates(root, exts=(".dcm", ".dat")):
    for p in Path(root).rglob("*"):
        if not p.is_file():
            continue
        if exts and p.suffix.lower() not in exts:
            # Some sites ditch extensions; peek header quickly
            try:
                if not is_dicom(str(p)):
                    continue
            except Exception:
                continue
        else:
            try:
                if not is_dicom(str(p)):
                    continue
            except Exception:
                continue
        yield p


def main():
    ap = argparse.ArgumentParser(description="Scout likely cover-slide DICOMs fast.")
    ap.add_argument("path", help="Directory to scan (e.g., /data2/radimages/rsnacontrolCT)")
    ap.add_argument(
        "--top", type=int, default=50, help="Show top-N candidates (default: 50)"
    )
    ap.add_argument(
        "--csv", type=str, default="", help="Optional CSV path to write results"
    )
    ap.add_argument(
        "--limit", type=int, default=0, help="Stop after reading N files (0 = no limit)"
    )
    ap.add_argument("--verbose", action="store_true", help="Print reasons for scoring")
    args = ap.parse_args()

    rows_out = []
    count = 0

    for p in iter_candidates(args.path):
        try:
            ds = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        except Exception:
            continue

        score, reasons = score_dicom(ds)
        modality = str(safe_get(ds, "Modality", ""))
        series_desc = str(safe_get(ds, "SeriesDescription", ""))
        photometric = str(safe_get(ds, "PhotometricInterpretation", ""))
        samples = safe_get(ds, "SamplesPerPixel", "")
        rows_tag = safe_get(ds, "Rows", "")
        cols_tag = safe_get(ds, "Columns", "")
        burned = str(safe_get(ds, "BurnedInAnnotation", ""))

        rows_out.append(
            {
                "path": str(p),
                "score": score,
                "modality": modality,
                "series_description": series_desc,
                "photometric": photometric,
                "samples_per_pixel": samples,
                "rows": rows_tag,
                "cols": cols_tag,
                "burned_in_annotation": burned,
            }
        )

        count += 1
        if args.limit and count >= args.limit:
            break

    # Rank by score desc, then surface some context-heavy fields
    rows_out.sort(key=lambda r: r["score"], reverse=True)

    print(f"\nScanned {len(rows_out)} DICOMs under {args.path}")
    print(f"Top {min(args.top, len(rows_out))} likely cover slides:\n")

    header = [
        "rank",
        "score",
        "modality",
        "photometric",
        "samples_per_pixel",
        "rows",
        "cols",
        "burned_in_annotation",
        "series_description",
        "path",
    ]
    print("\t".join(header))

    for i, r in enumerate(rows_out[: args.top], start=1):
        line = [
            str(i),
            str(r["score"]),
            r["modality"],
            r["photometric"],
            str(r["samples_per_pixel"]),
            str(r["rows"]),
            str(r["cols"]),
            r["burned_in_annotation"],
            re.sub(r"\s+", " ", r["series_description"]).strip()[:80],
            r["path"],
        ]
        print("\t".join(line))
        if args.verbose:
            # Recompute reasons (cheap) just for display
            try:
                ds = pydicom.dcmread(r["path"], stop_before_pixels=True, force=True)
                _, reasons = score_dicom(ds)
                print("   reasons:", ", ".join(reasons))
            except Exception:
                pass

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
            writer.writeheader()
            writer.writerows(rows_out)
        print(f"\nCSV written → {args.csv}")


if __name__ == "__main__":
    main()
