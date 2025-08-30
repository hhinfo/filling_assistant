#!/usr/bin/env python3
"""
Comprehensive test script for evaluating enhanced header detection performance
on the 30% test set with comparison between enhanced and basic headers
"""

import os
import json
import subprocess
import csv
from pathlib import Path
from datetime import datetime
import statistics

def run_identification(file_path, enhanced=True):
    """Run identification on a file and return results"""
    cmd = [
        "/home/ubuntu/MyProject/filling_assistant/.venv/bin/python", "-m", "filing_assistant.cli", 
        "identify", 
        "--file", str(file_path)
    ]
    
    if enhanced:
        cmd.append("--enhanced-headers")
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd="/home/ubuntu/MyProject/filling_assistant"
        )
        
        if result.returncode == 0:
            return parse_identification_output(result.stdout, enhanced)
        else:
            print(f"❌ Error running identification on {file_path}: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ Exception running identification on {file_path}: {e}")
        return None

def parse_identification_output(output, enhanced):
    """Parse the identification output to extract metrics"""
    lines = output.split('\n')
    
    result = {
        'enhanced_headers_enabled': enhanced,
        'enhanced_headers_used': False,
        'fillable_columns': 0,
        'unknown_columns': 0,
        'total_columns': 0,
        'sheets_processed': 0,
        'columns_details': [],
        'header_detector_available': True
    }
    
    # Check if enhanced headers were actually used
    if "Enhanced headers requested but not available" in output:
        result['header_detector_available'] = False
        result['enhanced_headers_used'] = False
    elif enhanced and "🤖 Enhanced business headers detected" in output:
        result['enhanced_headers_used'] = True
    elif enhanced:
        result['enhanced_headers_used'] = False
    
    # Parse summary statistics
    for line in lines:
        if "Fillable columns:" in line:
            try:
                result['fillable_columns'] = int(line.split(":")[1].strip())
            except:
                pass
        elif "Unknown columns:" in line:
            try:
                result['unknown_columns'] = int(line.split(":")[1].strip())
            except:
                pass
        elif "Sheets processed:" in line:
            try:
                result['sheets_processed'] = int(line.split(":")[1].strip())
            except:
                pass
    
    result['total_columns'] = result['fillable_columns'] + result['unknown_columns']
    
    return result

def test_file_pair(file_path):
    """Test a single file with both enhanced and basic headers"""
    print(f"🔍 Testing: {file_path.name}")
    
    # Test with enhanced headers
    enhanced_result = run_identification(file_path, enhanced=True)
    
    # Test with basic headers  
    basic_result = run_identification(file_path, enhanced=False)
    
    if enhanced_result and basic_result:
        comparison = {
            'file_name': file_path.name,
            'enhanced': enhanced_result,
            'basic': basic_result,
            'improvement': {
                'fillable_columns_delta': enhanced_result['fillable_columns'] - basic_result['fillable_columns'],
                'accuracy_improvement': 0  # Will calculate if we have ground truth
            }
        }
        
        # Print summary
        enhanced_icon = "🤖" if enhanced_result.get('enhanced_headers_used') else "📊"
        basic_icon = "📊"
        
        print(f"  {enhanced_icon} Enhanced: {enhanced_result['fillable_columns']} fillable columns")
        print(f"  {basic_icon} Basic: {basic_result['fillable_columns']} fillable columns")
        
        if enhanced_result['fillable_columns'] > basic_result['fillable_columns']:
            print(f"  ✅ +{comparison['improvement']['fillable_columns_delta']} improvement with enhanced headers")
        elif enhanced_result['fillable_columns'] < basic_result['fillable_columns']:
            print(f"  ⚠️ {comparison['improvement']['fillable_columns_delta']} fewer columns with enhanced headers")
        else:
            print(f"  ➖ No difference in fillable columns")
        
        return comparison
    
    return None

