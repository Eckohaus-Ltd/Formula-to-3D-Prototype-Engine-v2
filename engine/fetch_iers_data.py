import pandas as pd
import requests
import json
import argparse
import os
import compute
import plotly.express as px
from datetime import datetime, timezone
import pathlib

# ================================================================
#  Canonical IERS Rapid Service / Prediction Center (RS/PC) source
# ================================================================
IERS_SER7_URL = "https://maia.usno.navy.mil/ser7/ser7.dat"


# ================================================================
#  Logging Helper
# ================================================================
def log(msg):
    print(f"[fetch_iers] {msg}")


# ================================================================
#  Cache Loader
# ================================================================
def load_cached_json(cache_path):
    try:
        cached = json.loads(pathlib.Path(cache_path).read_text())
        log("Loaded cached volumetric_data.json from gh-pages/docs.")
        return cached
    except Exception as e:
        log(f"No valid cache found → {e}")
        return {"iers": [], "formula": [], "iers_status": "unavailable"}


# ================================================================
#  Temporary Debug: Dump Raw ser7.dat for Analysis
# ================================================================
def debug_dump_raw(text):
    print("RAW_SER7_START")
    print(text)
    print("RAW_SER7_END")


# ================================================================
#  Fixed-Width SER7 Parser (Prototype — final version after raw dump)
# ================================================================
def parse_ser7(text):
    """
    IMPORTANT:
    This parser is a placeholder until we see the exact raw ser7.dat.
    After we see RAW_SER7_START → RAW_SER7_END, we will finalize this.
    """
    rows = []

    for line in text.splitlines():
        if not line.strip():
            continue
        if not line[:4].isdigit():
            continue

        try:
            year = int(line[0:4].strip())
            doy = int(line[5:8].strip())
            mjd = float(line[9:16].strip())
            xp = float(line[17:27].strip())
            yp = float(line[28:38].strip())
            ut1 = float(line[39:52].strip())
            lod = float(line[53:62].strip())

            # Convert arcsec → milliarcsec (mas)
            xp_mas = xp * 1000.0
            yp_mas = yp * 1000.0

            z = year + (doy / 366.0)

            rows.append({
                "year": year,
                "doy": doy,
                "mjd": mjd,
                "xp": xp_mas,
                "yp": yp_mas,
                "ut1_utc": ut1,
                "lod": lod,
                "x": xp_mas,
                "y": yp_mas,
                "z": z
            })

        except Exception:
            continue

    return rows


# ================================================================
#  Fetch SER7 Live Dataset
# ================================================================
def fetch_ser7():
    try:
        log(f"Fetching canonical IERS RS/PC dataset → {IERS_SER7_URL}")
        r = requests.get(IERS_SER7_URL, timeout=20)
        r.raise_for_status()

        # 🔥 Dump raw data for inspection
        debug_dump_raw(r.text)

        rows = parse_ser7(r.text)
        log(f"Parsed {len(rows)} rows from ser7.dat.")
        return rows

    except Exception as e:
        log(f"SER7 fetch failed → {e}")
        return None


# ================================================================
#  Chart Renderer
# ================================================================
def render_3d_chart(points, output_path, title="3D Scatter"):
    if not points:
        log(f"No points to render for {title}")
        return

    df = pd.DataFrame(points)
    fig = px.scatter_3d(
        df,
        x="x", y="y", z="z",
        color="z",
        opacity=0.8,
        title=title
    )
    fig.write_image(output_path)
    log(f"Chart saved → {output_path}")


# ================================================================
#  Main Routine
# ================================================================
def main(output_json, images_dir):

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)

    cache_path = output_json

    # -------------------------------------------------------------
    # 1. Live SER7 → fallback to cache
    # -------------------------------------------------------------
    ser7 = fetch_ser7()

    if ser7 and len(ser7) > 0:
        data_source = "primary"
        iers_points = ser7
    else:
        cached = load_cached_json(cache_path)
        iers_points = cached.get("iers", [])
        data_source = "cached" if iers_points else "unavailable"

    # -------------------------------------------------------------
    # 2. Formula dataset
    # -------------------------------------------------------------
    try:
        formula_points = compute.generate_formula_data()
    except Exception as e:
        log(f"Formula generation failed → {e}")
        formula_points = []

    # -------------------------------------------------------------
    # 3. JSON output
    # -------------------------------------------------------------
    volumetric_data = {
        "iers": iers_points,
        "formula": formula_points,
        "iers_status": data_source,
        "last_test_run": datetime.now(timezone.utc).isoformat(),
        "iers_provenance": {
            "primary_source": IERS_SER7_URL,
            "description": "IERS Rapid Service / Prediction Center (RS/PC) daily combination/prediction series (ser7.dat)",
            "approx_rows": len(iers_points)
        }
    }

    with open(output_json, "w") as f:
        json.dump(volumetric_data, f, indent=2)

    log(
        f"volumetric_data.json updated → "
        f"{len(iers_points)} IERS rows, "
        f"{len(formula_points)} formula rows "
        f"(status: {data_source})."
    )

    # -------------------------------------------------------------
    # 4. Charts
    # -------------------------------------------------------------
    render_3d_chart(iers_points, os.path.join(images_dir, "iers.png"), "IERS Dataset")
    render_3d_chart(formula_points, os.path.join(images_dir, "formula.png"), "Formula Dataset")


# ================================================================
#  CLI
# ================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch IERS ser7 dataset and build volumetric data.")
    parser.add_argument("--output_json", type=str, default="gh-pages/docs/volumetric_data.json")
    parser.add_argument("--images_dir", type=str, default="gh-pages/docs/images")
    args = parser.parse_args()

    main(args.output_json, args.images_dir)
