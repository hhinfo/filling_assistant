#!/usr/bin/env python3
"""
Script to split training_files2 into 70% training and 30% test sets
Ensures balanced distribution across different companies and file types
"""

import os
import random
import shutil
from pathlib import Path
from collections import defaultdict

def main():
    # Set random seed for reproducible splits
    random.seed(42)
    
    # Paths
    source_dir = Path("training_files2")
    train_dir = Path("train_set")
    test_dir = Path("test_set")
    
    # Create output directories
    train_dir.mkdir(exist_ok=True)
    test_dir.mkdir(exist_ok=True)
    
    # Get all structured.json files (these are the ones we train on)
    json_files = list(source_dir.glob("*_structured.json"))
    
    # Group files by company/type to ensure balanced split
    company_groups = defaultdict(list)
    for file in json_files:
        # Extract company name from filename
        name = file.name
        if name.startswith("(") and ")" in name:
            company = name.split(")")[0] + ")"
        elif name.startswith("4."):
            company = "filled_files"
        elif name.startswith("1."):
            company = "empty_files"
        else:
            company = "other"
        
        company_groups[company].append(file)
    
    # Split each company group 70/30
    train_files = []
    test_files = []
    
    print("📊 Splitting files by company/type:")
    for company, files in company_groups.items():
        random.shuffle(files)  # Shuffle within each group
        
        split_point = int(len(files) * 0.7)
        company_train = files[:split_point]
        company_test = files[split_point:]
        
        train_files.extend(company_train)
        test_files.extend(company_test)
        
        print(f"  {company}: {len(company_train)} train, {len(company_test)} test")
    
    # Copy files to respective directories
    print(f"\n📁 Copying {len(train_files)} files to train_set/")
    for file in train_files:
        shutil.copy2(file, train_dir / file.name)
    
    print(f"📁 Copying {len(test_files)} files to test_set/")
    for file in test_files:
        shutil.copy2(file, test_dir / file.name)
    
    # Summary
    total_files = len(train_files) + len(test_files)
    train_percent = len(train_files) / total_files * 100
    test_percent = len(test_files) / total_files * 100
    
    print(f"\n✅ Split completed:")
    print(f"   Training set: {len(train_files)} files ({train_percent:.1f}%)")
    print(f"   Test set: {len(test_files)} files ({test_percent:.1f}%)")
    print(f"   Total: {total_files} files")

if __name__ == "__main__":
    main()
