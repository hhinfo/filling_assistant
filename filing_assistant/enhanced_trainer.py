"""
Enhanced training module with improved accuracy for fillable column identification
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Set
import os, re, glob
from collections import defaultdict, Counter
import json
from .io_utils import load_json, get_sheet, detect_header_row, list_value_columns
from .schema import normalize
from .verifier import verify_label
import statistics

# Import enhanced header detector with fallback
try:
    from .enhanced_header_detector import EnhancedHeaderDetector
    ENHANCED_HEADERS_AVAILABLE = True
except ImportError:
    print("⚠️ Enhanced header detector not available - falling back to basic headers")
    ENHANCED_HEADERS_AVAILABLE = False
    EnhancedHeaderDetector = None

def analyze_column_filling_patterns(empty_rows: List[Dict], filled_rows: List[Dict], 
                                  column_key: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Enhanced analysis of how a column gets filled between empty and filled versions
    """
    empty_values = []
    filled_values = []
    
    # Extract values from both versions
    for row in empty_rows[:200]:  # Sample first 200 rows for performance
        val = str(row.get(column_key, "")).strip()
        empty_values.append(val)
    
    for row in filled_rows[:200]:
        val = str(row.get(column_key, "")).strip()
        filled_values.append(val)
    
    # Count non-empty values
    empty_non_empty = sum(1 for v in empty_values if v and v not in ['0', ''])
    filled_non_empty = sum(1 for v in filled_values if v and v not in ['0', ''])
    
    # Calculate filling ratio
    total_rows = min(len(empty_values), len(filled_values))
    if total_rows == 0:
        return {"fillable": False, "confidence": 0.0, "reason": "no_data"}
    
    empty_ratio = empty_non_empty / total_rows
    filled_ratio = filled_non_empty / total_rows
    
    # Enhanced fillability scoring
    fillability_score = 0.0
    reasons = []
    
    # 1. Classic empty→filled pattern (highest confidence)
    if empty_ratio <= 0.1 and filled_ratio >= 0.3:
        fillability_score += 0.8
        reasons.append("empty_to_filled")
    
    # 2. Partial filling pattern (medium confidence)
    elif empty_ratio < filled_ratio and (filled_ratio - empty_ratio) >= 0.2:
        fillability_score += 0.6
        reasons.append("increased_filling")
    
    # 3. Value pattern changes (low-medium confidence)
    if len(filled_values) > 0 and len(empty_values) > 0:
        empty_unique = set(v for v in empty_values if v and v not in ['0', ''])
        filled_unique = set(v for v in filled_values if v and v not in ['0', ''])
        
        if len(filled_unique) > len(empty_unique) * 1.5:
            fillability_score += 0.3
            reasons.append("value_diversity_increase")
    
    # 4. Numeric vs text pattern analysis
    filled_non_empty_values = [v for v in filled_values if v and v not in ['0', '']]
    if filled_non_empty_values:
        # Check for numeric patterns
        numeric_count = sum(1 for v in filled_non_empty_values 
                          if re.match(r'^[\d.,]+$', v.replace(' ', '')))
        numeric_ratio = numeric_count / len(filled_non_empty_values)
        
        if numeric_ratio > 0.7:  # Mostly numeric
            fillability_score += 0.2
            reasons.append("numeric_pattern")
        
        # Check for common fillable value patterns
        common_patterns = [
            r'\d+',  # numbers
            r'[\d.,]+',  # prices/amounts
            r'[A-Z]{2,4}',  # codes
            r'\d{4}-\d{2}-\d{2}',  # dates
            r'[a-z]+@[a-z]+\.[a-z]+',  # emails
        ]
        
        pattern_matches = 0
        for pattern in common_patterns:
            if sum(1 for v in filled_non_empty_values if re.search(pattern, v)):
                pattern_matches += 1
        
        if pattern_matches >= 2:
            fillability_score += 0.1
            reasons.append("structured_pattern")
    
    # Final confidence calculation
    confidence = min(fillability_score, 1.0)
    is_fillable = confidence >= 0.3  # Lowered threshold for better recall
    
    result = {
        "fillable": is_fillable,
        "confidence": confidence,
        "empty_ratio": empty_ratio,
        "filled_ratio": filled_ratio,
        "empty_count": empty_non_empty,
        "filled_count": filled_non_empty,
        "total_rows": total_rows,
        "reasons": reasons,
        "filled_sample_values": filled_non_empty_values[:10] if filled_non_empty_values else []
    }
    
    if verbose:
        status = "FILLABLE" if is_fillable else "SKIP"
        print(f"         🔍 {status}: conf={confidence:.2f}, empty={empty_ratio:.2f}, filled={filled_ratio:.2f}, reasons={reasons}")
    
    return result

