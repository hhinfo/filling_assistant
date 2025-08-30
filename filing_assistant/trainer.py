from __future__ import annotations
from typing import Dict, Any, List, Tuple
import os, re, glob
from collections import defaultdict
from .io_utils import load_json, get_sheet, detect_header_row, list_value_columns
from .schema import normalize
from .verifier import verify_label

PAIR_EMPTY_RE = re.compile(r"(.*)(?:empty|blank)(.*)\.json$", re.IGNORECASE)
PAIR_FILLED_RE = re.compile(r"(.*)(?:filled?)(.*)\.json$", re.IGNORECASE)

def normalize_filename_for_pairing(filename: str) -> str:
    """Normalize filename to find matching pairs with different naming patterns"""
    # Remove common prefixes/suffixes that differ between empty and filled
    base = filename.lower()
    
    # Handle pattern: "1. Blank CPT_..." vs "4. Filled CPT_..."
    base = re.sub(r'^[0-9]+\.\s*(blank|filled?)\s*', '', base)
    
    # Handle pattern: "..._empty..." vs "..._filled..."
    base = re.sub(r'_?(empty|filled?|blank)_?', '_', base)
    
    # Handle pattern: "...Empty..." vs "...Filled..."
    base = re.sub(r'\s+(empty|filled?|blank)\s+', ' ', base)
    
    # Handle pattern: "...Empty.json" vs "...Filled.json" 
    base = re.sub(r'\s+(empty|filled?|blank)(_[^.]*)?\.json$', '.json', base)
    
    # Remove extra package/version suffixes like "- PKG1", "- PKG2", etc.
    base = re.sub(r'\s*-\s*pkg\d*', '', base)
    base = re.sub(r'\s*-\s*[a-z0-9]+$', '', base.replace('.json', '')) + '.json'
    
    # Clean up multiple underscores/spaces
    base = re.sub(r'_{2,}', '_', base)
    base = re.sub(r'\s{2,}', ' ', base)
    base = base.strip('_').strip()
    
    return base

def pair_training_files(data_dir: str, verbose: bool = False) -> List[Tuple[str, str]]:
    files = glob.glob(os.path.join(data_dir, "*.json"))
    empties, filleds = {}, {}
    
    if verbose:
        print(f"🔍 Scanning {len(files)} JSON files in '{data_dir}'...")
        print()
    
    for f in files:
        fname = os.path.basename(f)
        fname_lower = fname.lower()
        
        # Determine if this is an empty or filled file
        is_empty = any(word in fname_lower for word in ['empty', 'blank'])
        is_filled = any(word in fname_lower for word in ['filled', 'fill']) and not is_empty
        
        if is_empty or is_filled:
            # Normalize the filename to create a matching key
            key = normalize_filename_for_pairing(fname)
            
            if is_empty:
                empties[key] = f
                if verbose:
                    print(f"📝 Empty:  {fname}")
                    print(f"   Key:   {key}")
            elif is_filled:
                filleds[key] = f
                if verbose:
                    print(f"✅ Filled: {fname}")
                    print(f"   Key:   {key}")
    
    if verbose:
        print(f"\n📊 Found {len(empties)} empty files and {len(filleds)} filled files")
        print(f"🔗 Looking for matching pairs...")
        print()
    
    # Find matching pairs
    pairs = []
    matched_keys = sorted(set(empties.keys()) & set(filleds.keys()))
    
    if verbose:
        print(f"✨ New method found {len(matched_keys)} matching pairs:")
    
    for i, key in enumerate(matched_keys, 1):
        pairs.append((empties[key], filleds[key]))
        if verbose:
            empty_name = os.path.basename(empties[key])
            filled_name = os.path.basename(filleds[key])
            print(f"  {i:2d}. 📝 {empty_name}")
            print(f"      ✅ {filled_name}")
            print()
    
    # Also try the old method as fallback for files that don't match the new patterns
    old_empties, old_filleds = {}, {}
    for f in files:
        fname = os.path.basename(f)
        if PAIR_EMPTY_RE.match(fname):
            key = PAIR_EMPTY_RE.sub(r"\1\2", fname).lower()
            old_empties[key] = f
        elif PAIR_FILLED_RE.match(fname):
            key = PAIR_FILLED_RE.sub(r"\1\2", fname).lower()
            old_filleds[key] = f
    
    # Add old method pairs that weren't found by new method
    existing_files = set()
    for empty, filled in pairs:
        existing_files.add(empty)
        existing_files.add(filled)
    
    old_matched_keys = sorted(set(old_empties.keys()) & set(old_filleds.keys()))
    old_pairs_added = 0
    
    for k in old_matched_keys:
        if old_empties[k] not in existing_files and old_filleds[k] not in existing_files:
            pairs.append((old_empties[k], old_filleds[k]))
            old_pairs_added += 1
            if verbose:
                empty_name = os.path.basename(old_empties[k])
                filled_name = os.path.basename(old_filleds[k])
                print(f"🔄 Fallback method found additional pair:")
                print(f"     📝 {empty_name}")
                print(f"     ✅ {filled_name}")
                print()
    
    if verbose:
        print(f"🎯 TOTAL PAIRS FOUND: {len(pairs)}")
        print(f"   - New method: {len(matched_keys)} pairs")
        print(f"   - Fallback method: {old_pairs_added} additional pairs")
        print(f"   - Total files to process: {len(pairs) * 2}")
        print("="*60)
        print()
    
    return pairs

