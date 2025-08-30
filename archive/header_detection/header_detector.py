#!/usr/bin/env python3
"""
Advanced Header Detection for JSON Files with Generic Column Names

This module provides multiple strategies to automatically identify real business headers
buried in data rows when JSON files have generic column names like col_0, col_1, etc.
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any
from collections import Counter
import statistics

class HeaderDetector:
    """Intelligent header detection for messy JSON data files."""
    
    def __init__(self):
        # Business domain keywords that indicate header rows
        self.business_keywords = {
            'logistics': ['lane', 'service', 'port', 'origin', 'destination', 'carrier', 'freight', 'shipment', 'transport'],
            'financial': ['cost', 'price', 'rate', 'fee', 'charge', 'amount', 'total', 'minimum', 'surcharge', 'currency'],
            'measurement': ['cbm', 'volume', 'weight', 'kilos', 'pounds', 'tons', 'cubic', 'meter', 'feet'],
            'temporal': ['date', 'time', 'effective', 'expiration', 'valid', 'period', 'duration'],
            'identifiers': ['id', 'code', 'number', 'reference', 'tracking', 'lane_id', 'item'],
            'geographic': ['country', 'region', 'zone', 'area', 'location', 'address', 'city', 'state'],
            'business': ['quote', 'bid', 'proposal', 'contract', 'agreement', 'terms', 'conditions']
        }
        
        # Patterns that indicate template/system headers
        self.template_patterns = [
            r'<<.*?>>',  # Template variables like <<axis(lane_id)>>
            r'\{\{.*?\}\}',  # Handlebars templates
            r'\$\{.*?\}',  # Variable substitutions
            r'axis\(',  # Axis function calls
            r'bid\|',  # Bid system markers
        ]
    
    def score_header_row(self, row_data: Dict[str, Any], column_count: int) -> Tuple[float, Dict[str, Any]]:
        """
        Score how likely a row is to contain headers.
        
        Returns:
            Tuple of (score, analysis_details)
        """
        analysis = {
            'non_empty_count': 0,
            'business_keyword_matches': 0,
            'template_pattern_matches': 0,
            'unique_values': 0,
            'avg_length': 0,
            'contains_underscores': 0,
            'all_caps_ratio': 0,
            'sample_values': []
        }
        
        values = []
        for i in range(column_count):
            val = str(row_data.get(f'col_{i}', '')).strip()
            if val and val.lower() != 'nan':
                values.append(val)
                analysis['non_empty_count'] += 1
                
                # Collect sample values
                if len(analysis['sample_values']) < 10:
                    analysis['sample_values'].append(f'col_{i}: "{val}"')
        
        if not values:
            return 0.0, analysis
        
        # Calculate metrics
        analysis['unique_values'] = len(set(values))
        analysis['avg_length'] = statistics.mean([len(v) for v in values])
        
        # Check for business keywords
        for value in values:
            value_lower = value.lower()
            for category, keywords in self.business_keywords.items():
                if any(keyword in value_lower for keyword in keywords):
                    analysis['business_keyword_matches'] += 1
                    break
        
        # Check for template patterns
        for value in values:
            for pattern in self.template_patterns:
                if re.search(pattern, value):
                    analysis['template_pattern_matches'] += 1
                    break
        
        # Check for underscore naming (common in headers)
        analysis['contains_underscores'] = sum(1 for v in values if '_' in v)
        
        # Check for ALL CAPS (common in headers)
        analysis['all_caps_ratio'] = sum(1 for v in values if v.isupper() and len(v) > 2) / len(values)
        
        # Calculate composite score
        score = 0.0
        
        # High weight for business keywords
        score += (analysis['business_keyword_matches'] / len(values)) * 40
        
        # Medium weight for template patterns
        score += (analysis['template_pattern_matches'] / len(values)) * 30
        
        # Bonus for having many non-empty values
        coverage = analysis['non_empty_count'] / column_count
        score += coverage * 20
        
        # Bonus for underscores (header naming convention)
        score += (analysis['contains_underscores'] / len(values)) * 10
        
        # Bonus for unique values (headers should be unique)
        uniqueness = analysis['unique_values'] / len(values)
        score += uniqueness * 15
        
        # Penalty for very short or very long average length
        if 3 <= analysis['avg_length'] <= 25:
            score += 10
        elif analysis['avg_length'] < 3 or analysis['avg_length'] > 50:
            score -= 10
        
        return score, analysis
    
    def find_header_rows(self, sheet_data: Dict[str, Any], max_search_rows: int = 50) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        Find all potential header rows in the sheet data.
        
        Returns:
            List of (row_index, score, analysis) tuples, sorted by score descending
        """
        if 'data' not in sheet_data or 'columns' not in sheet_data:
            return []
        
        column_count = len(sheet_data['columns'])
        data_rows = sheet_data['data']
        
        candidates = []
        
        search_limit = min(max_search_rows, len(data_rows))
        
        for row_idx in range(search_limit):
            row = data_rows[row_idx]
            score, analysis = self.score_header_row(row, column_count)
            
            if score > 10:  # Minimum threshold
                candidates.append((row_idx, score, analysis))
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates
    
    def extract_headers(self, sheet_data: Dict[str, Any], header_row_idx: int) -> Dict[str, str]:
        """
        Extract cleaned headers from a specific row.
        
        Returns:
            Dictionary mapping col_X to cleaned header name
        """
        if 'data' not in sheet_data or header_row_idx >= len(sheet_data['data']):
            return {}
        
        header_row = sheet_data['data'][header_row_idx]
        column_count = len(sheet_data['columns'])
        
        headers = {}
        
        for i in range(column_count):
            raw_header = str(header_row.get(f'col_{i}', '')).strip()
            
            if raw_header and raw_header.lower() != 'nan':
                # Clean up the header
                cleaned = self.clean_header(raw_header)
                if cleaned:
                    headers[f'col_{i}'] = cleaned
        
        return headers
    
    def clean_header(self, raw_header: str) -> str:
        """Clean and normalize a raw header value."""
        # Remove template markers
        cleaned = raw_header
        for pattern in self.template_patterns:
            cleaned = re.sub(pattern, '', cleaned)
        
        # Remove common prefixes/suffixes
        cleaned = re.sub(r'^(axis|bid|itemType|predefinedAlternativeBid)[:|\|]', '', cleaned)
        cleaned = re.sub(r'\|.*$', '', cleaned)  # Remove everything after |
        
        # Clean up parentheses and brackets
        cleaned = re.sub(r'[(){}\[\]]', '', cleaned)
        
        # Normalize whitespace and underscores
        cleaned = re.sub(r'\s+', '_', cleaned.strip())
        cleaned = re.sub(r'_+', '_', cleaned)
        cleaned = cleaned.strip('_')
        
        # Convert to lowercase for consistency
        cleaned = cleaned.lower()
        
        return cleaned if len(cleaned) > 0 else ''
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a complete JSON file for header quality.
        
        Returns:
            Comprehensive analysis of all sheets in the file
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            return {'error': f'Failed to load file: {e}'}
        
        file_analysis = {
            'file_path': file_path,
            'sheets': {},
            'summary': {
                'total_sheets': 0,
                'sheets_with_generic_headers': 0,
                'sheets_with_detected_headers': 0,
                'best_header_detection_score': 0
            }
        }
        
        for sheet_name, sheet_data in data.items():
            if not isinstance(sheet_data, dict) or 'columns' not in sheet_data:
                continue
            
            file_analysis['summary']['total_sheets'] += 1
            
            # Check if this sheet has generic headers
            columns = sheet_data['columns']
            generic_pattern = re.compile(r'^col_\d+$')
            has_generic = any(generic_pattern.match(col) for col in columns)
            
            if has_generic:
                file_analysis['summary']['sheets_with_generic_headers'] += 1
            
            # Find potential header rows
            header_candidates = self.find_header_rows(sheet_data)
            
            sheet_analysis = {
                'has_generic_headers': has_generic,
                'column_count': len(columns),
                'row_count': len(sheet_data.get('data', [])),
                'header_candidates': []
            }
            
            for row_idx, score, analysis in header_candidates[:5]:  # Top 5 candidates
                sheet_analysis['header_candidates'].append({
                    'row_index': row_idx,
                    'score': round(score, 2),
                    'analysis': analysis
                })
                
                if score > file_analysis['summary']['best_header_detection_score']:
                    file_analysis['summary']['best_header_detection_score'] = round(score, 2)
            
            if header_candidates:
                file_analysis['summary']['sheets_with_detected_headers'] += 1
                
                # Extract headers from best candidate
                best_row_idx = header_candidates[0][0]
                extracted_headers = self.extract_headers(sheet_data, best_row_idx)
                sheet_analysis['extracted_headers'] = extracted_headers
            
            file_analysis['sheets'][sheet_name] = sheet_analysis
        
        return file_analysis


