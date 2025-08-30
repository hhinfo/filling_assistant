#!/usr/bin/env python3
"""
Test Enhanced Header Detection Integration in CLI Workflow
=========================================================
"""

import sys
import os

# Add the parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from filing_assistant.io_utils import load_json, detect_header_row, detect_header_row_enhanced

def test_basic_integration():
    """Test basic integration without OpenAI calls."""
    
    print("🧪 Testing Enhanced Header Detection Integration")
    print("=" * 60)
    
    # Load a sample file
    test_file = "training_files2/(AppliedMat) External CPT Empty_structured.json"
    
    if not os.path.exists(test_file):
        print("❌ Test file not found")
        return
    
    try:
        data = load_json(test_file)
        print(f"✅ Loaded file: {test_file}")
        
        # Test first sheet
        sheet_name = list(data.keys())[0]
        sheet_data = data[sheet_name]
        
        print(f"\n📋 Testing sheet: {sheet_name}")
        print(f"📊 Columns: {len(sheet_data.get('columns', []))}")
        
        # Test standard header detection
        print(f"\n🔍 Standard Header Detection:")
        headers_std, idx_std = detect_header_row(sheet_data)
        print(f"   Headers found: {len(headers_std)}")
        print(f"   Sample headers: {headers_std[:5]}")
        
        # Test enhanced header detection
        print(f"\n🚀 Enhanced Header Detection:")
        try:
            headers_enh, idx_enh, enhancement_info = detect_header_row_enhanced(sheet_data, test_file)
            print(f"   Enhanced: {enhancement_info.get('enhanced', False)}")
            print(f"   Headers found: {len(headers_enh)}")
            print(f"   Sample headers: {headers_enh[:5]}")
            
            if enhancement_info.get('enhanced'):
                confidence = enhancement_info.get('confidence', 0)
                print(f"   🎯 Confidence: {confidence:.1%}")
            else:
                reason = enhancement_info.get('reason', 'Unknown')
                print(f"   ⚠️ Reason: {reason}")
                
        except Exception as e:
            print(f"   ❌ Enhanced detection failed: {e}")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")

def test_cli_flags():
    """Test CLI flag availability."""
    
    print(f"\n🔧 Testing CLI Integration")
    print("=" * 40)
    
    # Import CLI module
    try:
        from filing_assistant.cli import app
        print("✅ CLI module imported successfully")
        
        # Check if enhanced_headers flag is available
        import inspect
        
        # Get the identify command
        for command in app.registered_commands.values():
            if hasattr(command, 'callback') and command.callback.__name__ == 'identify':
                sig = inspect.signature(command.callback)
                params = list(sig.parameters.keys())
                
                if 'enhanced_headers' in params:
                    print("✅ Enhanced headers flag available in identify command")
                else:
                    print("❌ Enhanced headers flag missing from identify command")
                    print(f"   Available parameters: {params}")
                break
        else:
            print("❌ Identify command not found")
            
    except Exception as e:
        print(f"❌ CLI integration test failed: {e}")

def main():
    """Main test function."""
    
    print("🚀 Enhanced Header Detection - Integration Test")
    print("=" * 60)
    
    # Test basic integration
    test_basic_integration()
    
    # Test CLI flags
    test_cli_flags()
    
    print(f"\n" + "=" * 60)
    print("✅ Integration Test Complete")

if __name__ == "__main__":
    main()
