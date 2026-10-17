#!/usr/bin/env python3
"""
Review of Alpha Research Project Status

This script analyzes all alpha signals in the alpha_research/ project to identify:
- Which alphas have real data files
- Which alphas are marked "active" but may be incomplete
- Issues that need fixing
"""

import os
import pandas as pd

def analyze_alpha_project():
    base_dir = "/Users/znding04/Work/alpha_research"
    
    print("🔍 ALPHA RESEARCH PROJECT REVIEW")
    print("=" * 50)
    
    # Check all alpha folders
    alpha_folders = []
    for item in os.listdir(base_dir):
        if item.startswith("alpha_") and os.path.isdir(os.path.join(base_dir, item)):
            alpha_folders.append(item)
    
    print(f"\n📁 Total alpha signals: {len(alpha_folders)}")
    
    # Analyze each alpha
    review = []
    for alpha_folder in sorted(alpha_folders):
        folder_path = os.path.join(base_dir, alpha_folder)
        
        # Check for main.py
        main_file = os.path.join(folder_path, "main.py")
        notes_file = os.path.join(folder_path, "notes.md")
        
        # Check for data files
        data_dir = os.path.join(base_dir, "data")
        related_data_files = []
        if os.path.exists(data_dir):
            for f in os.listdir(data_dir):
                if f.startswith(alpha_folder.split('_')[-1][:2]):  # match alpha XX
                    related_data_files.append(f)
        
        # Determine status
        status = "✅ Active" if len(related_data_files) > 0 else "❌ Incomplete"
        
        review.append({
            'folder': alpha_folder,
            'status': status,
            'has_main': os.path.exists(main_file),
            'has_notes': os.path.exists(notes_file),
            'data_files': related_data_files,
            'issues': []
        })
    
    # Print summary
    print("\n📊 ALPHA SIGNAL STATUS:")
    for r in review:
        status_icon = "✅" if "Active" in r['status'] else "❌"
        print(f"{status_icon} {r['folder']:20} | Status: {r['status']:10} | Data: {len(r['data_files']):2} files")
    
    # Identify problematic alphas
    incomplete = [r for r in review if "❌" in r['status']]
    if incomplete:
        print(f"\n⚠️  INCOMPLETE ALPHAS ({len(incomplete)}):")
        for inc in incomplete:
            print(f"   • {inc['folder']}")
            if not inc['has_main']:
                print("     ⚠️  Missing main.py")
            if not inc['has_notes']:
                print("     ⚠️  Missing notes.md")
    
    # Check specific problematic alphas based on the status in README
    print("\n🔍 STATUS CHECK (per README):")
    active_but_no_data = []
    for r in review:
        folder_name = r['folder']
        if folder_name.startswith('alpha_05'):
            print(f"   {folder_name}: Looking for _25d or similar in data files...")
            if not any('25d' in f for f in r['data_files']):
                active_but_no_data.append(folder_name)
    
    if active_but_no_data:
        print(f"\n⚠️  POTENTIAL ISSUE: {len(active_but_no_data)} alphas marked 'active' but may lack proper naming in data files:")
        for f in active_but_no_data:
            print(f"   • {f}")
    
    print("\n📋 NEXT STEPS:")
    print("   1. Fix any alphas marked incomplete (add missing files)")
    print("   2. Ensure active alphas have proper data file naming")
    print("   3. Run QC test on data files (check CSV structure)")
    print("   4. Update README if status changes")
    
    return review

if __name__ == "__main__":
    analyze_alpha_project()