def generate_detailed_report(test_results):
    """Generate a comprehensive test report"""
    
    if not test_results:
        print("❌ No test results to report")
        return
    
    print("\n" + "="*80)
    print("🎯 COMPREHENSIVE TEST RESULTS - Enhanced vs Basic Headers")
    print("="*80)
    
    # Overall Statistics
    total_files = len(test_results)
    enhanced_better = sum(1 for r in test_results if r['improvement']['fillable_columns_delta'] > 0)
    basic_better = sum(1 for r in test_results if r['improvement']['fillable_columns_delta'] < 0)
    same_performance = sum(1 for r in test_results if r['improvement']['fillable_columns_delta'] == 0)
    
    enhanced_available = sum(1 for r in test_results if r['enhanced'].get('header_detector_available', False))
    enhanced_used = sum(1 for r in test_results if r['enhanced'].get('enhanced_headers_used', False))
    
    print(f"📊 OVERALL STATISTICS:")
    print(f"   • Total Files Tested: {total_files}")
    print(f"   • Enhanced Headers Available: {enhanced_available}/{total_files} ({enhanced_available/total_files*100:.1f}%)")
    print(f"   • Enhanced Headers Actually Used: {enhanced_used}/{total_files} ({enhanced_used/total_files*100:.1f}%)")
    print(f"   • Enhanced Performed Better: {enhanced_better}/{total_files} ({enhanced_better/total_files*100:.1f}%)")
    print(f"   • Basic Performed Better: {basic_better}/{total_files} ({basic_better/total_files*100:.1f}%)")
    print(f"   • Same Performance: {same_performance}/{total_files} ({same_performance/total_files*100:.1f}%)")
    
    # Performance Metrics
    enhanced_totals = sum(r['enhanced']['fillable_columns'] for r in test_results)
    basic_totals = sum(r['basic']['fillable_columns'] for r in test_results)
    total_improvement = enhanced_totals - basic_totals
    
    print(f"\\n📈 PERFORMANCE METRICS:")
    print(f"   • Total Enhanced Fillable Columns: {enhanced_totals}")
    print(f"   • Total Basic Fillable Columns: {basic_totals}")
    print(f"   • Net Improvement: {total_improvement} columns ({total_improvement/basic_totals*100:.1f}%)")
    
    # Individual File Results
    print(f"\\n📋 DETAILED FILE RESULTS:")
    print(f"{'File Name':<50} {'Enhanced':<10} {'Basic':<10} {'Delta':<8} {'Status':<15}")
    print("-" * 95)
    
    for result in sorted(test_results, key=lambda x: x['improvement']['fillable_columns_delta'], reverse=True):
        enhanced_cols = result['enhanced']['fillable_columns']
        basic_cols = result['basic']['fillable_columns']
        delta = result['improvement']['fillable_columns_delta']
        
        if delta > 0:
            status = f"✅ +{delta}"
        elif delta < 0:
            status = f"⚠️ {delta}"
        else:
            status = "➖ Same"
        
        enhanced_icon = "🤖" if result['enhanced'].get('enhanced_headers_used') else "📊"
        file_name = result['file_name'][:45] + "..." if len(result['file_name']) > 45 else result['file_name']
        
        print(f"{file_name:<50} {enhanced_icon}{enhanced_cols:<9} 📊{basic_cols:<9} {delta:<8} {status:<15}")
    
    # Success Rate Analysis
    if enhanced_available > 0:
        actual_enhancement_rate = enhanced_used / enhanced_available * 100
        print(f"\\n🎯 ENHANCEMENT SUCCESS ANALYSIS:")
        print(f"   • When Enhanced Headers Available: {actual_enhancement_rate:.1f}% actually used")
        print(f"   • Average Improvement When Enhanced Used: {statistics.mean([r['improvement']['fillable_columns_delta'] for r in test_results if r['enhanced'].get('enhanced_headers_used', False)]):.1f} columns")
    
    # Generate CSV Report
    csv_path = Path("test_results_report.csv")
    with open(csv_path, 'w', newline='') as csvfile:
        fieldnames = ['file_name', 'enhanced_fillable', 'basic_fillable', 'improvement', 
                     'enhanced_headers_used', 'enhanced_headers_available']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in test_results:
            writer.writerow({
                'file_name': result['file_name'],
                'enhanced_fillable': result['enhanced']['fillable_columns'],
                'basic_fillable': result['basic']['fillable_columns'],
                'improvement': result['improvement']['fillable_columns_delta'],
                'enhanced_headers_used': result['enhanced'].get('enhanced_headers_used', False),
                'enhanced_headers_available': result['enhanced'].get('header_detector_available', False)
            })
    
    print(f"\\n💾 Detailed CSV report saved to: {csv_path}")

def main():
    test_dir = Path("test_set")
    
    if not test_dir.exists():
        print(f"❌ Test directory {test_dir} not found!")
        return
    
    # Get all structured JSON files in test set
    test_files = list(test_dir.glob("*_structured.json"))
    
    if not test_files:
        print(f"❌ No test files found in {test_dir}")
        return
    
    print(f"🚀 Starting comprehensive test of {len(test_files)} files...")
    print(f"📁 Test directory: {test_dir}")
    print(f"🎯 Testing enhanced header detection vs basic headers")
    print("="*60)
    
    test_results = []
    
    for i, test_file in enumerate(test_files, 1):
        print(f"\\n[{i}/{len(test_files)}] ", end="")
        result = test_file_pair(test_file)
        if result:
            test_results.append(result)
    
    print("\\n" + "="*60)
    print("🎉 Testing completed!")
    
    # Generate comprehensive report
    generate_detailed_report(test_results)
    
    # Save detailed results
    results_path = Path("detailed_test_results.json")
    with open(results_path, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\\n💾 Detailed test results saved to: {results_path}")

if __name__ == "__main__":
    main()
