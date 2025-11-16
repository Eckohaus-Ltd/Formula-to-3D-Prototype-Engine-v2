#!/usr/bin/env python3
"""
fetch_iers_data.py

Fetches the canonical IERS RS/PC dataset (ser7.dat),
parses *combined* and *prediction* Earth orientation parameters,
merges with existing formula-derived rows,
and writes a stable volumetric_data.json + PNG charts.

Designed for GitHub Actions (gh-pages publishing).
"""

import os
import re
import json
import argparse
from datetime import datetime, date
import requests


# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
IERS_SER7_URL = os.getenv("IERS_SER7_URL", "https://maia.usno.navy.mil/ser7/ser7.dat")
DEBUG = os.getenv("IERS_DEBUG", "false").lower() == "true"


# ----------------------------------------------------------------------
# UTILITIES
# ----------------------------------------------------------------------
def debug(msg):
    if DEBUG:
        print(msg)


# ----------------------------------------------------------------------
# PARSER: ROBUST OPTION-B TOKEN PARSER
# ----------------------------------------------------------------------
def parse_ser7(text):
    """
    Returns:
        {
          "combined": [ ... ],
          "predictions": [ ... ]
        }
    """
    combined = []
    predictions = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        parts = stripped.split()

        # ---------------------------
        # PREDICTIONS BLOCK
        # Example:
        # 2025 11 14  60993 0.1565 0.3154 0.08640
        # ---------------------------
        if (
            len(parts) == 7
            and parts[0].isdigit()
            and len(parts[0]) == 4  # year
            and parts[3].isdigit()  # MJD
        ):
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            mjd = int(parts[3])
            x = float(parts[4])
            y = float(parts[5])
            ut1 = float(parts[6])

            iso = date(year, month, day).isoformat()
            predictions.append(
                {
                    "date": iso,
                    "year": year,
                    "month": month,
                    "day": day,
                    "mjd": mjd,
                    "x_arcsec": x,
                    "y_arcsec": y,
                    "ut1_utc_sec": ut1,
                    "source": "IERS Bulletin A – prediction",
                }
            )
            continue

        # ---------------------------
        # COMBINED BLOCK
        # Example:
        # 25 11 7 60986 0.16583 .00009 0.31782 .00009 0.088185 0.000014
        # ---------------------------
        if (
            len(parts) == 10
            and parts[0].isdigit()
            and len(parts[0]) <= 2   # yy
            and parts[3].isdigit()   # MJD
        ):
            yy = int(parts[0])
            year = 2000 + yy
            month = int(parts[1])
            day = int(parts[2])
            mjd = int(parts[3])

            x = float(parts[4])
            sx = float(parts[5])
            y = float(parts[6])
            sy = float(parts[7])
            ut1 = float(parts[8])
            sut1 = float(parts[9])

            iso = date(year, month, day).isoformat()
            combined.append(
                {
                    "date": iso,
                    "year": year,
                    "month": month,
                    "day": day,
                    "mjd": mjd,
                    "x_arcsec": x,
                    "x_err_arcsec": sx,
                    "y_arcsec": y,
                    "y_err_arcsec": sy,
                    "ut1_utc_sec": ut1,
                    "ut1_err_sec": sut1,
                    "source": "IERS Bulletin A – combined RS/PC",
                }
            )
            continue

    return {"combined": combined, "predictions": predictions}


# ----------------------------------------------------------------------
# CHART GENERATOR
# ----------------------------------------------------------------------
def save_charts(iers_combined, images_dir):
    if not os.path.exists(images_dir):
        os.makedirs(images_dir, exist_ok=True)

    if len(iers_combined) == 0:
        debug("[chart] No IERS combined rows → skipping chart")
        return

    mjd = [row["mjd"] for row in iers_combined]
    x = [row["x_arcsec"] for row in iers_combined]
    y = [row["y_arcsec"] for row in iers_combined]

    # Chart 1 — x/y drift
    plt.figure(figsize=(9, 5))
    plt.title("IERS: x/y Polar Motion (Combined EOP)")
    plt.plot(mjd, x, label="x (arcsec)")
    plt.plot(mjd, y, label="y (arcsec)")
    plt.legend()
    plt.xlabel("MJD")
    plt.ylabel("Arcseconds")
    path = os.path.join(images_dir, "iers.png")
    plt.savefig(path, dpi=160)
    plt.close()
    print(f"[fetch_iers] Chart saved → {path}")


# ----------------------------------------------------------------------
# MAIN ENTRY
# ----------------------------------------------------------------------
def main(output_json, images_dir):
    print(f"[fetch_iers] Fetching canonical IERS RS/PC dataset → {IERS_SER7_URL}")

    try:
        r = requests.get(IERS_SER7_URL, timeout=20)
        r.raise_for_status()
        text = r.text
    except Exception as e:
        print(f"[fetch_iers] ERROR retrieving ser7.dat: {e}")
        text = ""

    parsed = parse_ser7(text)

    combined = parsed["combined"]
    predictions = parsed["predictions"]

    print(
        f"[fetch_iers] Parsed {len(combined)} combined rows, "
        f"{len(predictions)} prediction rows (total: {len(combined)+len(predictions)})"
    )

    # load existing JSON (formula data)
    existing = {}
    if os.path.exists(output_json):
        try:
            with open(output_json, "r") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    formula_rows = existing.get("formula", [])

    payload = {
        "meta": {
            "source": IERS_SER7_URL,
            "retrieved_utc": datetime.utcnow().isoformat() + "Z",
        },
        "iers": {
            "combined_eop": combined,
            "predictions": predictions,
        },
        "formula": formula_rows,
    }

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[fetch_iers] volumetric_data.json updated → {len(combined)}+{len(predictions)} rows")

    save_charts(combined, images_dir)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output_json", required=True)
    ap.add_argument("--images_dir", required=True)
    args = ap.parse_args()
    main(args.output_json, args.images_dir)
