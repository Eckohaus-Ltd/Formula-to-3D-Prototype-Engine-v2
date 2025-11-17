#!/usr/bin/env python3
"""
compute.py — Formula-to-3D dataset generator
--------------------------------------------

Outputs:
  docs/volumetric/formula_a.json  → Page 1 (local demo grid)
  docs/volumetric/formula_b.json  → Page 2 (AMRE → volumetric 3D scatter)

Formula A:
  Simple 10×10 grid with a non-linear surface z = sqrt(x * y).

Formula B:
  Pulls AMRE's Pong Phase Overlap export from Angular_Momentum_Reaction_Engine
  and maps it onto (x, y, z) for volumetric visualisation.

Environment overrides:
  AMRE_PONG_BRANCH  → branch name to use when building the default raw URL
  AMRE_PONG_URL     → full override of the Pong JSON URL (takes precedence)
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime
from typing import Any, Dict, List

import requests

# ================================================================
#  Helpers
# ================================================================


def now_utc_iso() -> str:
    """Return an ISO 8601 timestamp with timezone information."""
    return datetime.now().astimezone().isoformat()


# ================================================================
#  Formula A — Local demonstration grid (Page 1)
# ================================================================


def compute_formula_a() -> Dict[str, Any]:
    """
    Simple 10×10 grid demo for Page 1.

    Surface:
      z = sqrt(x * y)

    This is intentionally non-linear but cheap to compute, giving Plotly
    something interesting to render without depending on external data.
    """
    points: List[Dict[str, float]] = []

    for x in range(10):
        for y in range(10):
            z = math.sqrt(x * y) if x * y > 0 else 0.0
            points.append({"x": float(x), "y": float(y), "z": float(z)})

    return {
        "meta": {
            "id": "formula_a_e_mc2_demo",
            "description": "Local demo grid (E = mc² placeholder) for Page 1.",
            "generated_utc": now_utc_iso(),
            "version": "1.0.0",
        },
        "formula": points,
    }


# ================================================================
#  Formula B — AMRE → Formula-to-3D (Page 2)
# ================================================================

# Default branch for AMRE raw exports. The repo currently uses `master`,
# but this can be overridden if you later introduce a `main` branch.
_AMRE_DEFAULT_BRANCH = os.getenv("AMRE_PONG_BRANCH", "master")

AMRE_PONG_URL = os.getenv(
    "AMRE_PONG_URL",
    (
        "https://raw.githubusercontent.com/"
        "Eckohaus/Angular_Momentum_Reaction_Engine/"
        f"{_AMRE_DEFAULT_BRANCH}/exports/formulas/pong_phase_overlap.json"
    ),
)


def fetch_amre_pong_payload() -> Dict[str, Any]:
    """
    Fetch the phase/overlap lattice exported by AMRE.

    Returns a dict with at least:
      - meta: {...}
      - points: [ {...}, ... ]
    """
    print(f"[compute] Fetching AMRE Pong dataset: {AMRE_PONG_URL}")
    try:
        resp = requests.get(AMRE_PONG_URL, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        print("[compute] ✓ AMRE payload fetched successfully")
        return payload
    except Exception as exc:  # noqa: BLE001 (simple CLI script)
        print(f"[compute] WARNING: Failed to fetch AMRE dataset: {exc}")
        return {"meta": {"error": str(exc)}, "points": []}


def compute_formula_b_from_amre() -> Dict[str, Any]:
    """
    Convert AMRE's polar lattice into Formula-to-3D's volumetric dataset.

    Expected AMRE point schema (per tools/export_formulas.py):

      {
        "overlap_real": <float>  # real part of overlap (optional)
        "overlap_imag": <float>  # imaginary part of overlap (optional)
        "phase":        <float>, # phase angle
        "x":            <float>, # optional fallback real axis
        "y":            <float>, # optional fallback imag axis
        ...
      }

    Mapping into Formula-to-3D:

      x := overlap_real  (fallback to AMRE's x)
      y := overlap_imag  (fallback to AMRE's y)
      z := phase

    The output structure is:

      {
         "meta": {...},
         "formula": [
             {"x": <float>, "y": <float>, "z": <float>},
             ...
         ]
      }
    """
    pong = fetch_amre_pong_payload()

    # Ensure points array exists
    points = pong.get("points", [])
    if not isinstance(points, list):
        print(f"[compute] ERROR: AMRE 'points' is not a list (got {type(points)}).")
        points = []

    converted: List[Dict[str, float]] = []

    for p in points:
        x = p.get("overlap_real", p.get("x"))
        y = p.get("overlap_imag", p.get("y"))
        z = p.get("phase")

        # Skip malformed points
        if x is None or y is None or z is None:
            print(f"[compute] Skipping malformed point: {p}")
            continue

        try:
            converted.append(
                {
                    "x": float(x),
                    "y": float(y),
                    "z": float(z),
                }
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[compute] Conversion error for point {p}: {exc}")
            continue

    # Avoid empty output so Plotly always has *something* to render
    if not converted:
        print(
            "[compute] WARNING: No valid AMRE points found. "
            "Injecting placeholder point (0,0,0)."
        )
        converted = [{"x": 0.0, "y": 0.0, "z": 0.0}]

    # Construct metadata (preserve anything AMRE already wrote)
    meta = pong.get("meta", {}) or {}

    meta_out = {
        "id": meta.get("id", "amre_pong_phase_overlap_v1"),
        "description": meta.get(
            "description",
            "AMRE Pong phase overlap mapped to (Re overlap, Im overlap, phase).",
        ),
        "source_repo": meta.get(
            "source_repo", "Eckohaus/Angular_Momentum_Reaction_Engine"
        ),
        "source_path": meta.get(
            "source_path", "exports/formulas/pong_phase_overlap.json"
        ),
        "fetched_utc": now_utc_iso(),
        "version": meta.get("version", "1.0.0"),
    }

    print(f"[compute] ✓ Converted {len(converted)} AMRE points")
    return {"meta": meta_out, "formula": converted}


# ================================================================
#  I/O helpers
# ================================================================


def save_json(path: str, payload: Dict[str, Any]) -> None:
    """
    Write a JSON payload to disk, creating parent directories as needed.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    print(f"[compute] ✓ Wrote {path}")


# ================================================================
#  Main execution
# ================================================================


if __name__ == "__main__":
    save_json("docs/volumetric/formula_a.json", compute_formula_a())
    save_json("docs/volumetric/formula_b.json", compute_formula_b_from_amre())
    print("[compute] Completed all volumetric dataset outputs.")
