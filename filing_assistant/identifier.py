from __future__ import annotations
from typing import Dict, Any, List
from .io_utils import load_json, get_sheet, detect_header_row, detect_header_row_enhanced, list_value_columns
from .verifier import verify_label
from .cross_sheet_analyzer import cross_sheet_identify_required_columns

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

def enhanced_identify_required_columns(empty_file: str, store: Dict[str, Any], sheet_name: str = None, threshold: float = 0.7, use_enhanced_headers: bool = False) -> Dict[str, Any]:
    """Enhanced identification using learned patterns and improved scoring with optional enhanced header detection"""
    ej = load_json(empty_file)
    
    # Auto-detect sheet names if not specified
    if sheet_name is None:
        available_sheets = find_data_sheets(ej)
        learned_sheets = list(store.get("sheets", {}).keys())
        
        # Find sheets that exist in both the file and the learned patterns
        sheets_to_process = [sheet for sheet in available_sheets if sheet in learned_sheets]
        
        if not sheets_to_process:
            return {
                "error": "No matching sheets found",
                "available_sheets": available_sheets,
                "learned_sheets": learned_sheets
            }
    else:
        sheets_to_process = [sheet_name]
    
    all_results = {"sheets": {}}
    total_fillable = 0
    total_unknown = 0
    
    for current_sheet in sheets_to_process:
        es = get_sheet(ej, current_sheet)
        if not es:
            all_results["sheets"][current_sheet] = {
                "error": "sheet not found in file"
            }
            continue

        # Use enhanced header detection if requested
        if use_enhanced_headers:
            try:
                headers, hidx, enhancement_info = detect_header_row_enhanced(es, empty_file)
                enhanced_used = enhancement_info.get("enhanced", False)
                enhancement_confidence = enhancement_info.get("confidence", 0.0)
            except Exception as e:
                print(f"Warning: Enhanced header detection failed, falling back to standard: {e}")
                headers, hidx = detect_header_row(es)
                enhanced_used = False
                enhancement_confidence = 0.0
                enhancement_info = {"enhanced": False, "error": str(e)}
        else:
            headers, hidx = detect_header_row(es)
            enhanced_used = False
            enhancement_confidence = 0.0
            enhancement_info = {"enhanced": False, "reason": "not requested"}

        value_cols = list_value_columns(headers)

        learned = store.get("sheets", {}).get(current_sheet, {})
        learned_raws = set(learned.get("columns_to_fill", []))
        enhanced_patterns = learned.get("enhanced_patterns", {})

        results, unknowns = [], []
        sheet_fillable_count = 0

        for idx in value_cols:
            raw = headers[idx] if idx < len(headers) else ""
            if not raw: 
                continue
            
            # Enhanced scoring using learned patterns
            confidence_score = 0.0
            decision_factors = []
            
            # Factor 1: Was this column learned as fillable? (highest weight)
            if raw in learned_raws:
                confidence_score += 0.7
                decision_factors.append("learned_fillable")
            
            # Factor 2: Get verification confidence
            learned_verification = learned.get("verifications", {}).get(raw, {})
            if learned_verification:
                base_conf = float(learned_verification.get("confidence", 0.0))
                confidence_score += base_conf * 0.3
                method = learned_verification.get("method", "learned")
                
                # Factor 3: Enhanced pattern analysis boost
                if "pattern_analysis" in learned_verification:
                    pa = learned_verification["pattern_analysis"]
                    pattern_conf = pa.get("confidence", 0.0)
                    confidence_score += pattern_conf * 0.2
                    
                    if pa.get("reasons"):
                        decision_factors.extend(pa["reasons"][:2])
            else:
                # Fall back to live verification
                label, conf, method = verify_label(raw)
                confidence_score += conf * 0.3
            
            # Factor 4: Enhanced pattern matching
            if raw in enhanced_patterns:
                pattern_data = enhanced_patterns[raw]
                if pattern_data.get("value_types"):
                    confidence_score += 0.1
                    decision_factors.append("has_value_patterns")
            
            # Factor 5: Enhanced header detection boost
            if enhanced_used and enhancement_confidence > 0.8:
                confidence_score += 0.15
                decision_factors.append("ai_enhanced_header")
            
            # Final confidence and decision
            final_confidence = min(confidence_score, 1.0)
            
            # Enhanced threshold logic
            enhanced_threshold = threshold * 0.8  # Lower threshold for better recall
            is_fillable = (raw in learned_raws) or (final_confidence >= enhanced_threshold)
            
            if is_fillable:
                label = learned_verification.get("label", "unknown") if learned_verification else verify_label(raw)[0]
                results.append({
                    "position": idx,
                    "header": raw,
                    "label": label,
                    "confidence": final_confidence,
                    "verified_by": method,
                    "decision": "fill",
                    "learned_fillable": raw in learned_raws,
                    "decision_factors": decision_factors,
                    "enhanced_header": enhanced_used
                })
                sheet_fillable_count += 1
            else:
                label = learned_verification.get("label", "unknown") if learned_verification else verify_label(raw)[0]
                unknowns.append({
                    "position": idx,
                    "header": raw,
                    "label": label,
                    "confidence": final_confidence,
                    "verified_by": method,
                    "decision": "unknown",
                    "learned_fillable": False,
                    "decision_factors": decision_factors,
                    "enhanced_header": enhanced_used
                })

        all_results["sheets"][current_sheet] = {
            "columns": results,
            "unknowns": unknowns,
            "total_headers": len(headers),
            "analyzed_columns": len(value_cols),
            "header_enhancement": enhancement_info
        }
        total_fillable += sheet_fillable_count
        total_unknown += len(unknowns)

    # Add summary
    all_results["summary"] = {
        "total_fillable_columns": total_fillable,
        "total_unknown_columns": total_unknown,
        "sheets_processed": len(sheets_to_process),
        "enhancement_used": True,
        "enhanced_headers_used": use_enhanced_headers
    }
    
    return all_results

