#!/usr/bin/env python3
"""
fetch_iers_data.py

Full ingestion pipeline for the canonical IERS Rapid Service/Prediction Center
dataset (ser7.dat). Parses both combined EOP and prediction blocks, merges with
existing formula-derived points, writes volumetric_data.json, and exports PNG
charts via Plotly/Kaleido.

This script must remain compatible with GitHub Actions (non-interactive).
"""

import os
import re
import json
import argparse
from datetime import date, datetime

import requests
import plotly.express as px
import pandas as pd


# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------

IERS_SER7_URL = os.getenv("IERS_SER7_URL", "https://maia.usno.navy.mil/ser7/ser7.dat")
DEBUG = os.getenv("IERS_DEBUG", "false").lower() == "true"


def debug(msg: str):
    if DEBUG:
        print(f"[debug] {msg}")


# ----------------------------------------------------------------------
# PARSER: Robust Option-B tokenizer for ser7.dat
# ----------------------------------------------------------------------

def parse_ser7(text: str):
    """
    Parse RS/PC ser7.dat ASCII file.

    Returns:
        {
           "combined": [...],
           "predictions": [...]
        }
    """

    combined = []
    predictions = []

    for line in text.splitlines():
        parts = line.strip().split()
        if not parts:
            continue

        # -----------------------------------------
        # PREDICTIONS BLOCK
        # Example:
        # 2025 11 14 60993 0.1565 0.3154 0.08640
        # -----------------------------------------
        if (
            len(parts) == 7
            and parts[0].isdigit() and len(parts[0]) == 4
            and parts[3].isdigit()
        ):
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
            mjd = int(parts[3])
            x = float(parts[4])
            y = float(parts[5])
            ut1 = float(parts[6])

            iso = date(year, month, day).isoformat()
            predictions.append({
                "date": iso,
                "year": year,
                "month": month,
                "day": day,
                "mjd": mjd,
                "x_arcsec": x,
                "y_arcsec": y,
                "ut1_utc_sec": ut1,
                "source": "IERS Bulletin A – prediction"
            })
            continue

        # -----------------------------------------
        # COMBINED BLOCK (RS/PC)
        # Example:
        # 25 11 7 60986 0.16583 .00009 0.31782 .00009 0.088185 0.000014
        # -----------------------------------------
        if (
            len(parts) == 10
            and parts[0].isdigit() and len(parts[0]) <= 2
            and parts[3].isdigit()
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
            combined.append({
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
                "source": "IERS Bulletin A – combined RS/PC"
            })
            continue

    return {"combined": combined, "predictions": predictions}


# ----------------------------------------------------------------------
# PLOTLY CHART EXPORT (PNG)
# ----------------------------------------------------------------------

def save_charts(iers_combined, images_dir):
    if not os.path.exists(images_dir):
        os.makedirs(images_dir, exist_ok=True)

    if len(iers_combined) == 0:
        print("[fetch_iers] No IERS combined rows → skipping chart generation")
        return

    df = pd.DataFrame(iers_combined)

    fig = px.line(
        df,
        x="mjd",
        y=["x_arcsec", "y_arcsec"],
        labels={"mjd": "MJD", "value": "Arcseconds"},
        title="IERS: Polar Motion (Combined RS/PC)",
    )

    out_path = os.path.join(images_dir, "iers.png")
    fig.write_image(out_path)
    print(f"[fetch_iers] Chart saved → {out_path}")


# ----------------------------------------------------------------------
# MAIN PIPELINE
# ----------------------------------------------------------------------

def main(output_json: str, images_dir: str):

    print(f"[fetch_iers] Fetching canonical IERS RS/PC dataset → {IERS_SER7_URL}")

    # -------------------------------
    # Fetch raw text from RS/PC server
    # -------------------------------
    try:
        r = requests.get(IERS_SER7_URL, timeout=20)
        r.raise_for_status()
        raw = r.text
    except Exception as e:
        print(f"[fetch_iers] ERROR fetching ser7.dat: {e}")
        raw = ""

    parsed = parse_ser7(raw)
    combined = parsed["combined"]
    predictions = parsed["predictions"]

    print(
        f"[fetch_iers] Parsed {len(combined)} combined rows, "
        f"{len(predictions)} prediction rows (total: {len(combined) + len(predictions)})"
    )

    # -------------------------------
    # Load existing formula data
    # -------------------------------
    existing = {}
    if os.path.exists(output_json):
        try:
            with open(output_json, "r") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    formula_rows = existing.get("formula", [])

    # -------------------------------
    # Build final payload
    # -------------------------------
    payload = {
        "meta": {
            "source": IERS_SER7_URL,
            "retrieved_utc": datetime.now().astimezone().isoformat(),
        },
        "iers": {
            "combined_eop": combined,
            "predictions": predictions,
        },
        "formula": formula_rows,
    }

    # -------------------------------
    # Write JSON
    # -------------------------------
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"[fetch_iers] volumetric_data.json updated → {len(combined)}+{len(predictions)} rows")

    # -------------------------------
    # Render PNG charts
    # -------------------------------
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
