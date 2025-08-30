#!/usr/bin/env python3
"""
Test script for the enhanced header detection system with live OpenAI validation.
This script will demonstrate the 5-strategy detection system in action.
"""

import json
import os
import sys
from typing import Dict, List, Any
from enhanced_header_detector import EnhancedHeaderDetector

def load_sample_files(limit: int = 3) -> List[Dict[str, Any]]:
    """Load sample structured files for testing."""
    training_dir = "training_files2"
    sample_files = []
    
    # Get a few different companies for variety
    sample_patterns = [
        "(ACCO) External CPT Empty_structured.json",
        "(AppliedMat) External CPT Filled_structured.json", 
        "(Commscope) External CPT Empty_structured.json"
    ]
    
    for pattern in sample_patterns[:limit]:
        file_path = os.path.join(training_dir, pattern)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    sample_files.append({
                        'filename': pattern,
                        'path': file_path,
                        'data': data
                    })
                    print(f"✅ Loaded: {pattern}")
            except Exception as e:
                print(f"❌ Error loading {pattern}: {e}")
        else:
            print(f"⚠️ File not found: {file_path}")
    
    return sample_files

def test_detection_strategies(detector: EnhancedHeaderDetector, sample_files: List[Dict[str, Any]]):
    """Test all 5 detection strategies on sample files."""
    
    print("\n" + "="*80)
    print("🧪 TESTING ENHANCED HEADER DETECTION STRATEGIES")
    print("="*80)
    
    for i, file_info in enumerate(sample_files, 1):
        filename = file_info['filename']
        data = file_info['data']
        
        print(f"\n📄 Test {i}: {filename}")
        print("-" * 60)
        
        # Test each sheet in the file
        for sheet_name, sheet_data in data.items():
            if not isinstance(sheet_data, dict) or 'data' not in sheet_data:
                continue
                
            print(f"\n📋 Sheet: {sheet_name}")
            
            # Get current headers
            columns = sheet_data.get('columns', [])
            if not columns:
                print("   ⚠️ No columns found")
                continue
                
            print(f"   Current headers: {columns[:5]}{'...' if len(columns) > 5 else ''}")
            
            # Run detection
            try:
                result = detector.detect_headers_enhanced(sheet_data, filename)
                
                # Check the actual structure returned
                if result.get('final_mapping'):
                    final_mapping = result['final_mapping']
                    print(f"   ✅ Enhanced headers detected")
                    
                    # Show mapping (first 5 columns)
                    mappings = list(final_mapping.items())[:5]
                    for col, header in mappings:
                        print(f"      {col}: {header}")
                    if len(final_mapping) > 5:
                        print(f"      ... and {len(final_mapping) - 5} more")
                    
                    # Show confidence
                    confidence = result.get('confidence', 0)
                    print(f"   🎪 Total confidence: {confidence:.3f}")
                    
                    # Show OpenAI analysis if available
                    openai_validation = result.get('openai_validation', {})
                    if openai_validation.get('decision'):
                        print(f"   🤖 AI Decision: {openai_validation.get('decision', 'N/A')}")
                        reasoning = openai_validation.get('reasoning', '')
                        if reasoning:
                            print(f"   🎯 AI Reasoning: {reasoning[:100]}...")
                    
                    # Show strategy results
                    strategy_results = result.get('strategy_results', {})
                    print(f"   📊 Strategy detections:")
                    for strategy, count in strategy_results.items():
                        print(f"      • {strategy}: {count} candidates")
                    
                else:
                    print(f"   ❌ No enhanced headers detected")
                    print(f"   📊 Candidates found: {len(result.get('candidates', []))}")
                    
            except Exception as e:
                print(f"   💥 Detection error: {e}")

def test_openai_integration(detector: EnhancedHeaderDetector):
    """Test OpenAI integration specifically."""
    
    print("\n" + "="*80)
    print("🤖 TESTING OPENAI INTEGRATION")
    print("="*80)
    
    if not detector.openai_client:
        print("❌ OpenAI client not available")
        return
    
    print("✅ OpenAI client is available")
    
    # Test with a simple example
    test_data = {
        'columns': ['col_0', 'col_1', 'col_2'],
        'data': [
            {'col_0': 'Lane ID', 'col_1': 'Origin Port', 'col_2': 'Destination Port'},
            {'col_0': 'ASIA_US_001', 'col_1': 'Shanghai', 'col_2': 'Los Angeles'},
            {'col_0': 'ASIA_US_002', 'col_1': 'Ningbo', 'col_2': 'Long Beach'}
        ]
    }
    
    print("\n📋 Testing with sample logistics data:")
    print(f"   Current headers: {test_data['columns']}")
    print(f"   Row 1 data: {[test_data['data'][0][col] for col in test_data['columns']]}")
    
    try:
        result = detector.detect_headers_enhanced(test_data, "test_sample.json")
        
        openai_validation = result.get('openai_validation', {})
        if openai_validation:
            print(f"\n🤖 OpenAI Analysis:")
            print(f"   Decision: {openai_validation.get('decision', 'N/A')}")
            print(f"   Confidence: {openai_validation.get('confidence', 'N/A')}")
            print(f"   Reasoning: {openai_validation.get('reasoning', 'N/A')}")
            
            final_mapping = result.get('final_mapping', {})
            if final_mapping:
                print(f"   Suggested mappings:")
                for col, header in list(final_mapping.items())[:3]:
                    print(f"      {col}: {header}")
        else:
            print("⚠️ No OpenAI validation result")
            
    except Exception as e:
        print(f"💥 OpenAI test error: {e}")

def show_decision_history(detector: EnhancedHeaderDetector):
    """Show the current decision history for learning analysis."""
    
    print("\n" + "="*80)
    print("📚 DECISION HISTORY ANALYSIS")
    print("="*80)
    
    history = detector.decision_history
    metadata = history.get('metadata', {})
    decisions = history.get('decisions', {})
    
    print(f"📊 Total decisions recorded: {metadata.get('total_decisions', 0)}")
    print(f"📅 History created: {metadata.get('created', 'N/A')}")
    
    if decisions:
        print(f"\n🔍 Recent decisions ({len(decisions)} total):")
        recent = list(decisions.items())[-3:]  # Show last 3
        for key, decision in recent:
            print(f"   • {key}: {decision.get('decision', 'N/A')} (confidence: {decision.get('confidence', 'N/A')})")
    else:
        print("📝 No decisions recorded yet")

def main():
    """Main test function."""
    
    print("🚀 Enhanced Header Detection System Test")
    print("="*50)
    
    # Initialize detector
    print("🔧 Initializing enhanced header detector...")
    detector = EnhancedHeaderDetector()
    
    # Check OpenAI availability
    if detector.openai_client:
        print("✅ OpenAI integration: ENABLED")
    else:
        print("⚠️ OpenAI integration: DISABLED (API key missing or invalid)")
    
    # Load sample files
    print("\n📁 Loading sample files...")
    sample_files = load_sample_files(limit=2)  # Test with 2 files
    
    if not sample_files:
        print("❌ No sample files loaded. Exiting.")
        return
    
    # Test detection strategies
    test_detection_strategies(detector, sample_files)
    
    # Test OpenAI integration specifically
    test_openai_integration(detector)
    
    # Show decision history
    show_decision_history(detector)
    
    print("\n" + "="*80)
    print("✅ TESTING COMPLETE")
    print("="*80)
    
    # Save any new decisions
    detector.save_decision_history()
    print("💾 Decision history saved")

if __name__ == "__main__":
    main()
