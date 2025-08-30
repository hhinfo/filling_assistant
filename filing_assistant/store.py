from __future__ import annotations
from typing import Dict, Any
import json, os
from copy import deepcopy

def load_store(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"sheets": {}}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_store(path: str, obj: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def merge_patterns(store: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    out = deepcopy(store)
    for sheet, payload in incoming.get("sheets", {}).items():
        target = out["sheets"].setdefault(sheet, {"header_map": {}, "columns_to_fill": [], "column_positions": {}, "verifications": {}})
        for norm, variants in payload.get("header_map", {}).items():
            tgtset = set(target["header_map"].get(norm, []))
            tgtset.update(variants)
            target["header_map"][norm] = sorted(tgtset)
        merged = set(target.get("columns_to_fill", []))
        merged.update(payload.get("columns_to_fill", []))
        target["columns_to_fill"] = sorted(merged)
        for norm, pos in payload.get("column_positions", {}).items():
            target["column_positions"][norm] = pos
        for raw, v in payload.get("verifications", {}).items():
            target["verifications"][raw] = v
    return out
