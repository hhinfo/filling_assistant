# Filing Assistant Usage Examples

This document provides practical examples for using Filing Assistant's training and identification system.

## Training Examples

### Auto-Detection Training (Recommended)
Process all sheets automatically:
```bash
python -m filing_assistant.cli train \
  --data-dir "training_files2" \
  --out-store "patterns_stores/comprehensive_patterns.json" \
  --verbose
```

### Single Sheet Training (Legacy)
Train on specific sheet only:
```bash
python -m filing_assistant.cli train \
  --data-dir "training_files2" \
  --sheet "Bid Sheet" \
  --out-store "patterns_stores/bid_sheet_only.json" \
  --verbose
```

## Identification Examples

### Auto-Detection Identification (Recommended)
Identify columns in all relevant sheets:
```bash
python -m filing_assistant.cli identify \
  --file "training_files2/(Logitech 2025) External CPT Empty_structured.json" \
  --store "patterns_stores/Patterns_store_autodetect.json" \
  --verbose
```

### Save Results to File
```bash
python -m filing_assistant.cli identify \
  --file "training_files2/(Illumina) External CPT Empty_structured.json" \
  --store "patterns_stores/Patterns_store_autodetect.json" \
  --out "results/illumina_identification.json" \
  --verbose
```

### Custom Confidence Threshold
Only accept columns with 85% confidence or higher:
```bash
python -m filing_assistant.cli identify \
  --file "new_empty_file.json" \
  --store "patterns_stores/my_patterns.json" \
  --threshold 0.85 \
  --verbose
```

### Single Sheet Identification
Process only a specific sheet:
```bash
python -m filing_assistant.cli identify \
  --file "new_empty_file.json" \
  --sheet "Rate Card" \
  --store "patterns_stores/my_patterns.json" \
  --verbose
```

## Update Pattern Store Examples

### Simple Corrections
Update with basic column corrections:
```bash
python -m filing_assistant.cli update \
  --store "patterns_stores/my_patterns.json" \
  --user-labels "examples/corrections_simple.json"
```

### Multi-Sheet Corrections
Update with corrections across multiple sheets:
```bash
python -m filing_assistant.cli update \
  --store "patterns_stores/comprehensive_patterns.json" \
  --user-labels "examples/corrections_multi_sheet.json"
```

## Batch Processing Examples

### Train Multiple Pattern Stores
Create specialized pattern stores for different use cases:
```bash
# General purpose patterns
python -m filing_assistant.cli train \
  --data-dir "training_files2" \
  --out-store "patterns_stores/general_patterns.json"

# Air freight specific
python -m filing_assistant.cli train \
  --data-dir "air_freight_files" \
  --out-store "patterns_stores/air_freight_patterns.json"

# Sea freight specific  
python -m filing_assistant.cli train \
  --data-dir "sea_freight_files" \
  --out-store "patterns_stores/sea_freight_patterns.json"
```

### Process Multiple Files
Identify columns in multiple files:
```bash
# Create results directory
mkdir -p results

# Process each file
for file in new_files/*.json; do
  basename=$(basename "$file" .json)
  python -m filing_assistant.cli identify \
    --file "$file" \
    --store "patterns_stores/comprehensive_patterns.json" \
    --out "results/${basename}_identification.json" \
    --verbose
done
```

## Development and Testing Examples

### Mock Mode for Development
Use mock verification for consistent results:
```bash
export FA_MOCK_OPENAI=true
python -m filing_assistant.cli train \
  --data-dir "test_files" \
  --out-store "patterns_stores/test_patterns.json" \
  --verbose
```

### OpenAI Mode for Production
Use real OpenAI verification:
```bash
export FA_MOCK_OPENAI=false
export OPENAI_API_KEY=sk-your-key-here
python -m filing_assistant.cli train \
  --data-dir "production_files" \
  --out-store "patterns_stores/production_patterns.json" \
  --verbose
```

## Expected Output Examples

