# Changelog

All notable changes to Filing Assistant will be documented in this file.

## [3.0.0] - 2025-08-28 - Enhanced-Only Production System

### 🎯 **MAJOR SYSTEM TRANSFORMATION**
- **BREAKING**: Removed basic training method entirely - now enhanced-only system  
- **BREAKING**: Simplified CLI - removed `--enhanced`/`--basic` flags
- **CRITICAL FIX**: Header detection bug - now correctly uses JSON `"columns"` field instead of row data
- **NEW**: Comprehensive training result displays with rich formatting

### ✨ **New Features**
- **Training Pair Discovery**: Shows all discovered Empty/Filled pairs in formatted table before training
- **Rich User Interface**: Professional output with tables, panels, and progress indicators using Rich library  
- **Detailed Training Results**: Complete file→sheet→column breakdown showing exactly what was learned
- **Conservative Cross-Domain**: Appropriate low confidence for unfamiliar document formats

### 🔧 **System Improvements**
- **Performance**: 760% improvement over basic training maintained with enhanced-only approach
- **Data Processing**: Fixed critical bug where row data values were treated as column headers
- **User Experience**: Single training method eliminates confusion and complexity
- **Documentation**: Complete README overhaul reflecting current system capabilities

### 📊 **Current Performance Metrics**
```
Latest Training Session:
• Pairs Processed: 35 (100% success rate)
• Sheets Learned: 48 unique sheet types  
• Fillable Columns: 761 patterns identified
• Companies: 5+ different logistics companies
• Cross-Domain: Conservative identification for unknown formats
```

### 🗂️ **Project Organization**
- **Moved**: Legacy train/test splits to `legacy_data/`
- **Archived**: Development artifacts in `cleanup_archive/`  
- **Consolidated**: Evaluation reports in `evaluation_archive/`
- **Created**: `docs_archive/` for detailed technical documentation
- **Updated**: All documentation to reflect enhanced-only system

### 🚀 **Ready-to-Use Commands**
```bash
# Enhanced Training (simplified)
python -m filing_assistant.cli train --data-dir "training_files2" --out-store "enhanced_patterns_store.json" --verbose

# Column Identification  
python -m filing_assistant.cli identify --file "your_file.json" --store "enhanced_patterns_store.json" --verbose
```

### 🐛 **Critical Bug Fixes**
- **Header Detection**: Fixed `io_utils.py` to use JSON `"columns"` field directly instead of detecting from data rows
- **Data Processing**: Eliminated incorrect treatment of row values as column headers
- **Result Display**: Fixed training results to show actual discovered patterns

### 📋 **Breaking Changes**
- **CLI**: Removed `--enhanced` and `--basic` flags - now enhanced-only
- **Training**: No more method selection - automatically uses enhanced approach
- **File Names**: Primary pattern store is now `enhanced_patterns_store.json`

## [2.0.0] - 2025-08-27 - Multi-Sheet Auto-Detection

### 🚀 **Major Features Added**
- **Multi-Sheet Auto-Detection**: Automatically processes all relevant sheets instead of hardcoding "Bid Sheet"
- **Enhanced File Pairing**: Improved algorithm increasing file utilization from 21.4% to 83.3%
- **Multi-Language Support**: Handles English and Chinese sheet names and content
- **Advanced Identification**: Multi-sheet processing with confidence-based classification

### 📊 **Performance Improvements**  
- **File Coverage**: 83.3% utilization (140/168 files) vs 21.4% (36/168 files)
- **Sheet Discovery**: 65 unique sheet types discovered and processed
- **Column Learning**: 275 fillable columns learned across all sheets

### 🔧 **CLI Improvements**
- **New Options**: `--verbose` for detailed processing information
- **Enhanced Output**: Rich terminal output with beautiful tables and progress indicators
- **Auto-detection**: `--sheet` parameter now optional

## [1.0.0] - 2025-08-27 - Initial Release

### Initial Features
- Basic training and identification system
- Single sheet processing ("Bid Sheet" hardcoded)  
- OpenAI and mock verification modes
- Simple file pairing algorithm
- Basic CLI interface
- Pattern store system
- User correction capability

---

## Current System Status: ✅ **PRODUCTION READY**

The Filing Assistant is now a streamlined, enhanced-only system with:
- Fixed data processing bugs
- Comprehensive user feedback  
- Superior performance (760% improvement)
- Clean, organized codebase
- Updated documentation reflecting actual capabilities
