import json
import math
import os
from datetime import datetime

import requests  # used to pull AMRE JSON


# --------------------------------------------------------------------
# Local Formula A – E = mc² style placeholder (Page 1 baseline)
# --------------------------------------------------------------------

def compute_formula_a():
    """
    Simple local grid, treated as a lightweight E = mc² placeholder.

    We map:
        z = sqrt(x * y)  (for x, y >= 0)
    on a small integer grid, just to keep things visually non-trivial.
    """
    points = []
    for x in range(10):
        for y in range(10):
            z = math.sqrt(x * y) if x * y > 0 else 0.0
            points.append({"x": x, "y": y, "z": z})

    return {
        "meta": {
            "id": "formula_a_e_mc2_demo",
            "description": "Local demo grid (E = mc² placeholder) for Page 1.",
            "generated_utc": datetime.now().astimezone().isoformat(),
            "version": "1.0.0",
        },
        "formula": points,
    }


# --------------------------------------------------------------------
# Remote Formula B – AMRE Pong Phase Overlap (Page 2)
# --------------------------------------------------------------------

AMRE_PONG_URL = os.getenv(
    "AMRE_PONG_URL",
    # Default: raw JSON from AMRE main branch
    "https://raw.githubusercontent.com/Eckohaus/Angular_Momentum_Reaction_Engine_v2/"
    "main/exports/formulas/pong_phase_overlap.json",
)


def fetch_amre_pong_payload():
    """
    Fetch the Pong phase dataset exported by AMRE.

    Expected schema:

    {
      "meta": {...},
      "points": [
        { "x": ..., "y": ..., "phase": ..., "overlap_real": ..., "overlap_imag": ... },
        ...
      ]
    }
    """
    try:
        resp = requests.get(AMRE_PONG_URL, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        print(f"[compute] Fetched AMRE Pong dataset from {AMRE_PONG_URL}")
        return payload
    except Exception as e:
        print(f"[compute] WARNING: failed to fetch AMRE Pong dataset: {e}")
        return {"meta": {"error": str(e)}, "points": []}


def compute_formula_b_from_amre():
    """
    Convert AMRE's Pong phase lattice into the internal 'formula' format
    used by Formula-to-3D.

    We map:
      - x := overlap_real
      - y := overlap_imag
      - z := phase

    so that the 3D scatter becomes a direct visualisation of:
      overlap = A(r) e^{iφ}
      point ↦ (Re overlap, Im overlap, phase).
    """
    pong = fetch_amre_pong_payload()
    points = pong.get("points", [])

    converted = []
    for p in points:
        # Fallback defaults in case AMRE changes schema
        x = p.get("overlap_real", p.get("x", 0.0))
        y = p.get("overlap_imag", p.get("y", 0.0))
        z = p.get("phase", 0.0)
        converted.append({"x": x, "y": y, "z": z})

    meta = pong.get("meta", {})
    meta_out = {
        "id": meta.get("id", "amre_pong_phase_overlap_v1"),
        "description": meta.get(
            "description",
            "AMRE Pong phase overlap mapped to (Re overlap, Im overlap, phase).",
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

    return {
        "meta": meta_out,
        "formula": converted,
    }


# --------------------------------------------------------------------
# Utility
# --------------------------------------------------------------------

def save_json(path: str, payload: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


if __name__ == "__main__":
    # NOTE:
    #   docs/volumetric/formula_a.json → Page 1
    #   docs/volumetric/formula_b.json → Page 2 (AMRE Pong)
    save_json("docs/volumetric/formula_a.json", compute_formula_a())
    save_json("docs/volumetric/formula_b.json", compute_formula_b_from_amre())
    print("[compute] Wrote formula_a.json and formula_b.json under docs/volumetric/")