### Training Output
```
🚀 Filing Assistant Training — Auto-Detection Mode
📁 Training directory: training_files2
📊 Processing files: 140 files found

🔄 Phase 1: File Pairing Analysis
📋 Found 70 file pairs (140 files total)
✅ Pairing success rate: 83.3%

🔄 Phase 2: Sheet Detection & Pattern Learning
📋 Processing pair 1/70: (ACCO) External CPT
  📄 Empty: 1 sheets detected
  📄 Filled: 1 sheets detected  
  ✅ Learned 0 fillable columns

📋 Processing pair 2/70: (Logitech 2025) External CPT
  📄 Empty: 2 sheets detected (ReferenceData, Bid Sheet)
  📄 Filled: 2 sheets detected (ReferenceData, Bid Sheet)
  ✅ Learned 37 fillable columns

🎉 Training completed successfully!
📊 Total: 65 sheets, 275 fillable columns
```

### Identification Output  
```
🔍 Identifying fillable columns in: new_file.json
📋 Auto-detecting all sheets
📊 Confidence threshold: 0.7

                         Columns to Fill — Bid Sheet                          
┏━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Pos ┃ Header                            ┃ Label                   ┃ Conf ┃ Method       ┃ Decision ┃
┡━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│   1 │ lot id                            │ lot_id                  │ 0.95 │ mock-exact   │ fill     │
│   2 │ mode                              │ mode                    │ 0.95 │ mock-exact   │ fill     │
│  24 │ all in charge (usd)*              │ all_in_charge_usd       │ 0.90 │ mock-variant │ fill     │
└─────┴───────────────────────────────────┴─────────────────────────┴──────┴──────────────┴──────────┘

📊 Summary:
  Sheets processed: 2
  Fillable columns: 37
  Unknown columns: 0
```

## Error Handling Examples

### No Matching Sheets
```bash
$ python -m filing_assistant.cli identify --file "incompatible_file.json" --store "patterns.json"
❌ Error: No matching sheets found
Available sheets in file: Sheet1, Data  
Learned sheets in patterns: Bid Sheet, Rate Card
```

### Missing Files
```bash
$ python -m filing_assistant.cli identify --file "nonexistent.json" --store "patterns.json"  
❌ Error: FileNotFoundError: [Errno 2] No such file or directory: 'nonexistent.json'
```

### Low File Pairing Rate
```bash
$ python -m filing_assistant.cli train --data-dir "messy_files" --verbose
⚠️  Warning: Low pairing rate detected (45.2%)
💡 Suggestion: Ensure filenames contain 'Empty' and 'Filled' consistently
```

## Performance Tuning Examples

### High Confidence Mode
Only process columns with very high confidence:
```bash
python -m filing_assistant.cli identify \
  --file "critical_file.json" \
  --store "patterns.json" \
  --threshold 0.9
```

### Fast Processing Mode
Skip verbose output for batch processing:
```bash
python -m filing_assistant.cli identify \
  --file "file.json" \
  --store "patterns.json" \
  --out "result.json"
```

### Debug Mode
Maximum verbosity for troubleshooting:
```bash
python -m filing_assistant.cli train \
  --data-dir "problem_files" \
  --out-store "debug_patterns.json" \
  --verbose
```

## Integration Examples

### CI/CD Pipeline
```bash
#!/bin/bash
# Continuous training pipeline
set -e

# Download latest training files
aws s3 sync s3://training-bucket/ training_files/

# Train with mock mode for consistency
export FA_MOCK_OPENAI=true
python -m filing_assistant.cli train \
  --data-dir "training_files" \
  --out-store "patterns_stores/ci_patterns.json" \
  --verbose

# Upload patterns to production
aws s3 cp patterns_stores/ci_patterns.json s3://production-bucket/
```

### API Integration
```python
import subprocess
import json

def identify_columns(file_path, store_path):
    """Identify columns using Filing Assistant CLI"""
    result = subprocess.run([
        'python', '-m', 'filing_assistant.cli', 'identify',
        '--file', file_path,
        '--store', store_path,
        '--out', 'temp_result.json'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        with open('temp_result.json', 'r') as f:
            return json.load(f)
    else:
        raise Exception(f"Identification failed: {result.stderr}")
```