def learn_value_patterns(column_values: List[str]) -> Dict[str, Any]:
    """
    Learn patterns from actual filled values to improve future identification
    """
    if not column_values:
        return {}
    
    patterns = {
        "value_types": [],
        "common_prefixes": [],
        "common_suffixes": [],
        "length_stats": {},
        "regex_patterns": []
    }
    
    # Analyze value types
    numeric_count = sum(1 for v in column_values if re.match(r'^[\d.,\-+]+$', v.strip()))
    alpha_count = sum(1 for v in column_values if re.match(r'^[a-zA-Z\s]+$', v.strip()))
    mixed_count = len(column_values) - numeric_count - alpha_count
    
    total = len(column_values)
    if numeric_count / total > 0.7:
        patterns["value_types"].append("numeric")
    if alpha_count / total > 0.7:
        patterns["value_types"].append("alphabetic")
    if mixed_count / total > 0.5:
        patterns["value_types"].append("mixed")
    
    # Length statistics
    lengths = [len(v) for v in column_values]
    if lengths:
        patterns["length_stats"] = {
            "min": min(lengths),
            "max": max(lengths),
            "avg": statistics.mean(lengths),
            "median": statistics.median(lengths)
        }
    
    # Common patterns
    if len(column_values) >= 3:
        # Prefixes (first 2-3 chars)
        prefixes = [v[:2] for v in column_values if len(v) >= 2]
        prefix_counts = Counter(prefixes)
        patterns["common_prefixes"] = [p for p, c in prefix_counts.most_common(3) if c >= 2]
        
        # Suffixes (last 2-3 chars)
        suffixes = [v[-2:] for v in column_values if len(v) >= 2]
        suffix_counts = Counter(suffixes)
        patterns["common_suffixes"] = [s for s, c in suffix_counts.most_common(3) if c >= 2]
    
    return patterns

