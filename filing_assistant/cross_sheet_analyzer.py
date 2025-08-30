"""
Cross-Sheet Pattern Analysis Module

This module implements advanced pattern matching that analyzes ALL sheets
to find the best column candidates, overcoming the limitation of sheet-first matching.
"""

from typing import Dict, Any, List, Tuple, Optional
from .io_utils import load_json, get_sheet, detect_header_row, detect_header_row_enhanced, list_value_columns
from .verifier import verify_label
import difflib

class CrossSheetAnalyzer:
    """Analyzes patterns across multiple sheets to find optimal column matches"""
    
    def __init__(self, store: Dict[str, Any], use_enhanced_headers: bool = False):
        self.store = store
        self.use_enhanced_headers = use_enhanced_headers
        self.quality_threshold = 0.7
        
    def analyze_file(self, empty_file: str, target_sheet: str = None, threshold: float = 0.7) -> Dict[str, Any]:
        """
        Perform cross-sheet pattern analysis to find the best column candidates
        from any learned sheet pattern, not just the sheet name match.
        """
        ej = load_json(empty_file)
        
        # Get all available sheets in the target file
        available_sheets = self._find_data_sheets(ej)
        
        if target_sheet and target_sheet in available_sheets:
            sheets_to_analyze = [target_sheet]
        else:
            sheets_to_analyze = available_sheets
        
        # Analyze each sheet with cross-pattern matching
        results = {}
        best_matches = {}
        
        for sheet_name in sheets_to_analyze:
            sheet_results = self._analyze_sheet_with_cross_patterns(
                ej, sheet_name, empty_file, threshold
            )
            results[sheet_name] = sheet_results
            
            # Track best matches across sheets
            for column_match in sheet_results.get("columns", []):
                col_key = f"{sheet_name}:{column_match['position']}"
                if col_key not in best_matches or column_match["confidence"] > best_matches[col_key]["confidence"]:
                    best_matches[col_key] = column_match
                    best_matches[col_key]["source_sheet"] = sheet_name
        
        # Generate consolidated results
        consolidated = self._consolidate_cross_sheet_results(results, best_matches)
        
        return consolidated
    
    def _find_data_sheets(self, json_obj: Dict[str, Any]) -> List[str]:
        """Find sheets that contain actual data"""
        data_sheets = []
        
        for sheet_name, sheet_data in json_obj.items():
            if not isinstance(sheet_data, dict):
                continue
                
            # Skip metadata sheets
            if any(skip_word in sheet_name.lower() for skip_word in 
                   ['instruction', 'toc', 'validation', 'info', 'confidential', '保密']):
                continue
                
            # Check for data structure
            if 'columns' in sheet_data and 'data' in sheet_data:
                data_rows = sheet_data.get('data', [])
                columns = sheet_data.get('columns', [])
                
                if len(data_rows) >= 2 and len(columns) >= 3:
                    data_sheets.append(sheet_name)
        
        return data_sheets
    
    def _analyze_sheet_with_cross_patterns(self, json_obj: Dict[str, Any], sheet_name: str, 
                                          file_path: str, threshold: float) -> Dict[str, Any]:
        """Analyze a sheet against ALL learned patterns, not just same-name patterns"""
        
        sheet_data = get_sheet(json_obj, sheet_name)
        if not sheet_data:
            return {"error": "sheet not found"}
        
        # Get headers with optional enhancement
        if self.use_enhanced_headers:
            try:
                headers, hidx, enhancement_info = detect_header_row_enhanced(sheet_data, file_path)
                enhanced_used = enhancement_info.get("enhanced", False)
                enhancement_confidence = enhancement_info.get("confidence", 0.0)
            except Exception as e:
                headers, hidx = detect_header_row(sheet_data)
                enhanced_used = False
                enhancement_confidence = 0.0
                enhancement_info = {"enhanced": False, "error": str(e)}
        else:
            headers, hidx = detect_header_row(sheet_data)
            enhanced_used = False
            enhancement_confidence = 0.0
            enhancement_info = {"enhanced": False}
        
        value_cols = list_value_columns(headers)
        
        # CROSS-SHEET ANALYSIS: Check against ALL learned patterns
        all_learned_patterns = self.store.get("sheets", {})
        
        results = []
        unknowns = []
        
        for idx in value_cols:
            raw_header = headers[idx] if idx < len(headers) else ""
            if not raw_header:
                continue
            
            # Find best match across ALL learned sheets
            best_match = self._find_best_cross_sheet_match(raw_header, all_learned_patterns)
            
            # Calculate final confidence with enhancement bonus
            final_confidence = best_match["confidence"]
            if enhanced_used and enhancement_confidence > 0.8:
                final_confidence += 0.15
                best_match["decision_factors"].append("ai_enhanced_header")
            
            final_confidence = min(final_confidence, 1.0)
            
            # Decision logic
            is_fillable = (best_match["is_learned_fillable"] or 
                          final_confidence >= threshold)
            
            column_result = {
                "position": idx,
                "header": raw_header,
                "label": best_match["label"],
                "confidence": final_confidence,
                "verified_by": best_match["method"],
                "decision": "fill" if is_fillable else "unknown",
                "learned_fillable": best_match["is_learned_fillable"],
                "decision_factors": best_match["decision_factors"],
                "enhanced_header": enhanced_used,
                "source_patterns": best_match["source_patterns"],
                "cross_sheet_analysis": True
            }
            
            if is_fillable:
                results.append(column_result)
            else:
                unknowns.append(column_result)
        
        return {
            "columns": results,
            "unknowns": unknowns,
            "total_headers": len(headers),
            "analyzed_columns": len(value_cols),
            "header_enhancement": enhancement_info,
            "cross_sheet_patterns_used": len(all_learned_patterns)
        }
    
    def _find_best_cross_sheet_match(self, header: str, all_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Find the best pattern match across all learned sheets"""
        
        candidates = []
        
        # Analyze against each learned sheet
        for learned_sheet_name, learned_data in all_patterns.items():
            learned_fillable = set(learned_data.get("columns_to_fill", []))
            verifications = learned_data.get("verifications", {})
            enhanced_patterns = learned_data.get("enhanced_patterns", {})
            
            # Direct header match
            if header in learned_fillable:
                verification = verifications.get(header, {})
                candidates.append({
                    "confidence": 0.95,
                    "match_type": "direct_learned_fillable",
                    "source_sheet": learned_sheet_name,
                    "label": verification.get("label", "unknown"),
                    "method": verification.get("method", "learned"),
                    "is_learned_fillable": True,
                    "decision_factors": ["direct_match", "learned_fillable"]
                })
            
            # Verification match
            if header in verifications:
                verification = verifications[header]
                base_conf = float(verification.get("confidence", 0.0))
                candidates.append({
                    "confidence": base_conf * 0.85,  # Slight discount for cross-sheet
                    "match_type": "verification_match",
                    "source_sheet": learned_sheet_name,
                    "label": verification.get("label", "unknown"),
                    "method": verification.get("method", "learned"),
                    "is_learned_fillable": header in learned_fillable,
                    "decision_factors": ["verification_match"]
                })
            
            # Enhanced pattern match
            if header in enhanced_patterns:
                pattern_data = enhanced_patterns[header]
                candidates.append({
                    "confidence": 0.75,
                    "match_type": "enhanced_pattern_match",
                    "source_sheet": learned_sheet_name,
                    "label": pattern_data.get("label", "unknown"),
                    "method": "enhanced_pattern",
                    "is_learned_fillable": header in learned_fillable,
                    "decision_factors": ["enhanced_pattern"]
                })
            
            # Semantic similarity matching
            semantic_matches = self._find_semantic_matches(header, verifications)
            for match in semantic_matches:
                match["source_sheet"] = learned_sheet_name
                match["match_type"] = "semantic_similarity"
                candidates.append(match)
        
        # Select best candidate
        if candidates:
            best = max(candidates, key=lambda x: x["confidence"])
            
            # Aggregate source information
            source_sheets = list(set(c["source_sheet"] for c in candidates))
            
            return {
                "confidence": best["confidence"],
                "label": best["label"],
                "method": f"{best['method']}+cross-sheet",
                "is_learned_fillable": best["is_learned_fillable"],
                "decision_factors": best["decision_factors"] + ["cross_sheet_analysis"],
                "source_patterns": source_sheets,
                "best_match_type": best["match_type"]
            }
        else:
            # Fallback to live verification
            label, conf, method = verify_label(header)
            return {
                "confidence": conf,
                "label": label,
                "method": method,
                "is_learned_fillable": False,
                "decision_factors": ["live_verification"],
                "source_patterns": [],
                "best_match_type": "fallback"
            }
    
    def _find_semantic_matches(self, header: str, verifications: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find semantically similar headers using string similarity"""
        matches = []
        
        for verified_header, verification in verifications.items():
            # Calculate similarity
            similarity = difflib.SequenceMatcher(None, header.lower(), verified_header.lower()).ratio()
            
            if similarity > 0.7:  # High similarity threshold
                confidence = similarity * float(verification.get("confidence", 0.0)) * 0.7
                matches.append({
                    "confidence": confidence,
                    "label": verification.get("label", "unknown"),
                    "method": f"semantic_similarity_{similarity:.2f}",
                    "is_learned_fillable": False,  # Conservative
                    "decision_factors": [f"semantic_match_{similarity:.2f}"],
                    "similarity": similarity
                })
        
        return matches
    
    def _consolidate_cross_sheet_results(self, all_results: Dict[str, Any], 
                                       best_matches: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate results from cross-sheet analysis"""
        
        # Find the sheet with the best overall results
        best_sheet = None
        best_sheet_score = 0
        
        for sheet_name, sheet_results in all_results.items():
            if "error" in sheet_results:
                continue
                
            # Calculate sheet score based on fillable columns and confidence
            columns = sheet_results.get("columns", [])
            if columns:
                avg_confidence = sum(c["confidence"] for c in columns) / len(columns)
                sheet_score = len(columns) * avg_confidence
                
                if sheet_score > best_sheet_score:
                    best_sheet_score = sheet_score
                    best_sheet = sheet_name
        
        # Primary results from best sheet
        primary_results = all_results.get(best_sheet, {}) if best_sheet else {}
        
        # Add cross-sheet analysis summary
        total_patterns_analyzed = sum(
            sheet_data.get("cross_sheet_patterns_used", 0) 
            for sheet_data in all_results.values() 
            if isinstance(sheet_data, dict) and "cross_sheet_patterns_used" in sheet_data
        )
        
        total_fillable = sum(
            len(sheet_data.get("columns", [])) 
            for sheet_data in all_results.values() 
            if isinstance(sheet_data, dict) and "columns" in sheet_data
        )
        
        total_unknown = sum(
            len(sheet_data.get("unknowns", [])) 
            for sheet_data in all_results.values() 
            if isinstance(sheet_data, dict) and "unknowns" in sheet_data
        )
        
        # Enhanced summary with cross-sheet information
        summary = {
            "sheets_processed": len([s for s in all_results.values() if isinstance(s, dict) and "error" not in s]),
            "total_fillable_columns": total_fillable,
            "total_unknown_columns": total_unknown,
            "cross_sheet_analysis": True,
            "patterns_analyzed": total_patterns_analyzed,
            "best_sheet": best_sheet,
            "best_sheet_score": best_sheet_score,
            "enhancement_used": self.use_enhanced_headers,
            "quality_threshold": self.quality_threshold
        }
        
        return {
            "primary_sheet": best_sheet,
            "primary_results": primary_results,
            "all_sheet_results": all_results,
            "summary": summary,
            "cross_sheet_analysis": True
        }


def cross_sheet_identify_required_columns(empty_file: str, store: Dict[str, Any], 
                                        sheet_name: str = None, threshold: float = 0.7, 
                                        use_enhanced_headers: bool = False) -> Dict[str, Any]:
    """
    Enhanced identification using cross-sheet pattern analysis
    
    This function overcomes the limitation of sheet-first matching by analyzing
    patterns from ALL learned sheets to find the best column candidates.
    """
    analyzer = CrossSheetAnalyzer(store, use_enhanced_headers)
    return analyzer.analyze_file(empty_file, sheet_name, threshold)
