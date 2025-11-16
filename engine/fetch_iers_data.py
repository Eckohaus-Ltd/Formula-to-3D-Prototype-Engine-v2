import pandas as pd
import requests
import json
from io import StringIO
import argparse
import os
import compute  # assumes compute.py defines generate_formula_data()
import plotly.express as px
from datetime import datetime, timezone
import pathlib

# Primary IERS URL
CSV_URL = "https://datacenter.iers.org/data/csv/bulletina.longtime.csv"

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
        return {"iers": [], "formula": []}

# -------------------------------------------------------------------
# CSV Fetch & Parse
# -------------------------------------------------------------------

def fetch_and_parse_csv(url):
    """Download CSV and parse semicolon-delimited content."""
    try:
        log(f"Attempting IERS download: {url}")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        log(f"IERS download failed → {e}")
        return None

    try:
        df = pd.read_csv(StringIO(response.text), sep=';', engine='python')
        log("IERS CSV parsed successfully.")
        return df
    except pd.errors.ParserError as e:
        log(f"CSV parse failed → {e}")
        return None

# -------------------------------------------------------------------
# Extract IERS 3D Points
# -------------------------------------------------------------------

def extract_3d_points(df):
    """Extract x_pole, y_pole, Year columns for volumetric display."""
    if df is None:
        return None

    required_cols = ["x_pole", "y_pole", "Year"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        log(f"Missing expected IERS columns: {missing}")
        return None

    points = [
        {"x": row["x_pole"], "y": row["y_pole"], "z": row["Year"]}
        for _, row in df.iterrows()
        if not pd.isnull(row["x_pole"])
        and not pd.isnull(row["y_pole"])
        and not pd.isnull(row["Year"])
    ]

    log(f"Extracted {len(points)} IERS points.")
    return points

# -------------------------------------------------------------------
# Chart Rendering
# -------------------------------------------------------------------

def render_3d_chart(points, output_path, title="3D Scatter"):
    """Render a 3D scatter plot and save as PNG using Plotly + Kaleido."""
    if not points:
        log(f"No points to render for {title}.")
        return

    df = pd.DataFrame(points)
    fig = px.scatter_3d(df, x="x", y="y", z="z",
                        color="z", title=title, opacity=0.8)
    fig.write_image(output_path)
    log(f"Pre-rendered chart saved to {output_path}")

# -------------------------------------------------------------------
# Main Logic (with caching + fallback)
# -------------------------------------------------------------------

def main(output_json, images_dir):

    # Ensure directories exist
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)

    # Location of cached volumetric_data.json (same as output)
    cache_path = output_json

    # ----------------------------------------------------
    # 1. Try fetch IERS CSV
    # ----------------------------------------------------
    df = fetch_and_parse_csv(CSV_URL)
    iers_points = extract_3d_points(df)

    if iers_points is None or len(iers_points) == 0:
        log("IERS unavailable → using cached dataset.")
        cached = load_cached_json(cache_path)
        iers_points = cached.get("iers", [])
        data_source = "cached"
    else:
        data_source = "fetched"

    # ----------------------------------------------------
    # 2. Generate formula points (your compute engine)
    # ----------------------------------------------------
    try:
        formula_points = compute.generate_formula_data()
    except Exception as e:
        log(f"Error generating formula points: {e}")
        formula_points = []

    # ----------------------------------------------------
    # 3. Build JSON output
    # ----------------------------------------------------
    volumetric_data = {
        "iers": iers_points,
        "formula": formula_points,
        "iers_status": data_source,
        "last_test_run": datetime.now(timezone.utc).isoformat()
    }

    with open(output_json, "w") as f:
        json.dump(volumetric_data, f, indent=2)

    log(f"volumetric_data.json updated: {len(iers_points)} IERS points, "
        f"{len(formula_points)} formula points (source: {data_source}).")

    # ----------------------------------------------------
    # 4. Pre-render charts
    # ----------------------------------------------------
    render_3d_chart(
        iers_points,
        os.path.join(images_dir, "iers.png"),
        title="IERS Dataset"
    )
    render_3d_chart(
        formula_points,
        os.path.join(images_dir, "formula.png"),
        title="Formula Dataset"
    )


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
