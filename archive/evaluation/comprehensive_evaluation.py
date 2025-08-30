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

def categorize_files(files: List[Path]) -> Dict[str, List[Path]]:
    """Categorize files into in-domain vs out-of-domain based on training patterns."""
    
    # Known training patterns from our training data
    in_domain_patterns = [
        "APEX", "CPT_Global Air Service", "Customer CPT_2025", "Customer CPT_Zebra", 
        "Emerson CPT", "Commscope", "AEO CPT", "Corsair"
    ]
    
    in_domain = []
    out_of_domain = []
    
    for file_path in files:
        file_name = file_path.name
        is_in_domain = any(pattern in file_name for pattern in in_domain_patterns)
        
        if is_in_domain:
            in_domain.append(file_path)
        else:
            out_of_domain.append(file_path)
    
    return {
        "in_domain": in_domain,
        "out_of_domain": out_of_domain
    }

def test_files(files: List[Path], category: str) -> Dict:
    """Test a list of files and return aggregated results."""
    print(f"\n🔍 Testing {category.upper()} files ({len(files)} files)")
    print("-" * 60)
    
    total_fillable = 0
    total_unknown = 0
    total_columns = 0
    successful_tests = 0
    file_results = []
    
    for file_path in files:
        print(f"📁 {file_path.name}")
        
        # Run identification without specifying sheet (auto-detect)
        result = run_identify(str(file_path))
        
        if result["success"]:
            metrics = parse_identification_results(result["stdout"])
            
            if metrics["total_columns"] > 0:
                successful_tests += 1
                total_fillable += metrics["fillable_columns"]
                total_unknown += metrics["unknown_columns"]
                total_columns += metrics["total_columns"]
                
                rate = (metrics["fillable_columns"] / metrics["total_columns"]) * 100 if metrics["total_columns"] > 0 else 0
                print(f"   ✅ {metrics['fillable_columns']}/{metrics['total_columns']} fillable ({rate:.1f}%)")
                
                file_results.append({
                    "file": file_path.name,
                    "fillable": metrics["fillable_columns"],
                    "total": metrics["total_columns"],
                    "rate": rate
                })
            else:
                print(f"   ⚠️ No columns found")
        else:
            print(f"   ❌ Failed")
    
    return {
        "category": category,
        "files_tested": successful_tests,
        "total_files": len(files),
        "total_columns": total_columns,
        "fillable_columns": total_fillable,
        "unknown_columns": total_unknown,
        "fillable_rate": (total_fillable / total_columns * 100) if total_columns > 0 else 0,
        "file_results": file_results
    }

def main():
    test_dir = Path("/home/ubuntu/MyProject/filling_assistant/test_subset")
    
    # Find all files (both empty and filled for comprehensive testing)
    all_files = list(test_dir.glob("*structured.json"))
    
    # Categorize files
    categorized = categorize_files(all_files)
    
    print("🎯 ENHANCED HEADER DETECTION COMPREHENSIVE EVALUATION")
    print("=" * 80)
    print(f"Total test files: {len(all_files)}")
    print(f"In-domain files: {len(categorized['in_domain'])}")
    print(f"Out-of-domain files: {len(categorized['out_of_domain'])}")
    
    # Test in-domain files
    in_domain_results = test_files(categorized["in_domain"], "IN-DOMAIN")
    
    # Test out-of-domain files  
    out_domain_results = test_files(categorized["out_of_domain"], "OUT-OF-DOMAIN")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 EVALUATION SUMMARY")
    print("=" * 80)
    
    print(f"\n🎯 IN-DOMAIN PERFORMANCE:")
    if in_domain_results["total_columns"] > 0:
        print(f"   Files: {in_domain_results['files_tested']}/{in_domain_results['total_files']}")
        print(f"   Columns: {in_domain_results['fillable_columns']}/{in_domain_results['total_columns']}")
        print(f"   Success Rate: {in_domain_results['fillable_rate']:.1f}%")
    else:
        print("   No testable in-domain files found")
    
    print(f"\n🌐 OUT-OF-DOMAIN PERFORMANCE:")
    if out_domain_results["total_columns"] > 0:
        print(f"   Files: {out_domain_results['files_tested']}/{out_domain_results['total_files']}")
        print(f"   Columns: {out_domain_results['fillable_columns']}/{out_domain_results['total_columns']}")
        print(f"   Success Rate: {out_domain_results['fillable_rate']:.1f}%")
    else:
        print("   No testable out-of-domain files found")
    
    # Overall performance
    total_fillable = in_domain_results["fillable_columns"] + out_domain_results["fillable_columns"]
    total_columns = in_domain_results["total_columns"] + out_domain_results["total_columns"]
    overall_rate = (total_fillable / total_columns * 100) if total_columns > 0 else 0
    
    print(f"\n🎯 OVERALL PERFORMANCE:")
    print(f"   Total Columns: {total_fillable}/{total_columns}")
    print(f"   Overall Success Rate: {overall_rate:.1f}%")
    
    # Top performers
    all_results = in_domain_results["file_results"] + out_domain_results["file_results"]
    all_results.sort(key=lambda x: x["rate"], reverse=True)
    
    print(f"\n📈 TOP PERFORMING FILES:")
    for i, result in enumerate(all_results[:5]):
        domain = "IN" if any(result["file"] in f.name for f in categorized["in_domain"]) else "OUT"
        print(f"   {i+1}. {result['file']}: {result['fillable']}/{result['total']} ({result['rate']:.1f}%) [{domain}]")
    
    # Save results
    evaluation_results = {
        "summary": {
            "total_files": len(all_files),
            "in_domain": in_domain_results,
            "out_of_domain": out_domain_results,
            "overall": {
                "fillable_columns": total_fillable,
                "total_columns": total_columns,
                "success_rate": overall_rate
            }
        },
        "detailed_results": {
            "in_domain_files": [f.name for f in categorized["in_domain"]],
            "out_of_domain_files": [f.name for f in categorized["out_of_domain"]],
            "all_results": all_results
        }
    }
    
    with open("/home/ubuntu/MyProject/filling_assistant/comprehensive_evaluation_results.json", "w") as f:
        json.dump(evaluation_results, f, indent=2)
    
    print(f"\n📝 Detailed results saved to: comprehensive_evaluation_results.json")

if __name__ == "__main__":
    main()
