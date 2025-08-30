#!/usr/bin/env python3
"""
Practical Header Detection Integration

This module provides a simple interface to improve header detection
for the filing assistant system when dealing with generic column names.
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

def detect_real_headers(json_file_path: str) -> Dict[str, Dict[str, str]]:
    """
    Detect real headers in JSON files with generic column names.
    
    Args:
        json_file_path: Path to the JSON file
        
    Returns:
        Dictionary mapping sheet names to column mappings (col_X -> real_header)
    """
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading {json_file_path}: {e}")
        return {}
    
    result = {}
    
    for sheet_name, sheet_data in data.items():
        if not isinstance(sheet_data, dict) or 'columns' not in sheet_data or 'data' not in sheet_data:
            continue
            
        # Check if this sheet has generic headers
        columns = sheet_data['columns']
        has_generic = any(re.match(r'^col_\d+$', col) for col in columns)
        
        if not has_generic:
            continue  # Skip sheets that already have good headers
            
        # Find the best header row
        header_mapping = find_best_headers(sheet_data)
        if header_mapping:
            result[sheet_name] = header_mapping
    
    return result

def find_best_headers(sheet_data: Dict[str, Any]) -> Dict[str, str]:
    """Find the best header row in a sheet and extract clean headers."""
    
    # Business keywords that indicate header content
    business_keywords = [
        'lane', 'service', 'port', 'origin', 'destination', 'carrier', 'freight',
        'cost', 'price', 'rate', 'fee', 'charge', 'amount', 'total', 'minimum',
        'weight', 'cbm', 'volume', 'kilos', 'country', 'region', 'date', 'currency',
        'id', 'code', 'number', 'reference', 'quote', 'bid', 'proposal'
    ]
    
    # Template patterns
    template_patterns = [r'<<.*?>>', r'axis\(', r'bid\|']
    
    column_count = len(sheet_data['columns'])
    data_rows = sheet_data['data']
    
    best_score = 0
    best_row_idx = -1
    
    # Search first 50 rows for headers
    for row_idx in range(min(50, len(data_rows))):
        row = data_rows[row_idx]
        
        # Count non-empty values
        values = []
        for i in range(column_count):
            val = str(row.get(f'col_{i}', '')).strip()
            if val and val.lower() != 'nan':
                values.append(val)
        
        if len(values) < 3:  # Need at least 3 non-empty values
            continue
        
        # Score this row
        score = 0
        
        # Check for business keywords
        keyword_matches = 0
        for value in values:
            value_lower = value.lower()
            if any(keyword in value_lower for keyword in business_keywords):
                keyword_matches += 1
        
        score += (keyword_matches / len(values)) * 50
        
        # Check for template patterns
        template_matches = 0
        for value in values:
            if any(re.search(pattern, value) for pattern in template_patterns):
                template_matches += 1
        
        score += (template_matches / len(values)) * 40
        
        # Bonus for coverage (many non-empty columns)
        coverage = len(values) / column_count
        score += coverage * 30
        
        # Bonus for underscores (common in headers)
        underscore_count = sum(1 for v in values if '_' in v)
        score += (underscore_count / len(values)) * 20
        
        if score > best_score:
            best_score = score
            best_row_idx = row_idx
    
    # Extract headers from best row
    if best_row_idx >= 0 and best_score > 15:  # Minimum threshold
        return extract_clean_headers(data_rows[best_row_idx], column_count)
    
    return {}

def extract_clean_headers(header_row: Dict[str, Any], column_count: int) -> Dict[str, str]:
    """Extract and clean headers from a row."""
    headers = {}
    
    for i in range(column_count):
        raw_header = str(header_row.get(f'col_{i}', '')).strip()
        
        if raw_header and raw_header.lower() != 'nan':
            cleaned = clean_header_name(raw_header)
            if cleaned:
                headers[f'col_{i}'] = cleaned
    
    return headers

def clean_header_name(raw_header: str) -> str:
    """Clean a raw header value into a usable name."""
    # Remove template markers
    cleaned = re.sub(r'<<.*?>>', '', raw_header)
    cleaned = re.sub(r'axis\([^)]*\)', '', cleaned)
    cleaned = re.sub(r'bid\|[^>]*', '', cleaned)
    
    # Remove parentheses and brackets
    cleaned = re.sub(r'[(){}\[\]]', '', cleaned)
    
    # Clean up separators
    cleaned = re.sub(r'[:|].*$', '', cleaned)  # Remove everything after : or |
    
    # Normalize to snake_case
    cleaned = re.sub(r'\s+', '_', cleaned.strip())
    cleaned = re.sub(r'_+', '_', cleaned)
    cleaned = cleaned.strip('_').lower()
    
    return cleaned if len(cleaned) > 0 else ''

def create_header_mapping_report(training_dir: str) -> None:
    """Create a report of header mappings for all training files."""
    
    print("🔍 HEADER DETECTION REPORT")
    print("=" * 50)
    
    training_path = Path(training_dir)
    json_files = list(training_path.glob("*_structured.json"))
    
    total_files = len(json_files)
    files_with_generic = 0
    files_with_detected_headers = 0
    
    for json_file in sorted(json_files):
        print(f"\n📁 {json_file.name}")
        print("-" * 40)
        
        header_mappings = detect_real_headers(str(json_file))
        
        if not header_mappings:
            print("   ✅ No generic headers detected (good quality)")
            continue
        
        files_with_generic += 1
        
        has_detections = False
        for sheet_name, mapping in header_mappings.items():
            if mapping:
                has_detections = True
                print(f"   📋 {sheet_name}:")
                print(f"      🎯 Detected {len(mapping)} headers:")
                
                # Show sample mappings
                for col, header in list(mapping.items())[:5]:
                    print(f"         {col} → '{header}'")
                
                if len(mapping) > 5:
                    print(f"         ... and {len(mapping) - 5} more")
        
        if has_detections:
            files_with_detected_headers += 1
        else:
            print("   ❌ No headers could be detected")
    
    print(f"\n📊 SUMMARY")
    print("=" * 20)
    print(f"   📁 Total files analyzed: {total_files}")
    print(f"   🔴 Files with generic headers: {files_with_generic}")
    print(f"   🎯 Files with detected headers: {files_with_detected_headers}")
    
    if files_with_generic > 0:
        detection_rate = (files_with_detected_headers / files_with_generic) * 100
        print(f"   📈 Detection success rate: {detection_rate:.1f}%")

def improve_io_utils_with_header_detection():
    """Show how to integrate header detection into io_utils.py"""
    
    print("🔧 INTEGRATION STRATEGY FOR IO_UTILS.PY")
    print("=" * 45)
    print()
    
    integration_code = '''
# Add this to io_utils.py

def detect_header_row_advanced(sheet_data):
    """
    Advanced header detection that handles both proper headers and generic columns.
    """
    columns = sheet_data.get('columns', [])
    
    # Check if we have generic column names
    has_generic = any(re.match(r'^col_\\d+$', col) for col in columns)
    
    if not has_generic:
        # Use existing logic for good headers
        return detect_header_row(sheet_data)
    
    # For generic headers, search for real headers in data
    from header_detector import find_best_headers
    
    header_mapping = find_best_headers(sheet_data)
    if header_mapping:
        # Create a virtual header row using detected headers
        detected_headers = []
        for i, col in enumerate(columns):
            if f'col_{i}' in header_mapping:
                detected_headers.append(header_mapping[f'col_{i}'])
            else:
                detected_headers.append(f'col_{i}')  # Keep generic if no detection
        
        return 0, detected_headers  # Return row 0 with improved headers
    
    # Fallback to original method
    return detect_header_row(sheet_data)

# Usage in load_structured_data():
def load_structured_data(file_path):
    """Load structured data with advanced header detection."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    structured_data = {}
    for sheet_name, sheet_data in data.items():
        # Use advanced header detection
        header_row_idx, headers = detect_header_row_advanced(sheet_data)
        
        # Continue with existing logic...
        structured_data[sheet_name] = {
            'headers': headers,
            'data': sheet_data.get('data', []),
            'header_row_detected': header_row_idx
        }
    
    return structured_data
'''
    
    print(integration_code)

if __name__ == "__main__":
    # Demo the practical usage
    print("🎯 PRACTICAL HEADER DETECTION DEMO")
    print("=" * 40)
    
    # Test on AppliedMat file
    test_file = "/home/ubuntu/MyProject/filling_assistant/training_files2/(AppliedMat) External CPT Empty_structured.json"
    
    mappings = detect_real_headers(test_file)
    
    if mappings:
        print(f"✅ Detected headers in {len(mappings)} sheets:")
        for sheet, mapping in mappings.items():
            print(f"   📋 {sheet}: {len(mapping)} headers detected")
            for col, header in list(mapping.items())[:3]:
                print(f"      {col} → '{header}'")
    else:
        print("❌ No header mappings detected")
    
    print("\n" + "="*50)
    improve_io_utils_with_header_detection()
