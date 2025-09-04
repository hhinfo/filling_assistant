from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
import json, re, os, sys
from .schema import normalize

# Import enhanced header detector with fallback
try:
    from .enhanced_header_detector import EnhancedHeaderDetector
    ENHANCED_DETECTION_AVAILABLE = True
except ImportError:
    ENHANCED_DETECTION_AVAILABLE = False
    EnhancedHeaderDetector = None

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def detect_header_row(sheet_obj: Dict[str, Any]) -> Tuple[List[str], int]:
    """Return (headers, header_row_index_in_data).
    For structured JSON files, use the 'columns' field directly as headers."""
    cols = sheet_obj.get("columns", [])
    
    # For structured JSON with explicit columns field, use it directly
    if cols:
        headers = [normalize(str(col)) for col in cols]
        return headers, -1  # -1 indicates headers are from columns field, not data rows
    
    # Fallback: try to detect headers from data rows (for legacy formats)
    rows = sheet_obj.get("data", [])
    if not rows:
        return [], -1
        
    score_row = []
    for idx, row in enumerate(rows):
        values = [str(row.get(c, "")) for c in cols] if cols else list(row.values())
        non_empty = [v for v in values if v.strip()]
        richness = sum(int(bool(re.search(r"[()*/-]|\s", v))) for v in non_empty)
        score = (len(non_empty), richness)
        score_row.append((score, idx, non_empty))
    
    score_row.sort(reverse=True)
    if not score_row:
        return [], -1
    _, best_idx, _ = score_row[0]
    
    if cols:
        headers = [normalize(str(rows[best_idx].get(c, ""))) for c in cols]
    else:
        headers = [normalize(str(v)) for v in rows[best_idx].values()]
    return headers, best_idx

def detect_header_row_enhanced(sheet_obj: Dict[str, Any], file_name: str = "unknown") -> Tuple[List[str], int, Dict[str, Any]]:
    """Enhanced header detection using the 5-strategy system with OpenAI validation.
    Returns (headers, header_row_index, enhancement_info)"""
    
    # First get standard headers as fallback
    standard_headers, standard_idx = detect_header_row(sheet_obj)
    
    # Try enhanced detection if available
    if ENHANCED_DETECTION_AVAILABLE:
        try:
            detector = EnhancedHeaderDetector()
            result = detector.detect_headers_enhanced(sheet_obj, file_name)
            
            final_mapping = result.get('final_mapping', {})
            confidence = result.get('confidence', 0.0)
            
            # Use enhanced headers if confidence is high enough
            if final_mapping and confidence > 0.6:
                # Convert enhanced mapping back to header list
                enhanced_headers = []
                cols = sheet_obj.get("columns", [])
                
                for i, col_key in enumerate(cols):
                    if f"col_{i}" in final_mapping:
                        enhanced_header = final_mapping[f"col_{i}"]
                        enhanced_headers.append(normalize(enhanced_header))
                    elif col_key in final_mapping:
                        enhanced_header = final_mapping[col_key]
                        enhanced_headers.append(normalize(enhanced_header))
                    else:
                        # Fall back to standard header
                        standard_header = standard_headers[i] if i < len(standard_headers) else f"col_{i}"
                        enhanced_headers.append(standard_header)
                
                enhancement_info = {
                    "enhanced": True,
                    "confidence": confidence,
                    "ai_validation": result.get('openai_validation', {}),
                    "strategy_results": result.get('strategy_results', {}),
                    "original_headers": standard_headers
                }
                
                return enhanced_headers, standard_idx, enhancement_info
        
        except Exception as e:
            # Fall back to standard detection on any error
            print(f"Warning: Enhanced header detection failed: {e}")
    
    # Return standard headers with enhancement info
    enhancement_info = {
        "enhanced": False,
        "reason": "Enhanced detection not available or failed",
        "original_headers": standard_headers
    }
    
    return standard_headers, standard_idx, enhancement_info

def get_sheet(json_obj: Dict[str, Any], sheet_name: str) -> Optional[Dict[str, Any]]:
    return json_obj.get(sheet_name)

def list_value_columns(headers: List[str]) -> List[int]:
    # Heuristic: in these JSONs, col_0 is a row label, real values start from col_1
    return list(range(1, len(headers)))