def identify_required_columns(empty_file: str, store: Dict[str, Any], sheet_name: str = None, threshold: float = 0.7) -> Dict[str, Any]:
    """
    Main identification function - uses cross-sheet pattern analysis with enhanced headers
    
    This function first attempts cross-sheet analysis for better pattern matching,
    then falls back to traditional sheet-first matching if needed.
    """
    # Try cross-sheet analysis first for better pattern matching
    try:
        cross_sheet_results = cross_sheet_identify_required_columns(
            empty_file, store, sheet_name, threshold, use_enhanced_headers=True
        )
        
        # Check if cross-sheet analysis found good results
        primary_results = cross_sheet_results.get("primary_results", {})
        if primary_results and "columns" in primary_results:
            columns = primary_results["columns"]
            if columns:
                avg_confidence = sum(c["confidence"] for c in columns) / len(columns)
                # If high quality results, use cross-sheet analysis
                if avg_confidence >= threshold * 0.8:
                    return cross_sheet_results
        
        # Fallback to enhanced sheet-first matching
        print("⚠️ Cross-sheet analysis yielded low confidence, falling back to sheet-first matching")
        return enhanced_identify_required_columns(empty_file, store, sheet_name, threshold, use_enhanced_headers=True)
        
    except Exception as e:
        print(f"⚠️ Cross-sheet analysis failed: {e}, falling back to enhanced identification")
        return enhanced_identify_required_columns(empty_file, store, sheet_name, threshold, use_enhanced_headers=True)

def basic_identify_required_columns(empty_file: str, store: Dict[str, Any], sheet_name: str = None, threshold: float = 0.7) -> Dict[str, Any]:
    """Original identification method"""
    ej = load_json(empty_file)
    
    # Auto-detect sheet names if not specified
    if sheet_name is None:
        available_sheets = find_data_sheets(ej)
        learned_sheets = list(store.get("sheets", {}).keys())
        
        # Find sheets that exist in both the file and the learned patterns
        sheets_to_process = [sheet for sheet in available_sheets if sheet in learned_sheets]
        
        if not sheets_to_process:
            return {
                "error": "No matching sheets found",
                "available_sheets": available_sheets,
                "learned_sheets": learned_sheets
            }
    else:
        sheets_to_process = [sheet_name]
    
    all_results = {"sheets": {}}
    
    # Auto-detect sheet names if not specified
    if sheet_name is None:
        available_sheets = find_data_sheets(ej)
        learned_sheets = list(store.get("sheets", {}).keys())
        
        # Find sheets that exist in both the file and the learned patterns
        sheets_to_process = [sheet for sheet in available_sheets if sheet in learned_sheets]
        
        if not sheets_to_process:
            return {
                "error": "No matching sheets found",
                "available_sheets": available_sheets,
                "learned_sheets": learned_sheets
            }
    else:
        sheets_to_process = [sheet_name]
    
    all_results = {"sheets": {}}
    
    for current_sheet in sheets_to_process:
        es = get_sheet(ej, current_sheet)
        if not es:
            all_results["sheets"][current_sheet] = {
                "error": "sheet not found in file"
            }
            continue

        headers, hidx = detect_header_row(es)
        value_cols = list_value_columns(headers)

        learned = store.get("sheets", {}).get(current_sheet, {})
        learned_raws = set(learned.get("columns_to_fill", []))

        results, unknowns = [], []

        for idx in value_cols:
            raw = headers[idx] if idx < len(headers) else ""
            if not raw: 
                continue
            
            # Check if this column was learned as fillable
            candidate = raw in learned_raws
            
            # Get verification for the column
            learned_verification = learned.get("verifications", {}).get(raw, {})
            if learned_verification:
                # Use learned verification if available
                label = learned_verification.get("label", "unknown")
                conf = float(learned_verification.get("confidence", 0.0))
                method = learned_verification.get("method", "learned")
            else:
                # Fall back to live verification
                label, conf, method = verify_label(raw)
            
            if candidate or conf >= threshold:
                results.append({
                    "position": idx,
                    "header": raw,
                    "label": label,
                    "confidence": conf,
                    "verified_by": method,
                    "decision": "fill",
                    "learned_fillable": candidate
                })
            else:
                unknowns.append({
                    "position": idx,
                    "header": raw,
                    "label": label,
                    "confidence": conf,
                    "verified_by": method,
                    "decision": "unknown",
                    "learned_fillable": candidate
                })

        all_results["sheets"][current_sheet] = {
            "columns": results,
            "unknowns": unknowns,
            "total_headers": len(headers),
            "analyzed_columns": len(value_cols)
        }
    
    # Add summary
    total_fillable = sum(len(sheet_data.get("columns", [])) for sheet_data in all_results["sheets"].values() if "columns" in sheet_data)
    total_unknown = sum(len(sheet_data.get("unknowns", [])) for sheet_data in all_results["sheets"].values() if "unknowns" in sheet_data)
    
    all_results["summary"] = {
        "sheets_processed": len(sheets_to_process),
        "total_fillable_columns": total_fillable,
        "total_unknown_columns": total_unknown
    }

    return all_results
