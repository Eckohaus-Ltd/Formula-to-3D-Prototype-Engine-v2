#!/usr/bin/env python3
"""
compute.py — Formula-to-3D dataset generator
--------------------------------------------

Outputs:
  docs/volumetric/formula_a.json  → Page 1 (local demo grid)
  docs/volumetric/formula_b.json  → Page 2 (AMRE → volumetric)

Formula A:
  Lightweight non-linear surface (z = sqrt(x*y)) rendered on Page 1.

Formula B:
  Fetches AMRE’s pong_phase_overlap.json and maps:
      x := overlap_real (fallback: x)
      y := overlap_imag (fallback: y)
      z := phase

Branch + URL logic (important):
  - AMRE currently uses `master`, not `main`
  - You can override the branch with AMRE_PONG_BRANCH
  - You can override the full URL with AMRE_PONG_URL
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime
from typing import Any, Dict, List

import requests


# ================================================================
#  Utility helpers
# ================================================================

def now_utc_iso() -> str:
    """Return timestamp in ISO8601 with timezone."""
    return datetime.now().astimezone().isoformat()


# ================================================================
#  Formula A (Page 1) — fixed local grid
# ================================================================

def compute_formula_a() -> Dict[str, Any]:
    """Simple 10×10 demo grid for Page 1."""
    points: List[Dict[str, float]] = []

    for x in range(10):
        for y in range(10):
            z = math.sqrt(x * y) if x * y > 0 else 0.0
            points.append({"x": float(x), "y": float(y), "z": float(z)})

    return {
        "meta": {
            "id": "formula_a_e_mc2_demo",
            "description": "Local non-linear grid (E = mc² placeholder) for Page 1.",
            "generated_utc": now_utc_iso(),
            "version": "1.0.0",
        },
        "formula": points,
    }


# ================================================================
#  Formula B (Page 2) — AMRE → Formula-to-3D mapping
# ================================================================

# Default: AMRE uses *master*.
_AMRE_BRANCH = os.getenv("AMRE_PONG_BRANCH", "master")

# If AMRE_PONG_URL provided, use it; otherwise construct raw/master URL.
AMRE_PONG_URL = os.getenv(
    "AMRE_PONG_URL",
    f"https://raw.githubusercontent.com/"
    f"Eckohaus/Angular_Momentum_Reaction_Engine/"
    f"{_AMRE_BRANCH}/exports/formulas/pong_phase_overlap.json"
)


def fetch_amre_pong_payload() -> Dict[str, Any]:
    """Fetch the pong-phase-overlap dataset from AMRE."""
    print(f"[compute] Fetching AMRE Pong dataset:")
    print(f"          → {AMRE_PONG_URL}")

    try:
        resp = requests.get(AMRE_PONG_URL, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
        print("[compute] ✓ Successfully fetched AMRE dataset")
        return payload

    except Exception as exc:
        print(f"[compute] WARNING: Fetch failed ({exc})")
        return {"meta": {"error": str(exc)}, "points": []}


def compute_formula_b_from_amre() -> Dict[str, Any]:
    """Convert AMRE points → Formula-to-3D volumetric structure."""
    pong = fetch_amre_pong_payload()

    points = pong.get("points", [])
    if not isinstance(points, list):
        print(f"[compute] ERROR: 'points' is not a list (got {type(points)})")
        points = []

    converted: List[Dict[str, float]] = []

    for p in points:
        x = p.get("overlap_real", p.get("x"))
        y = p.get("overlap_imag", p.get("y"))
        z = p.get("phase")

        if x is None or y is None or z is None:
            print(f"[compute] Skipping malformed point: {p}")
            continue

        try:
            converted.append({"x": float(x), "y": float(y), "z": float(z)})
        except Exception as exc:
            print(f"[compute] Conversion error for {p}: {exc}")
            continue

    # If AMRE fails, ensure one placeholder point exists
    if not converted:
        print("[compute] WARNING: No valid AMRE points → injecting (0,0,0)")
        converted = [{"x": 0.0, "y": 0.0, "z": 0.0}]

    meta = pong.get("meta", {}) or {}

    meta_out = {
        "id": meta.get("id", "amre_pong_phase_overlap_v1"),
        "description": meta.get(
            "description",
            "AMRE Pong phase overlap mapped to 3D (Re, Im, phase)."
        ),
        "source_repo": meta.get("source_repo", "Eckohaus/Angular_Momentum_Reaction_Engine"),
        "source_path": meta.get("source_path", "exports/formulas/pong_phase_overlap.json"),
        "fetched_utc": now_utc_iso(),
        "version": meta.get("version", "1.0.0"),
    }

    print(f"[compute] ✓ Converted {len(converted)} AMRE points")
    return {"meta": meta_out, "formula": converted}


# ================================================================
#  JSON save helper
# ================================================================

def save_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    print(f"[compute] ✓ Wrote {path}")


# ================================================================
#  Entrypoint
# ================================================================

if __name__ == "__main__":
    save_json("docs/volumetric/formula_a.json", compute_formula_a())
    save_json("docs/volumetric/formula_b.json", compute_formula_b_from_amre())
    print("[compute] Completed all volumetric dataset outputs.")