def enhanced_learn_from_pair(empty_file, filled_file, target_sheet=None, verbose=False, use_enhanced_headers=True):
    """
    AI-Enhanced learning - always uses OpenAI-powered header detection for business intelligence
    """
    if not ENHANCED_HEADERS_AVAILABLE:
        raise ValueError("OpenAI integration required for AI-enhanced Filing Assistant. Please install openai and set OPENAI_API_KEY.")
    
    if verbose:
        print(f"🧠 AI-Enhanced learning from pair:")
        print(f"   📝 Empty:  {os.path.basename(empty_file)}")
        print(f"   ✅ Filled: {os.path.basename(filled_file)}")
        print(f"   🤖 OpenAI business header detection: ENABLED")
    
    # Always initialize enhanced header detector
    try:
        header_detector = EnhancedHeaderDetector()
        if verbose:
            print(f"   🤖 OpenAI header detector initialized")
    except Exception as e:
        if verbose:
            print(f"   ❌ Could not initialize OpenAI header detector: {e}")
        raise ValueError(f"Failed to initialize OpenAI header detector: {e}")
    
    ej, fj = load_json(empty_file), load_json(filled_file)
    
    # Auto-detect sheet names if not specified
    from .trainer import find_data_sheets
    if target_sheet is None:
        empty_sheets = find_data_sheets(ej)
        filled_sheets = find_data_sheets(fj)
        common_sheets = set(empty_sheets) & set(filled_sheets)
        
        if not common_sheets:
            if verbose:
                print(f"   ❌ No common data sheets found")
            return {"sheets": {}}
        
        sheets_to_process = list(common_sheets)
        if verbose:
            print(f"   📊 Auto-detected sheets: {sheets_to_process}")
    else:
        sheets_to_process = [target_sheet]
    
    all_results = {"sheets": {}}
    
    for current_sheet in sheets_to_process:
        if verbose:
            print(f"   🔍 Enhanced processing sheet: '{current_sheet}'")
            
        es, fs = get_sheet(ej, current_sheet), get_sheet(fj, current_sheet)
        if not es or not fs:
            if verbose:
                print(f"      ❌ Could not find sheet '{current_sheet}' in one or both files")
            continue

        e_headers, e_hidx = detect_header_row(es)
        f_headers, f_hidx = detect_header_row(fs)
        headers = e_headers if sum(len(h) for h in e_headers) >= sum(len(h) for h in f_headers) else f_headers
        
        # Always apply enhanced header detection with OpenAI
        enhanced_headers_used = False
        try:
            # Use the filled file for better header detection (more complete data)
            enhanced_result = header_detector.detect_headers_enhanced(fs, filled_file, current_sheet)
            if enhanced_result and isinstance(enhanced_result, tuple) and len(enhanced_result) >= 2:
                enhanced_headers, confidence = enhanced_result[:2]
                if enhanced_headers and confidence > 0.7:  # Require high confidence
                    # Update headers with enhanced headers
                    for idx, enhanced_header in enhanced_headers.items():
                        if idx < len(headers):
                            headers[idx] = enhanced_header
                    enhanced_headers_used = True
                    if verbose:
                        print(f"      🤖 OpenAI business headers applied: {len(enhanced_headers)} headers detected (conf: {confidence:.1%})")
                else:
                    if verbose:
                        print(f"      📊 OpenAI headers available but low confidence ({confidence:.1%}), using basic headers")
            else:
                if verbose:
                    print(f"      📊 OpenAI header detection failed, using basic headers")
        except Exception as e:
            if verbose:
                print(f"      ⚠️ OpenAI header detection error: {e}")
            # Don't fail the whole process for header detection errors
        
        value_cols = list_value_columns(headers)

        if verbose:
            header_type = "🤖 OpenAI business headers" if enhanced_headers_used else "📊 Fallback basic headers"
            print(f"      📋 {header_type} detected: {len(headers)} columns")
            print(f"      🔍 AI-Enhanced analyzing {len(value_cols)} value columns")

        e_cols, e_rows = es.get("columns", []), es.get("data", [])[e_hidx+1:]
        f_cols, f_rows = fs.get("columns", []), fs.get("data", [])[f_hidx+1:]

        columns_to_fill: List[str] = []
        column_positions: Dict[str, int] = {}
        header_map = defaultdict(set)
        verifications: Dict[str, Any] = {}
        enhanced_patterns: Dict[str, Any] = {}

        if verbose:
            print(f"      🔍 Enhanced column analysis:")

        # Enhanced column analysis
        for idx in value_cols:
            raw = headers[idx] if idx < len(headers) else ""
            if not raw: 
                continue
            
            # Get column key for data access
            column_key = e_cols[idx] if idx < len(e_cols) else f"col_{idx}"
            
            # Enhanced pattern analysis
            pattern_analysis = analyze_column_filling_patterns(
                e_rows, f_rows, column_key, verbose=verbose
            )
            
            if pattern_analysis["fillable"]:
                columns_to_fill.append(raw)
                column_positions[raw] = idx
                
                # Learn value patterns from filled data
                filled_values = pattern_analysis.get("filled_sample_values", [])
                if filled_values:
                    enhanced_patterns[raw] = learn_value_patterns(filled_values)
                
                if verbose:
                    conf = pattern_analysis["confidence"]
                    reasons = ", ".join(pattern_analysis["reasons"])
                    print(f"         ✨ FILLABLE: '{raw}' (pos {idx}) conf={conf:.2f} [{reasons}]")

            header_map[raw].add(raw)
            
            # Enhanced label verification with pattern context
            label, conf, method = verify_label(raw)
            
            # Boost confidence if we have strong patterns
            if raw in enhanced_patterns:
                pattern_boost = 0.1 if enhanced_patterns[raw].get("value_types") else 0.0
                conf = min(conf + pattern_boost, 1.0)
                method = f"{method}+pattern"
            
            verifications[raw] = {
                "label": label, 
                "confidence": conf, 
                "method": method,
                "pattern_analysis": pattern_analysis
            }

        normalized_header_map = {raw: sorted(list(header_map[raw])) for raw in header_map.keys()}

        if verbose:
            print(f"      📝 Enhanced result: {len(columns_to_fill)} fillable columns identified")
            if columns_to_fill:
                for col in columns_to_fill:
                    v = verifications.get(col, {})
                    print(f"         • {col} → {v.get('label', '?')} (conf: {v.get('confidence', 0):.2f})")

        # Store enhanced results for this sheet
        all_results["sheets"][current_sheet] = {
            "header_map": normalized_header_map,
            "columns_to_fill": sorted(columns_to_fill),
            "column_positions": column_positions,
            "verifications": verifications,
            "enhanced_patterns": enhanced_patterns,  # Store learned patterns
            "enhanced_headers_used": enhanced_headers_used,  # Track if enhanced headers were used
            "header_detection_method": "enhanced" if enhanced_headers_used else "basic"
        }

    if verbose:
        total_fillable = sum(len(sheet_data.get("columns_to_fill", [])) for sheet_data in all_results["sheets"].values())
        print(f"   🎯 Enhanced total fillable columns: {total_fillable}")
        print()

    return all_results

def enhanced_merge_patterns(store1: Dict[str, Any], store2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced pattern merging that combines value patterns and improves confidence scores
    """
    from .store import merge_patterns
    
    # Start with standard merge
    merged = merge_patterns(store1, store2)
    
    # Enhance with pattern data
    for sheet_name, sheet_data in store2.get("sheets", {}).items():
        if sheet_name in merged.get("sheets", {}):
            # Merge enhanced patterns
            enhanced_patterns = sheet_data.get("enhanced_patterns", {})
            if enhanced_patterns:
                if "enhanced_patterns" not in merged["sheets"][sheet_name]:
                    merged["sheets"][sheet_name]["enhanced_patterns"] = {}
                
                for col, patterns in enhanced_patterns.items():
                    if col in merged["sheets"][sheet_name]["enhanced_patterns"]:
                        # Merge pattern data (e.g., combine value samples)
                        existing = merged["sheets"][sheet_name]["enhanced_patterns"][col]
                        # Add logic to merge patterns intelligently
                        merged["sheets"][sheet_name]["enhanced_patterns"][col] = patterns
                    else:
                        merged["sheets"][sheet_name]["enhanced_patterns"][col] = patterns
    
    return merged
