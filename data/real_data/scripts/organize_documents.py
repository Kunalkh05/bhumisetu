#!/usr/bin/env python3
"""
BHUMISETU Real Land Acquisition Document Organizer
Consolidates and organizes all 344 downloaded government PDFs into a single,
easily searchable tracking folder (data/real_data/all_documents/) using APFS hardlinks.
Generates:
1. data/real_data/all_documents/<clean_descriptive_filename>.pdf
2. data/real_data/all_documents/TRACKER.csv
3. data/real_data/all_documents/INDEX.md
"""

import os
import re
import csv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_DIR = os.path.join(BASE_DIR, "all_documents")
RAW_DOCS_DIR = os.path.join(BASE_DIR, "raw_documents")
MANIFEST_PATH = os.path.join(BASE_DIR, "source_manifest.csv")
EVENTS_PATH = os.path.join(BASE_DIR, "real_land_acquisition_events.csv")
CASES_PATH = os.path.join(BASE_DIR, "real_land_acquisition_cases.csv")

os.makedirs(TARGET_DIR, exist_ok=True)

# Load manifest and events
with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
    manifest_rows = list(csv.DictReader(f))

with open(EVENTS_PATH, "r", encoding="utf-8") as f:
    events_rows = list(csv.DictReader(f))

events_by_source = {e['source_id']: e for e in events_rows}

def sanitize(s, max_len=25):
    if not s:
        return ""
    clean = re.sub(r'[^A-Za-z0-9]', '_', str(s))
    clean = re.sub(r'_+', '_', clean).strip('_')
    return clean[:max_len]

tracker_records = []

for idx, m in enumerate(manifest_rows, 1):
    src_id = m['source_id']
    dist = m['source_district'].upper()
    ev = events_by_source.get(src_id, {})
    
    stage = ev.get('event_type', 'DOC')
    stage_abbr = {
        'SECTION_11': 'SEC11',
        'SECTION_19': 'SEC19',
        'SECTION_21': 'SEC21',
        'AWARD': 'AWARD',
        'EXTENSION': 'EXTENSION',
        'DIRECT_PURCHASE': 'DIR_PURCHASE',
        'GENERAL_NOTICE': 'NOTICE'
    }.get(stage, 'DOC')

    vil = sanitize(ev.get('village', ''), 20)
    case_num = sanitize(ev.get('case_number', ''), 25)
    prj = sanitize(ev.get('project_name', ''), 20)
    
    # Meaningful descriptive filename
    parts = [dist, f"{idx:03d}", stage_abbr]
    if prj and prj != "UNSPECIFIED":
        parts.append(prj)
    if vil and vil != "UNSPECIFIED":
        parts.append(vil)
    if case_num and case_num != "UNSPECIFIED":
        parts.append(case_num)
    
    clean_filename = "__".join(parts) + ".pdf"
    
    # Source path
    src_path = os.path.join(BASE_DIR, m['local_file_path'])
    dest_path = os.path.join(TARGET_DIR, clean_filename)
    
    # Link file (use hardlink to avoid copying 915 MB)
    if os.path.exists(dest_path):
        os.remove(dest_path)
    
    if os.path.exists(src_path):
        try:
            os.link(src_path, dest_path)
        except OSError:
            # Fallback to copy if hardlink fails across filesystems
            import shutil
            shutil.copy2(src_path, dest_path)
            
    file_size_mb = round(int(m['file_size_bytes']) / (1024 * 1024), 2)
    
    tracker_records.append({
        'index': idx,
        'organized_file': clean_filename,
        'source_id': src_id,
        'district': m['source_district'],
        'stage': stage,
        'stage_abbr': stage_abbr,
        'village': ev.get('village', '') or 'N/A',
        'taluka': ev.get('taluka', '') or 'N/A',
        'case_number': ev.get('case_number', '') or 'N/A',
        'project_name': ev.get('project_name', '') or 'N/A',
        'publication_date': m['source_publication_date'],
        'file_size_mb': file_size_mb,
        'sha256_hash': m['sha256_hash'],
        'source_url': m['source_pdf_url'],
        'original_local_path': m['local_file_path']
    })

# Write TRACKER.csv
tracker_csv = os.path.join(TARGET_DIR, "TRACKER.csv")
with open(tracker_csv, "w", newline="", encoding="utf-8") as f:
    fields = [
        'index', 'organized_file', 'source_id', 'district', 'stage', 'stage_abbr',
        'village', 'taluka', 'case_number', 'project_name', 'publication_date',
        'file_size_mb', 'sha256_hash', 'source_url', 'original_local_path'
    ]
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(tracker_records)

# Also place a copy at data/real_data/DOCUMENT_TRACKER.csv
root_tracker_csv = os.path.join(BASE_DIR, "DOCUMENT_TRACKER.csv")
with open(root_tracker_csv, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(tracker_records)

# Write INDEX.md
index_md = os.path.join(TARGET_DIR, "INDEX.md")
with open(index_md, "w", encoding="utf-8") as f:
    f.write("# BHUMISETU Real Government Land Acquisition Documents Catalog\n\n")
    f.write(f"**Total Verified Government Documents**: {len(tracker_records)}\n\n")
    f.write("All original official PDF notices and awards from Maharashtra Collectorate Portals organized into a single directory.\n\n")
    f.write("| Index | District | Stage | Case / Notice Details | Village / Project | Date | Size | Local File (Click to Open) | Official S3WaaS Source |\n")
    f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
    for r in tracker_records:
        details = r['case_number'] if r['case_number'] != 'N/A' else r['source_id']
        loc_prj = f"{r['village']} ({r['project_name']})" if r['project_name'] != 'N/A' else r['village']
        abs_file_path = os.path.join(TARGET_DIR, r['organized_file'])
        f.write(f"| {r['index']} | **{r['district']}** | `{r['stage_abbr']}` | {details} | {loc_prj} | {r['publication_date']} | {r['file_size_mb']} MB | [📄 {r['organized_file']}](file://{abs_file_path}) | [🌐 Official Notice ↗]({r['source_url']}) |\n")

print(f"Successfully organized {len(tracker_records)} files into {TARGET_DIR}")
print(f"Generated tracker: {tracker_csv}")
print(f"Generated markdown index: {index_md}")
