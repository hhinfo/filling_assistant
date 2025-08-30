#!/usr/bin/env python3
"""
Header Mapping Generator for Filing Assistant System

This script generates header mappings for all training files without modifying
the original JSON files. It creates a mapping file that can be used by io_utils.py
to provide better header names for human interpretation while keeping the AI model
unchanged.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any
from practical_header_detection import detect_real_headers

def generate_header_mappings(training_dir: str, output_file: str = "header_mappings.json") -> Dict[str, Any]:
    """
    Generate header mappings for all training files.
    
    Args:
        training_dir: Directory containing training JSON files
        output_file: Output file for header mappings
        
    Returns:
        Dictionary containing all header mappings
    """
    training_path = Path(training_dir)
    json_files = list(training_path.glob("*_structured.json"))
    
    header_mappings = {
        "metadata": {
            "generated_by": "header_mapping_generator.py",
            "training_directory": training_dir,
            "total_files_processed": 0,
            "files_with_generic_headers": 0,
            "files_with_detected_headers": 0,
            "detection_statistics": {}
        },
        "file_mappings": {}
    }
    
    print(f"🔍 Generating header mappings for {len(json_files)} files...")
    print("=" * 60)
    
    for json_file in sorted(json_files):
        file_name = json_file.name
        print(f"\n📁 Processing: {file_name}")
        
        header_mappings["metadata"]["total_files_processed"] += 1
        
        # Detect headers for this file
        detected_headers = detect_real_headers(str(json_file))
        
        if detected_headers:
            header_mappings["metadata"]["files_with_generic_headers"] += 1
            
            file_mapping = {
                "file_path": str(json_file),
                "has_generic_headers": True,
                "sheet_mappings": {}
            }
            
            total_headers_detected = 0
            
            for sheet_name, mapping in detected_headers.items():
                if mapping:
                    file_mapping["sheet_mappings"][sheet_name] = mapping
                    total_headers_detected += len(mapping)
                    print(f"   📋 {sheet_name}: {len(mapping)} headers detected")
            
            if total_headers_detected > 0:
                header_mappings["metadata"]["files_with_detected_headers"] += 1
                file_mapping["total_headers_detected"] = total_headers_detected
                header_mappings["file_mappings"][file_name] = file_mapping
                print(f"   ✅ Total headers detected: {total_headers_detected}")
            else:
                print(f"   ❌ No headers could be detected")
        else:
            print(f"   ✅ File has proper headers (no conversion needed)")
            header_mappings["file_mappings"][file_name] = {
                "file_path": str(json_file),
                "has_generic_headers": False,
                "sheet_mappings": {}
            }
    
    # Generate statistics
    metadata = header_mappings["metadata"]
    if metadata["files_with_generic_headers"] > 0:
        detection_rate = (metadata["files_with_detected_headers"] / metadata["files_with_generic_headers"]) * 100
        metadata["detection_statistics"]["success_rate"] = round(detection_rate, 1)
    else:
        metadata["detection_statistics"]["success_rate"] = 0.0
    
    # Save mappings to file
    output_path = Path(training_dir) / output_file
    with open(output_path, 'w') as f:
        json.dump(header_mappings, f, indent=2)
    
    print(f"\n💾 Header mappings saved to: {output_path}")
    print_mapping_summary(header_mappings)
    
    return header_mappings

def print_mapping_summary(mappings: Dict[str, Any]) -> None:
    """Print a summary of the generated mappings."""
    metadata = mappings["metadata"]
    
    print(f"\n📊 HEADER MAPPING SUMMARY")
    print("=" * 30)
    print(f"📁 Total files processed: {metadata['total_files_processed']}")
    print(f"🔴 Files with generic headers: {metadata['files_with_generic_headers']}")
    print(f"🎯 Files with detected headers: {metadata['files_with_detected_headers']}")
    print(f"📈 Detection success rate: {metadata['detection_statistics']['success_rate']}%")
    
    # Show top files by header count
    file_header_counts = []
    for file_name, file_mapping in mappings["file_mappings"].items():
        if "total_headers_detected" in file_mapping:
            file_header_counts.append((file_name, file_mapping["total_headers_detected"]))
    
    if file_header_counts:
        file_header_counts.sort(key=lambda x: x[1], reverse=True)
        print(f"\n🏆 Top files by headers detected:")
        for file_name, count in file_header_counts[:5]:
            print(f"   📋 {file_name}: {count} headers")

def create_enhanced_io_utils_integration() -> str:
    """Generate code for integrating header mappings into io_utils.py"""
    
    integration_code = '''
# Add this to io_utils.py for header mapping integration

import json
from pathlib import Path

# Global variable to cache header mappings
_header_mappings = None

def load_header_mappings(training_dir: str = None) -> Dict[str, Any]:
    """Load header mappings from the mapping file."""
    global _header_mappings
    
    if _header_mappings is not None:
        return _header_mappings
    
    if training_dir is None:
        training_dir = "training_files2"  # Default directory
    
    mapping_file = Path(training_dir) / "header_mappings.json"
    
    if not mapping_file.exists():
        print(f"⚠️  Header mapping file not found: {mapping_file}")
        return {}
    
    try:
        with open(mapping_file, 'r') as f:
            _header_mappings = json.load(f)
        return _header_mappings
    except Exception as e:
        print(f"❌ Error loading header mappings: {e}")
        return {}

def get_enhanced_headers(file_path: str, sheet_name: str, original_headers: List[str]) -> List[str]:
    """
    Get enhanced headers using mappings if available, otherwise return original headers.
    
    Args:
        file_path: Path to the JSON file
        sheet_name: Name of the sheet
        original_headers: Original column headers from JSON
        
    Returns:
        Enhanced headers with business names where available
    """
    mappings = load_header_mappings()
    
    if not mappings or "file_mappings" not in mappings:
        return original_headers
    
    file_name = Path(file_path).name
    
    if file_name not in mappings["file_mappings"]:
        return original_headers
    
    file_mapping = mappings["file_mappings"][file_name]
    
    if not file_mapping.get("has_generic_headers", False):
        return original_headers  # File already has good headers
    
    sheet_mappings = file_mapping.get("sheet_mappings", {})
    
    if sheet_name not in sheet_mappings:
        return original_headers  # No mapping for this sheet
    
    # Apply header mapping
    header_mapping = sheet_mappings[sheet_name]
    enhanced_headers = []
    
    for i, original_header in enumerate(original_headers):
        # Try to find mapping for this column
        col_key = f"col_{i}"
        if col_key in header_mapping:
            enhanced_headers.append(header_mapping[col_key])
        else:
            enhanced_headers.append(original_header)  # Keep original if no mapping
    
    return enhanced_headers

def load_structured_data_enhanced(file_path: str) -> Dict[str, Any]:
    """
    Enhanced version of load_structured_data that uses header mappings.
    """
    # Load original data
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    structured_data = {}
    
    for sheet_name, sheet_data in data.items():
        if not isinstance(sheet_data, dict) or 'columns' not in sheet_data:
            continue
        
        # Get original headers
        original_headers = sheet_data['columns']
        
        # Detect header row (use existing logic)
        header_row_idx, detected_headers = detect_header_row(sheet_data)
        
        # Enhance headers with mappings
        enhanced_headers = get_enhanced_headers(file_path, sheet_name, detected_headers)
        
        structured_data[sheet_name] = {
            'headers': enhanced_headers,
            'original_headers': detected_headers,  # Keep original for compatibility
            'data': sheet_data.get('data', []),
            'header_row_detected': header_row_idx,
            'headers_enhanced': len(enhanced_headers) != len(detected_headers) or enhanced_headers != detected_headers
        }
    
    return structured_data

# Usage example:
# Replace calls to load_structured_data(file_path) with load_structured_data_enhanced(file_path)
# The enhanced version provides better header names while maintaining full compatibility
'''
    
    return integration_code

def main():
    """Main function to generate header mappings."""
    training_dir = "training_files2"
    
    print("🎯 HEADER MAPPING GENERATOR")
    print("=" * 30)
    print(f"📁 Training directory: {training_dir}")
    print()
    
    # Generate mappings
    mappings = generate_header_mappings(training_dir)
    
    print(f"\n🔧 INTEGRATION CODE:")
    print("=" * 20)
    print("Add the following code to io_utils.py:")
    print()
    
    integration_code = create_enhanced_io_utils_integration()
    print(integration_code)
    
    print(f"\n✅ NEXT STEPS:")
    print("=" * 15)
    print("1. 📋 Review generated header_mappings.json")
    print("2. 🔧 Integrate enhanced functions into io_utils.py")
    print("3. 🧪 Test with existing workflows to ensure compatibility")
    print("4. 🎯 Update CLI to display enhanced headers for better UX")
    print("5. 🚀 Deploy with zero risk to existing AI model")

if __name__ == "__main__":
    main()
