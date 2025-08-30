#!/usr/bin/env python3

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

def run_identify(file_path: str, sheet_name: str = None) -> Dict:
    """Run the identify command and parse results."""
    cmd = [
        sys.executable, "-m", "filing_assistant.cli", "identify",
        "--file", file_path,
        "--store", "patterns_store.json",
        "--enhanced-headers"
    ]
    
    if sheet_name:
        cmd.extend(["--sheet", sheet_name])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/ubuntu/MyProject/filling_assistant")
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "stdout": "",
            "stderr": ""
        }

def get_sheet_names(file_path: str) -> List[str]:
    """Extract sheet names from structured JSON file."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return list(data.keys())
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

def parse_identification_results(output: str) -> Dict:
    """Parse the identification output to extract metrics."""
    fillable_columns = 0
    unknown_columns = 0
    sheets_processed = 0
    enhanced_enabled = False
    
    lines = output.split('\n')
    for line in lines:
        if "Fillable columns:" in line:
            try:
                fillable_columns = int(line.split("Fillable columns:")[1].split()[0])
            except:
                pass
        elif "Unknown columns:" in line:
            try:
                unknown_columns = int(line.split("Unknown columns:")[1].split()[0])
            except:
                pass
        elif "Sheets processed:" in line:
            try:
                sheets_processed = int(line.split("Sheets processed:")[1].split()[0])
            except:
                pass
        elif "Enhanced headers: ENABLED" in line:
            enhanced_enabled = True
    
    return {
        "fillable_columns": fillable_columns,
        "unknown_columns": unknown_columns,
        "sheets_processed": sheets_processed,
        "enhanced_enabled": enhanced_enabled,
        "total_columns": fillable_columns + unknown_columns
    }

def main():
    test_dir = Path("/home/ubuntu/MyProject/filling_assistant/test_subset")
    
    # Find all empty files
    empty_files = [f for f in test_dir.glob("*Empty*structured.json")]
    
    print(f"🧪 Testing Enhanced Header Detection on {len(empty_files)} files")
    print("=" * 80)
    
    results = []
    total_fillable = 0
    total_unknown = 0
    total_columns = 0
    successful_tests = 0
    
    for file_path in empty_files:
        print(f"\n📁 Testing: {file_path.name}")
        
        # Get sheet names
        sheet_names = get_sheet_names(str(file_path))
        if not sheet_names:
            print(f"   ❌ Could not read sheet names")
            continue
            
        file_results = {
            "file": file_path.name,
            "sheets": {},
            "total_fillable": 0,
            "total_unknown": 0,
            "total_columns": 0
        }
        
        # Test each sheet
        for sheet_name in sheet_names:
            print(f"   📋 Sheet: {sheet_name}")
            
            result = run_identify(str(file_path), sheet_name)
            
            if result["success"]:
                metrics = parse_identification_results(result["stdout"])
                file_results["sheets"][sheet_name] = metrics
                file_results["total_fillable"] += metrics["fillable_columns"]
                file_results["total_unknown"] += metrics["unknown_columns"]
                file_results["total_columns"] += metrics["total_columns"]
                
                print(f"      ✅ {metrics['fillable_columns']} fillable, {metrics['unknown_columns']} unknown")
            else:
                print(f"      ❌ Failed: {result.get('error', 'Unknown error')}")
                file_results["sheets"][sheet_name] = {"error": result.get("error", "Unknown error")}
        
        if file_results["total_columns"] > 0:
            successful_tests += 1
            total_fillable += file_results["total_fillable"]
            total_unknown += file_results["total_unknown"]
            total_columns += file_results["total_columns"]
            
            print(f"   📊 File Total: {file_results['total_fillable']} fillable / {file_results['total_columns']} columns")
        
        results.append(file_results)
    
    # Summary
    print("\n" + "=" * 80)
    print("🎯 ENHANCED HEADER DETECTION EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Files tested: {successful_tests}/{len(empty_files)}")
    print(f"Total columns analyzed: {total_columns}")
    print(f"Fillable columns identified: {total_fillable}")
    print(f"Unknown columns: {total_unknown}")
    
    if total_columns > 0:
        fillable_rate = (total_fillable / total_columns) * 100
        print(f"Fillable identification rate: {fillable_rate:.1f}%")
    
    # Top performing files
    print(f"\n📈 TOP PERFORMING FILES:")
    performing_files = [r for r in results if r["total_columns"] > 0]
    performing_files.sort(key=lambda x: x["total_fillable"], reverse=True)
    
    for i, file_result in enumerate(performing_files[:5]):
        if file_result["total_columns"] > 0:
            rate = (file_result["total_fillable"] / file_result["total_columns"]) * 100
            print(f"   {i+1}. {file_result['file']}: {file_result['total_fillable']}/{file_result['total_columns']} ({rate:.1f}%)")
    
    # Save detailed results
    with open("/home/ubuntu/MyProject/filling_assistant/test_evaluation_results.json", "w") as f:
        json.dump({
            "summary": {
                "files_tested": successful_tests,
                "total_files": len(empty_files),
                "total_columns": total_columns,
                "fillable_columns": total_fillable,
                "unknown_columns": total_unknown,
                "fillable_rate": (total_fillable / total_columns * 100) if total_columns > 0 else 0
            },
            "detailed_results": results
        }, f, indent=2)
    
    print(f"\n📝 Detailed results saved to: test_evaluation_results.json")

if __name__ == "__main__":
    main()