def find_data_sheets(json_obj: Dict[str, Any]) -> List[str]:
    """Find sheets that contain actual data (not just metadata or instructions)"""
    data_sheets = []
    
    for sheet_name, sheet_data in json_obj.items():
        if not isinstance(sheet_data, dict):
            continue
            
        # Skip sheets that are clearly metadata or instructions
        if any(skip_word in sheet_name.lower() for skip_word in 
               ['instruction', 'toc', 'validation', 'info', 'confidential', '保密']):
            continue
            
        # Check if sheet has the expected structure with data
        if 'columns' in sheet_data and 'data' in sheet_data:
            data_rows = sheet_data.get('data', [])
            columns = sheet_data.get('columns', [])
            
            # Skip if too few rows or columns (likely not real data)
            if len(data_rows) < 2 or len(columns) < 3:
                continue
                
            data_sheets.append(sheet_name)
    
    return data_sheets

def learn_from_pair(empty_path: str, filled_path: str, sheet_name: str = None, verbose: bool = False) -> Dict[str, Any]:
    if verbose:
        print(f"🧠 Learning from pair:")
        print(f"   📝 Empty:  {os.path.basename(empty_path)}")
        print(f"   ✅ Filled: {os.path.basename(filled_path)}")
    
    ej, fj = load_json(empty_path), load_json(filled_path)
    
    # Auto-detect sheet names if not specified
    if sheet_name is None:
        empty_sheets = find_data_sheets(ej)
        filled_sheets = find_data_sheets(fj)
        
        # Find common sheets between empty and filled
        common_sheets = set(empty_sheets) & set(filled_sheets)
        
        if not common_sheets:
            if verbose:
                print(f"   ❌ No common data sheets found")
                print(f"      Empty sheets: {empty_sheets}")
                print(f"      Filled sheets: {filled_sheets}")
                print()
            return {"sheets": {}}
        
        sheets_to_process = list(common_sheets)
        if verbose:
            print(f"   📊 Auto-detected sheets: {sheets_to_process}")
    else:
        sheets_to_process = [sheet_name]
        if verbose:
            print(f"   📊 Using specified sheet: {sheet_name}")
    
    all_results = {"sheets": {}}
    
    for current_sheet in sheets_to_process:
        if verbose:
            print(f"   🔍 Processing sheet: '{current_sheet}'")
            
        es, fs = get_sheet(ej, current_sheet), get_sheet(fj, current_sheet)
        if not es or not fs:
            if verbose:
                print(f"      ❌ Could not find sheet '{current_sheet}' in one or both files")
            continue

        e_headers, e_hidx = detect_header_row(es)
        f_headers, f_hidx = detect_header_row(fs)
        headers = e_headers if sum(len(h) for h in e_headers) >= sum(len(h) for h in f_headers) else f_headers
        value_cols = list_value_columns(headers)

        if verbose:
            print(f"      📋 Headers detected: {len(headers)} columns")
            print(f"      🔍 Analyzing columns {value_cols[0] if value_cols else 'none'} to {value_cols[-1] if value_cols else 'none'} (skipping row labels)")

        e_cols, e_rows = es.get("columns", []), es.get("data", [])[e_hidx+1:]
        f_cols, f_rows = fs.get("columns", []), fs.get("data", [])[f_hidx+1:]

        def column_has_values(rows, cols, col_idx):
            if col_idx >= len(cols): return False
            key = cols[col_idx]
            for r in rows[:200]:
                val = str(r.get(key, "")).strip()
                if val and len(val) > 2:
                    return True
            return False

        columns_to_fill: List[str] = []
        column_positions: Dict[str, int] = {}
        header_map = defaultdict(set)
        verifications: Dict[str, Any] = {}

        if verbose:
            print(f"      🔍 Column analysis:")

        for idx in value_cols:
            raw = headers[idx] if idx < len(headers) else ""
            if not raw: 
                continue
            e_has = column_has_values(e_rows, e_cols, idx)
            f_has = column_has_values(f_rows, f_cols, idx)
            
            if (not e_has) and f_has:
                columns_to_fill.append(raw)
                column_positions[raw] = idx
                if verbose:
                    print(f"         ✨ FILLABLE: '{raw}' (pos {idx}) - empty→filled")
            elif verbose:
                status = "both filled" if e_has and f_has else ("both empty" if not e_has and not f_has else "filled→empty")
                print(f"         ⏭️  SKIP: '{raw}' (pos {idx}) - {status}")

            header_map[raw].add(raw)
            label, conf, method = verify_label(raw)
            verifications[raw] = {"label": label, "confidence": conf, "method": method}

        normalized_header_map = {raw: sorted(list(header_map[raw])) for raw in header_map.keys()}

        if verbose:
            print(f"      📝 Result: {len(columns_to_fill)} fillable columns identified")
            if columns_to_fill:
                for col in columns_to_fill:
                    v = verifications.get(col, {})
                    print(f"         • {col} → {v.get('label', '?')} (conf: {v.get('confidence', 0):.2f})")

        # Store results for this sheet
        all_results["sheets"][current_sheet] = {
            "header_map": normalized_header_map,
            "columns_to_fill": sorted(columns_to_fill),
            "column_positions": column_positions,
            "verifications": verifications
        }

    if verbose:
        total_fillable = sum(len(sheet_data.get("columns_to_fill", [])) for sheet_data in all_results["sheets"].values())
        print(f"   🎯 Total fillable columns across all sheets: {total_fillable}")
        print()

    return all_results
