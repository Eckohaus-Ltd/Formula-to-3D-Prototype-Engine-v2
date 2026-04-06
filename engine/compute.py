#!/usr/bin/env python3
"""
compute.py — Formula-to-3D dataset generator
--------------------------------------------
Mitigation: Updated to align with AMRE 'formula' key and prevent null-overwrites.
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
    return datetime.now().astimezone().isoformat()

# ================================================================
#  Formula A (Page 1) — fixed local grid
# ================================================================

def compute_formula_a() -> Dict[str, Any]:
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

_AMRE_BRANCH = os.getenv("AMRE_PONG_BRANCH", "master")
AMRE_PONG_URL = os.getenv(
    "AMRE_PONG_URL",
    f"https://raw.githubusercontent.com/Eckohaus/Angular_Momentum_Reaction_Engine/{_AMRE_BRANCH}/exports/formulas/pong_phase_overlap.json"
)

def fetch_amre_pong_payload() -> Dict[str, Any] | None:
    """Fetch from AMRE with explicit error handling."""
    print(f"[compute] Fetching AMRE Pong dataset: {AMRE_PONG_URL}")
    try:
        # If private repo, we might need headers={'Authorization': f'token {os.getenv("AMRE_TOKEN")}'}
        resp = requests.get(AMRE_PONG_URL, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"[compute] ABORT: Fetch failed ({exc})")
        return None

def compute_formula_b_from_amre() -> Dict[str, Any] | None:
    """Convert AMRE 'formula' key → Formula-to-3D structure."""
    pong = fetch_amre_pong_payload()
    if not pong:
        return None

    # FIX: AMRE uses "formula", not "points"
    raw_points = pong.get("formula", [])
    
    if not isinstance(raw_points, list) or len(raw_points) == 0:
        print("[compute] ABORT: No valid points found in source JSON.")
        return None

    converted: List[Dict[str, float]] = []

    for p in raw_points:
        # Mapping logic with fallbacks
        x = p.get("overlap_real", p.get("x"))
        y = p.get("overlap_imag", p.get("y"))
        z = p.get("phase", p.get("z"))

        if x is not None and y is not None and z is not None:
            try:
                converted.append({"x": float(x), "y": float(y), "z": float(z)})
            except:
                continue

    if not converted:
        return None

    meta = pong.get("meta", {}) or {}
    meta_out = {
        "id": meta.get("id", "amre_pong_phase_overlap_v1"),
        "description": meta.get("description", "AMRE Pong phase overlap mapped to 3D."),
        "source_repo": "Eckohaus/Angular_Momentum_Reaction_Engine",
        "source_path": "exports/formulas/pong_phase_overlap.json",
        "fetched_utc": now_utc_iso(),
        "version": meta.get("version", "1.0.0"),
    }

    print(f"[compute] ✓ Processed {len(converted)} AMRE points")
    return {"meta": meta_out, "formula": converted}

# ================================================================
#  Main Execution
# ================================================================

if __name__ == "__main__":
    # Always update Page 1
    save_json("docs/volumetric/formula_a.json", compute_formula_a())
    
    # Conditionally update Page 2
    formula_b = compute_formula_b_from_amre()
    if formula_b:
        save_json("docs/volumetric/formula_b.json", formula_b)
    else:
        print("[compute] SKIPPING formula_b.json update to preserve existing data.")
        
    print("[compute] Completed execution cycle.")

def save_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    print(f"[compute] ✓ Wrote {path}")
