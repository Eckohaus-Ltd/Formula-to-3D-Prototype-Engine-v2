import pandas as pd
import requests
import json
from io import StringIO
import argparse
import os
import compute
import plotly.express as px
from datetime import datetime, timezone
import pathlib

# -------------------------------------------------------------------
# Canonical IERS RS/PC Source (USNO)
# -------------------------------------------------------------------

IERS_SER7 = "https://maia.usno.navy.mil/ser7/ser7.dat"

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def log(msg):
    print(f"[fetch_iers] {msg}")

def load_cached_json(cache_path):
    """Load existing volumetric_data.json from gh-pages/docs if needed."""
    try:
        cached = json.loads(pathlib.Path(cache_path).read_text())
        log("Loaded cached volumetric_data.json from gh-pages/docs.")
        return cached
    except Exception as e:
        log(f"No valid cache found → {e}")
        return {"iers": [], "formula": [], "iers_status": "unavailable"}

# -------------------------------------------------------------------
# IERS ser7.dat Fetch & Parse
# -------------------------------------------------------------------

def fetch_ser7():
    """
    Fetch RS/PC Combined Earth Orientation Parameters (ser7.dat)
    Format is fixed-width; we parse using whitespace splitting.
    """
    try:
        log(f"Fetching canonical IERS RS/PC dataset → {IERS_SER7}")
        r = requests.get(IERS_SER7, timeout=20)
        r.raise_for_status()
        text = r.text
    except Exception as e:
        log(f"IERS RS/PC fetch failed → {e}")
        return None

    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 8:
            continue

        try:
            year = int(parts[0])
            mjd = int(parts[1])
            xp = float(parts[2])    # arcseconds
            yp = float(parts[3])    # arcseconds
        except:
            continue

        rows.append({"year": year, "mjd": mjd, "x_pole": xp, "y_pole": yp})

    if rows:
        log(f"Parsed {len(rows)} rows from ser7.dat.")
        return pd.DataFrame(rows)

    log("ser7.dat parsed but no valid rows found.")
    return None

# -------------------------------------------------------------------
# Convert to 3D Points
# -------------------------------------------------------------------

def extract_3d_points(df):
    if df is None:
        return None

    required = ["x_pole", "y_pole", "year"]
    if any(col not in df.columns for col in required):
        log("Missing required columns for 3D extraction.")
        return None

    pts = []
    for _, row in df.iterrows():
        if pd.isnull(row["x_pole"]) or pd.isnull(row["y_pole"]) or pd.isnull(row["year"]):
            continue
        pts.append({
            "x": row["x_pole"],
            "y": row["y_pole"],
            "z": row["year"]
        })

    log(f"Extracted {len(pts)} 3D IERS points.")
    return pts

# -------------------------------------------------------------------
# Chart Rendering
# -------------------------------------------------------------------

def render_3d_chart(points, output_path, title="3D Scatter"):
    if not points:
        log(f"No points to render for {title}")
        return

    df = pd.DataFrame(points)
    fig = px.scatter_3d(df, x="x", y="y", z="z",
                        color="z", opacity=0.8, title=title)
    fig.write_image(output_path)
    log(f"Chart saved → {output_path}")

# -------------------------------------------------------------------
# Main Logic
# -------------------------------------------------------------------

def main(output_json, images_dir):

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)

    cache_path = output_json

    # ----------------------------------------------------
    # 1. IERS-ONLY FETCH → fallback to cache
    # ----------------------------------------------------

    df = fetch_ser7()
    iers_points = extract_3d_points(df) if df is not None else None

    if iers_points:
        data_source = "primary"
    else:
        cached = load_cached_json(cache_path)
        iers_points = cached.get("iers", [])
        data_source = "cached" if iers_points else "unavailable"

    # ----------------------------------------------------
    # 2. Formula Dataset
    # ----------------------------------------------------
    try:
        formula_points = compute.generate_formula_data()
    except Exception as e:
        log(f"Formula generation failed → {e}")
        formula_points = []

    # ----------------------------------------------------
    # 3. Build JSON
    # ----------------------------------------------------
    volumetric_data = {
        "iers": iers_points,
        "formula": formula_points,
        "iers_status": data_source,
        "last_test_run": datetime.now(timezone.utc).isoformat()
    }

    with open(output_json, "w") as f:
        json.dump(volumetric_data, f, indent=2)

    log(f"volumetric_data.json updated → "
        f"{len(iers_points)} IERS, {len(formula_points)} formula "
        f"(status: {data_source}).")

    # ----------------------------------------------------
    # 4. Charts
    # ----------------------------------------------------
    render_3d_chart(iers_points, os.path.join(images_dir, "iers.png"), "IERS Dataset")
    render_3d_chart(formula_points, os.path.join(images_dir, "formula.png"), "Formula Dataset")

# -------------------------------------------------------------------
# CLI Entry
# -------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch IERS data (ser7.dat) and output volumetric JSON + charts.")
    parser.add_argument(
        "--output_json",
        type=str,
        default="gh-pages/docs/volumetric_data.json",
        help="Path to output JSON file"
    )
    parser.add_argument(
        "--images_dir",
        type=str,
        default="gh-pages/docs/images",
        help="Directory for chart images"
    )
    args = parser.parse_args()

    main(args.output_json, args.images_dir)