def demo_header_detection():
    """Demonstrate header detection on the AppliedMat file."""
    detector = HeaderDetector()
    
    file_path = '/home/ubuntu/MyProject/filling_assistant/training_files2/(AppliedMat) External CPT Empty_structured.json'
    
    print("🔍 ADVANCED HEADER DETECTION DEMO")
    print("=" * 50)
    
    analysis = detector.analyze_file(file_path)
    
    if 'error' in analysis:
        print(f"❌ Error: {analysis['error']}")
        return
    
    print(f"📁 File: {analysis['file_path'].split('/')[-1]}")
    print(f"📊 Summary:")
    print(f"   • Total Sheets: {analysis['summary']['total_sheets']}")
    print(f"   • Sheets with Generic Headers: {analysis['summary']['sheets_with_generic_headers']}")
    print(f"   • Sheets with Detected Headers: {analysis['summary']['sheets_with_detected_headers']}")
    print(f"   • Best Detection Score: {analysis['summary']['best_header_detection_score']}")
    print()
    
    for sheet_name, sheet_info in analysis['sheets'].items():
        print(f"📋 Sheet: {sheet_name}")
        print(f"   • Has Generic Headers: {sheet_info['has_generic_headers']}")
        print(f"   • Columns: {sheet_info['column_count']}, Rows: {sheet_info['row_count']}")
        
        if sheet_info['header_candidates']:
            best_candidate = sheet_info['header_candidates'][0]
            print(f"   • Best Header Row: {best_candidate['row_index']} (score: {best_candidate['score']})")
            print(f"   • Business Keywords Found: {best_candidate['analysis']['business_keyword_matches']}")
            print(f"   • Template Patterns Found: {best_candidate['analysis']['template_pattern_matches']}")
            
            if 'extracted_headers' in sheet_info:
                print(f"   • Extracted Headers ({len(sheet_info['extracted_headers'])}):")
                for col, header in list(sheet_info['extracted_headers'].items())[:10]:
                    print(f"     {col} → '{header}'")
                if len(sheet_info['extracted_headers']) > 10:
                    print(f"     ... and {len(sheet_info['extracted_headers']) - 10} more")
        else:
            print("   • No header candidates found")
        print()


if __name__ == "__main__":
    demo_header_detection()
