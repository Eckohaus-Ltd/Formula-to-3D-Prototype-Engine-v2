#!/usr/bin/env python3
# compute.py — Formula-to-3D dataset generator
# --------------------------------------------
# Outputs:
#   docs/volumetric/formula_a.json  → Page 1 (local grid demo)
#   docs/volumetric/formula_b.json  → Page 2 (AMRE → volumetric)

import json
import math
import os
from datetime import datetime
import requests


# ================================================================
#  Formula A — Local demonstration grid (Page 1)
# ================================================================

def compute_formula_a():
    """
    Simple local 10×10 grid demo used for Page 1.

    z = sqrt(x * y)  (non-trivial surface)
    """
    points = []
    for x in range(10):
        for y in range(10):
            z = math.sqrt(x * y) if x * y > 0 else 0.0
            points.append({"x": x, "y": y, "z": z})

    return {
        "meta": {
            "id": "formula_a_e_mc2_demo",
            "description": "Local E = mc² placeholder grid for Page 1.",
            "generated_utc": datetime.now().astimezone().isoformat(),
            "version": "1.0.0",
        },
        "formula": points,
    }


# ================================================================
#  Formula B — AMRE → Formula-to-3D (Page 2)
# ================================================================

AMRE_PONG_URL = os.getenv(
    "AMRE_PONG_URL",
    "https://raw.githubusercontent.com/Eckohaus/Angular_Momentum_Reaction_Engine_v2"
    "/main/exports/formulas/pong_phase_overlap.json"
)


def fetch_amre_pong_payload():
    """
    Pull the Pong Phase Overlap dataset from AMRE.
    """
    print(f"[compute] Fetching AMRE Pong dataset: {AMRE_PONG_URL}")
    try:
        resp = requests.get(AMRE_PONG_URL, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        print("[compute] ✓ AMRE payload fetched successfully")
        return payload
    except Exception as e:
        print(f"[compute] WARNING: Failed to fetch AMRE dataset: {e}")
        return {"meta": {"error": str(e)}, "points": []}


def compute_formula_b_from_amre():
    """
    Convert AMRE's polar lattice → Formula-to-3D 3D scatter dataset.

    Mapping:
      x := overlap_real  (fallback: x)
      y := overlap_imag  (fallback: y)
      z := phase

    Output format:
      {
         "meta": {...},
         "formula": [
             {"x": <float>, "y": <float>, "z": <float>},
             ...
         ]
      }
    """
    pong = fetch_amre_pong_payload()

    # Validate structure
    points = pong.get("points", [])
    if not isinstance(points, list):
        print(f"[compute] ERROR: 'points' key invalid; got type={type(points)}")
        points = []

    converted = []

    for p in points:
        x = p.get("overlap_real", p.get("x"))
        y = p.get("overlap_imag", p.get("y"))
        z = p.get("phase")

        if x is None or y is None or z is None:
            print(f"[compute] Skipping malformed AMRE point: {p}")
            continue

        try:
            converted.append({
                "x": float(x),
                "y": float(y),
                "z": float(z)
            })
        except Exception as e:
            print(f"[compute] Conversion error for point {p}: {e}")
            continue

    # Ensure the output is never empty
    if not converted:
        print("[compute] WARNING: No valid AMRE points found. "
              "Injecting placeholder (0,0,0).")
        converted = [{"x": 0.0, "y": 0.0, "z": 0.0}]

    # Build metadata
    meta = pong.get("meta", {})
    meta_out = {
        "id": meta.get("id", "amre_pong_phase_overlap_v1"),
        "description": meta.get(
            "description",
            "AMRE Pong phase overlap mapped to (Re overlap, Im overlap, phase)."
        ),
        "source_repo": meta.get(
            "source_repo", "Eckohaus/Angular_Momentum_Reaction_Engine_v2"
        ),
        "source_path": meta.get(
            "source_path", "exports/formulas/pong_phase_overlap.json"
        ),
        "fetched_utc": datetime.now().astimezone().isoformat(),
        "version": meta.get("version", "1.0.0"),
    }

    print(f"[compute] ✓ Converted {len(converted)} AMRE points")

    return {"meta": meta_out, "formula": converted}


# ================================================================
#  Utility
# ================================================================

def save_json(path: str, payload: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"[compute] ✓ Wrote {path}")


# ================================================================
#  Main execution
# ================================================================

if __name__ == "__main__":
    save_json("docs/volumetric/formula_a.json", compute_formula_a())
    save_json("docs/volumetric/formula_b.json", compute_formula_b_from_amre())
    print("[compute] Completed all volumetric dataset outputs.")
