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
# Primary + Fallback URLs
# -------------------------------------------------------------------

IERS_PRIMARY = "https://datacenter.iers.org/data/csv/bulletina.longtime.csv"

# NASA Earthdata mirror (authenticated)
# NOTE: Replace with the exact mirror endpoint once chosen
NASA_FALLBACK_URL = "https://cddis.nasa.gov/archive/slr/products/iers/bulletin_a.csv"

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def log(msg):
    print(f"[fetch_iers] {msg}")

def load_cached_json(cache_path):
    """Load the existing volumetric_data.json from gh-pages/docs."""
    try:
        cached = json.loads(pathlib.Path(cache_path).read_text())
        log("Loaded cached volumetric_data.json from gh-pages/docs.")
        return cached
    except Exception as e:
        log(f"No valid cache found → {e}")
        return {"iers": [], "formula": [], "iers_status": "unavailable"}

# -------------------------------------------------------------------
# Fetchers
# -------------------------------------------------------------------

def fetch_from_primary():
    """Attempt to fetch IERS Bulletin A from the primary IERS server."""
    try:
        log(f"Attempting primary IERS download: {IERS_PRIMARY}")
        r = requests.get(IERS_PRIMARY, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text), sep=';', engine='python')
        log("Primary IERS CSV parsed successfully.")
        return df
    except Exception as e:
        log(f"Primary IERS fetch failed → {e}")
        return None


def fetch_from_earthdata():
    """Attempt to fetch from NASA Earthdata using Bearer token."""
    token = os.getenv("EARTHDATA_BEARER_TOKEN")
    if not token:
        log("No EARTHDATA_BEARER_TOKEN provided. Skipping fallback.")
        return None

    headers = {"Authorization": f"Bearer {token}"}

    try:
        log(f"Attempting NASA Earthdata fallback: {NASA_FALLBACK_URL}")
        r = requests.get(NASA_FALLBACK_URL, headers=headers, timeout=20)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text), sep=';', engine='python')
        log("NASA fallback CSV parsed successfully.")
        return df
    except Exception as e:
        log(f"NASA fallback fetch failed → {e}")
        return None

# -------------------------------------------------------------------
# Extract IERS 3D Points
# -------------------------------------------------------------------

def extract_3d_points(df):
    if df is None:
        return None

    required_cols = ["x_pole", "y_pole", "Year"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        log(f"Missing expected IERS columns: {missing}")
        return None

    pts = [
        {"x": row["x_pole"], "y": row["y_pole"], "z": row["Year"]}
        for _, row in df.iterrows()
        if not pd.isnull(row["x_pole"])
        and not pd.isnull(row["y_pole"])
        and not pd.isnull(row["Year"])
    ]

    log(f"Extracted {len(pts)} IERS points.")
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
    log(f"Pre-rendered chart saved to {output_path}")

# -------------------------------------------------------------------
# Main Logic
# -------------------------------------------------------------------

def main(output_json, images_dir):

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)

    cache_path = output_json

    # ----------------------------------------------------
    # 1. PRIMARY → if fail → EARTHDATA → if fail → CACHE
    # ----------------------------------------------------

    data_source = "unavailable"

    # Try primary
    df = fetch_from_primary()
    iers_points = extract_3d_points(df) if df is not None else None
    if iers_points:
        data_source = "ok"
    else:
        # Try NASA fallback
        df_fb = fetch_from_earthdata()
        iers_points = extract_3d_points(df_fb) if df_fb is not None else None

        if iers_points:
            data_source = "fallback"
        else:
            # Cache fallback
            cached = load_cached_json(cache_path)
            iers_points = cached.get("iers", [])
            if iers_points:
                data_source = "cached"
            else:
                log("No cached IERS data available — using empty array.")
                data_source = "unavailable"
                iers_points = []

    # ----------------------------------------------------
    # 2. Formula dataset
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
        f"{len(iers_points)} IERS points, "
        f"{len(formula_points)} formula points "
        f"(status: {data_source}).")

    # ----------------------------------------------------
    # 4. Pre-render charts
    # ----------------------------------------------------
    render_3d_chart(iers_points, os.path.join(images_dir, "iers.png"), "IERS Dataset")
    render_3d_chart(formula_points, os.path.join(images_dir, "formula.png"), "Formula Dataset")


# -------------------------------------------------------------------
# CLI Entry
# -------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch IERS data and output volumetric JSON + charts.")
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
        help="Directory to store pre-rendered chart images"
    )
    args = parser.parse_args()

    main(args.output_json, args.images_dir)
