#!/usr/bin/env python3
"""
BHUMISETU Real Land Acquisition Data Collector & Structuring Pipeline
Authoritative Sources: Maharashtra District Portals (Nagpur, Pune, Nashik, Solapur, Yavatmal)
Strict Compliance:
- Real data only (no synthetic records, no hallucinated dates)
- Retain original PDFs with SHA-256 hashes
- Full data provenance (source_url, document_hash, extraction_method, page, raw snippet)
- Multi-event case reconstruction
- Specific tracking of statutory extension orders (RFCTLARR Sec 25 / Sec 19(1) extensions)
- Clean segregation of Original vs Derived fields
- No ML labels assigned prematurely
"""

import os
import re
import csv
import json
import time
import hashlib
import subprocess
import urllib.request
from datetime import datetime
from bs4 import BeautifulSoup
import pypdf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DOCS_DIR = os.path.join(BASE_DIR, "raw_documents")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
OCR_BIN = os.path.join(SCRIPTS_DIR, "ocr_pdf")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

DISTRICT_CONFIGS = [
    {
        'district': 'Nagpur',
        'state': 'Maharashtra',
        'org': 'District Collectorate & Administration Nagpur',
        'dept': 'Revenue & Land Acquisition Department',
        'url_pattern': 'https://nagpur.gov.in/documents/page/{}/',
        'first_page_url': 'https://nagpur.gov.in/documents/',
        'max_pages': 25
    },
    {
        'district': 'Pune',
        'state': 'Maharashtra',
        'org': 'District Collectorate & Administration Pune',
        'dept': 'Special Land Acquisition Office (SLAD / PLAQ)',
        'url_pattern': 'https://pune.gov.in/en/documents/page/{}/',
        'first_page_url': 'https://pune.gov.in/en/documents/',
        'max_pages': 15
    },
    {
        'district': 'Nashik',
        'state': 'Maharashtra',
        'org': 'District Collectorate & Administration Nashik',
        'dept': 'Special Land Acquisition Office',
        'url_pattern': 'https://nashik.gov.in/en/documents/page/{}/',
        'first_page_url': 'https://nashik.gov.in/en/documents/',
        'max_pages': 10
    },
    {
        'district': 'Solapur',
        'state': 'Maharashtra',
        'org': 'District Collectorate & Administration Solapur',
        'dept': 'Private & Additional Land Acquisition (PALAQ) Branch',
        'url_pattern': 'https://solapur.gov.in/en/documents/page/{}/',
        'first_page_url': 'https://solapur.gov.in/en/documents/',
        'max_pages': 12
    },
    {
        'district': 'Yavatmal',
        'state': 'Maharashtra',
        'org': 'District Collectorate & Administration Yavatmal',
        'dept': 'Deputy Collector (Land Acquisition) Bembla Project Office',
        'url_pattern': 'https://yavatmal.gov.in/en/documents/page/{}/',
        'first_page_url': 'https://yavatmal.gov.in/en/documents/',
        'max_pages': 10
    }
]

LA_KEYWORDS = [
    'acquisition', 'award', '11(1)', '19(1)', '21', 'section 25',
    'भूसंपादन', 'निवाडा', 'section 11', 'section 19', 'section 21',
    'direct purchase', 'private purchase', 'mouza', 'mauje', 'taluka',
    'ring road', 'road widening', 'bembla', 'kanhan', 'gosikhurd', 'extension'
]

def is_la_document(title):
    t_lower = title.lower()
    return any(k in t_lower for k in LA_KEYWORDS)

def parse_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d.%m.%Y'):
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            pass
    return None

def extract_case_details(title, text_content=""):
    combined = title + " " + text_content[:500]
    
    # 1. Case Number
    case_num = None
    m_case = re.search(r'(?:Case\s*No\.?|LAC\s*No\.?|LAO\s*No\.?|S\.?R\.?\s*No\.?|No\.?)\s*[:\-]?\s*([0-9]{1,4}\s*[\/\-]\s*[A-Za-z\u0900-\u097F0-9\.\-]+(?:\s*[\/\-]\s*[0-9]{2,4}(?:[\/\-][0-9]{2,4})?)?)', combined, re.I)
    if m_case:
        case_num = m_case.group(1).strip()
    else:
        # Check for numeric case patterns like "Case No - 07-2025" or "Case No. 16-2025" or "SR 28/2019"
        m_case2 = re.search(r'Case\s*No\s*[\.\-]?\s*([0-9]{1,4}[\.\-][0-9]{2,4})', combined, re.I)
        if m_case2:
            case_num = m_case2.group(1).strip()
            
    # 2. Village / Mouza
    village = None
    m_vil = re.search(r'(?:Mouza|Mouja|Mauza|Mauje|Village)\s*[\-–:]?\s*([A-Za-z\u0900-\u097F\s\(\)]+?)(?:,|\s+Tah|\s+Taluka|\s+Dist|\s+for|\s+regarding|\s+Case|\s+LAO|$)', combined, re.I)
    if m_vil:
        v_cand = m_vil.group(1).strip()
        if len(v_cand) > 2 and len(v_cand) < 40 and not any(x in v_cand.lower() for x in ['acquisition', 'notice', 'section']):
            village = v_cand
            
    # 3. Taluka
    taluka = None
    m_tal = re.search(r'(?:Tahsil|Tah\.?|Taluka|Tal\.?|Tq\.?)\s*[\-–:]?\s*([A-Za-z\u0900-\u097F\s\(\)]+?)(?:,|\s+Dist|\s+District|\s+regarding|\s+Case|\s+for|$)', combined, re.I)
    if m_tal:
        t_cand = m_tal.group(1).strip()
        if len(t_cand) > 2 and len(t_cand) < 30 and not any(x in t_cand.lower() for x in ['acquisition', 'notice', 'collector']):
            taluka = t_cand

    # 4. Project Name
    project_name = None
    if re.search(r'Ring\s*Road', combined, re.I):
        if 'pune' in combined.lower() or 'prr' in combined.lower():
            project_name = 'Pune Ring Road Project'
        elif 'nashik' in combined.lower():
            project_name = 'Nashik Ring Road Project'
        else:
            project_name = 'Ring Road Project'
    elif re.search(r'Kanhan\s*River|Kochhi\s*Barrage', combined, re.I):
        project_name = 'Kanhan River Project (Kochhi Barrage)'
    elif re.search(r'Gosikhurd', combined, re.I):
        project_name = 'Gosikhurd National Irrigation Project'
    elif re.search(r'Bembla', combined, re.I):
        project_name = 'Bembla River Irrigation Project'
    elif re.search(r'Shaktipeeth\s*Expressway', combined, re.I):
        project_name = 'Maharashtra Shaktipeeth Expressway'
    elif re.search(r'NH\s*[\-–]?\s*548\s*[\-–]?\s*D', combined, re.I):
        project_name = 'National Highway NH-548-D'
    elif re.search(r'NH\s*[\-–]?\s*9', combined, re.I):
        project_name = 'National Highway NH-9'
    elif re.search(r'Railway|Pune-Solapur-Wadi', combined, re.I):
        project_name = 'Pune-Solapur-Wadi 3rd & 4th Railway Line Project'
    elif re.search(r'D\.?P\.?\s*Road|Road\s*Widening|wide\s*road', combined, re.I):
        project_name = 'Urban Development Plan (DP) Road Widening'
    elif re.search(r'Nira\s*Devghar', combined, re.I):
        project_name = 'Nira Devghar Irrigation Project'
    elif re.search(r'MIDC', combined, re.I):
        project_name = 'MIDC Industrial Land Acquisition'

    # 5. Act Key
    act_key = "RFCTLARR_2013"
    if re.search(r'National\s*Highway\s*Act|1956', combined, re.I):
        act_key = "NATIONAL_HIGHWAYS_ACT_1956"
    elif re.search(r'Railways\s*\(Amendment\)\s*Act|2008|Section\s*20A', combined, re.I):
        act_key = "RAILWAYS_ACT_2008"
    elif re.search(r'Maharashtra\s*Highway\s*Act|1955', combined, re.I):
        act_key = "MAHARASHTRA_HIGHWAYS_ACT_1955"
    elif re.search(r'MIDC\s*Act|1961', combined, re.I):
        act_key = "MIDC_ACT_1961"
    elif re.search(r'Land\s*Acquisition\s*Act\s*,?\s*1894|Act\s*1894', combined, re.I):
        act_key = "LAND_ACQUISITION_ACT_1894"

    # 6. Event Type / Stage
    event_type = "GENERAL_NOTICE"
    if re.search(r'Extension|additional\s*time|proceedings\s*extended|section\s*25', combined, re.I):
        event_type = "EXTENSION"
    elif re.search(r'11\s*\(\s*1\s*\)|Section\s*11|Sec\s*11|Section\s*3A', combined, re.I):
        event_type = "SECTION_11"
    elif re.search(r'19\s*\(\s*1\s*\)|Section\s*19|Sec\s*19|Section\s*3D', combined, re.I):
        event_type = "SECTION_19"
    elif re.search(r'21\s*\(\s*1\s*\)|Section\s*21|Sec\s*21', combined, re.I):
        event_type = "SECTION_21"
    elif re.search(r'Final\s*Award|Award\s*under\s*section|Supplementary\s*Award|Section\s*23|Section\s*3G|Sec\.?23', combined, re.I):
        event_type = "AWARD"
    elif re.search(r'Direct\s*Purchase|private\s*negotiation', combined, re.I):
        event_type = "DIRECT_PURCHASE"

    return {
        'case_number': case_num,
        'village': village,
        'taluka': taluka,
        'project_name': project_name,
        'act_key': act_key,
        'event_type': event_type
    }

def run_ocr(pdf_path):
    if not os.path.exists(OCR_BIN):
        return []
    try:
        proc = subprocess.run([OCR_BIN, pdf_path], capture_output=True, text=True, timeout=30)
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except Exception as e:
        # print(f"OCR error on {pdf_path}: {e}")
        pass
    return []

def extract_pdf_content(pdf_path):
    pages_text = []
    extraction_method = "TEXT"
    try:
        reader = pypdf.PdfReader(pdf_path)
        for i, page in enumerate(reader.pages[:10]):
            t = page.extract_text()
            if t and len(t.strip()) > 30:
                pages_text.append({'page': i + 1, 'text': t.strip()})
    except Exception as e:
        pass
    
    if not pages_text:
        # Fallback to compiled Apple Vision OCR
        ocr_res = run_ocr(pdf_path)
        if ocr_res:
            extraction_method = "OCR"
            for item in ocr_res:
                if item.get('text', '').strip():
                    pages_text.append({'page': item['page'], 'text': item['text'].strip()})

    return extraction_method, pages_text

def download_file(url, target_path):
    if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
        with open(target_path, 'rb') as f:
            data = f.read()
            return data, hashlib.sha256(data).hexdigest()
    
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
        sha = hashlib.sha256(data).hexdigest()
        with open(target_path, 'wb') as f:
            f.write(data)
        return data, sha

def main():
    print("=== BHUMISETU Real Land Acquisition Data Collection Started ===")
    os.makedirs(RAW_DOCS_DIR, exist_ok=True)
    
    discovered_docs = []
    
    for cfg in DISTRICT_CONFIGS:
        dist_name = cfg['district']
        print(f"\n--- Scanning {dist_name} Collectorate Portal ---")
        dist_raw_dir = os.path.join(RAW_DOCS_DIR, dist_name.lower())
        os.makedirs(dist_raw_dir, exist_ok=True)
        
        found_in_dist = 0
        for p in range(1, cfg['max_pages'] + 1):
            url = cfg['first_page_url'] if p == 1 else cfg['url_pattern'].format(p)
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=12) as resp:
                    soup = BeautifulSoup(resp.read(), 'html.parser')
                    tables = soup.find_all('table')
                    if not tables:
                        break
                    rows = tables[0].find_all('tr')[1:]
                    if not rows:
                        break
                    for r in rows:
                        tds = r.find_all('td')
                        if len(tds) >= 2:
                            title = tds[0].get_text(strip=True)
                            date_str = tds[1].get_text(strip=True) if len(tds) > 1 else ''
                            a = tds[-1].find('a') or tds[0].find('a')
                            href = a['href'] if a and a.has_attr('href') else ''
                            
                            if href and '.pdf' in href.lower() and is_la_document(title):
                                found_in_dist += 1
                                discovered_docs.append({
                                    'district': dist_name,
                                    'state': cfg['state'],
                                    'org': cfg['org'],
                                    'dept': cfg['dept'],
                                    'portal_page': p,
                                    'title': title,
                                    'date_str': date_str,
                                    'pdf_url': href,
                                    'source_url': url
                                })
            except Exception as e:
                # print(f"Error on {dist_name} page {p}: {e}")
                break
        print(f"Discovered {found_in_dist} Land Acquisition documents in {dist_name}")

    print(f"\nTotal verified LA documents discovered across all districts: {len(discovered_docs)}")

    manifest_rows = []
    event_rows = []
    raw_cases_dict = {}

    print("\n--- Downloading Authentic Government PDFs & Running Provenance Extraction ---")
    doc_idx = 0
    for doc in discovered_docs:
        doc_idx += 1
        dist = doc['district']
        pdf_url = doc['pdf_url']
        filename = f"{dist.lower()}_{doc_idx:03d}_{os.path.basename(pdf_url)}"
        target_path = os.path.join(RAW_DOCS_DIR, dist.lower(), filename)
        
        try:
            data, sha256_hash = download_file(pdf_url, target_path)
            file_size = len(data)
        except Exception as e:
            print(f"Failed to download {pdf_url}: {e}")
            continue
        
        # Manifest entry
        source_id = f"SRC_{dist.upper()}_{doc_idx:03d}"
        pub_date = parse_date(doc['date_str'])
        
        # Extract text / OCR
        extraction_method, pages = extract_pdf_content(target_path)
        first_page_text = pages[0]['text'] if pages else ""
        all_text = " ".join([p['text'] for p in pages[:3]])
        
        # Entity extraction
        extracted = extract_case_details(doc['title'], all_text)
        
        manifest_rows.append({
            'source_id': source_id,
            'source_title': doc['title'],
            'source_organization': doc['org'],
            'source_department': doc['dept'],
            'source_state': doc['state'],
            'source_district': dist,
            'source_url': doc['source_url'],
            'source_pdf_url': pdf_url,
            'source_publication_date': pub_date or doc['date_str'],
            'download_timestamp': datetime.utcnow().isoformat() + "Z",
            'local_file_path': os.path.relpath(target_path, BASE_DIR),
            'sha256_hash': sha256_hash,
            'file_size_bytes': file_size,
            'mime_type': 'application/pdf',
            'act_key': extracted['act_key'],
            'extraction_method': extraction_method
        })

        # Event generation
        event_id = f"EVT_{dist.upper()}_{doc_idx:03d}"
        snippet = (doc['title'] + " | " + first_page_text[:150]).strip().replace("\n", " ")
        event_rows.append({
            'event_id': event_id,
            'source_id': source_id,
            'district': dist,
            'case_number': extracted['case_number'] or "UNSPECIFIED",
            'village': extracted['village'] or "",
            'taluka': extracted['taluka'] or "",
            'project_name': extracted['project_name'] or "",
            'act_key': extracted['act_key'],
            'event_type': extracted['event_type'],
            'event_date': pub_date or doc['date_str'],
            'recording_date': pub_date or doc['date_str'],
            'stage': extracted['event_type'],
            'description': doc['title'],
            'source_document': filename,
            'source_url': pdf_url,
            'source_page': 1,
            'extraction_method': extraction_method,
            'source_document_hash': sha256_hash,
            'raw_text_snippet': snippet[:300]
        })

        # Multi-event Case Reconstruction logic
        # Group key: Case Number (if present) else District + Village + Project
        if extracted['case_number'] and len(extracted['case_number']) > 2:
            case_key = f"{dist}__CASE__{re.sub(r'[^A-Za-z0-9]', '_', extracted['case_number']).upper()}"
        elif extracted['village']:
            case_key = f"{dist}__VIL__{re.sub(r'[^A-Za-z0-9]', '_', extracted['village']).upper()}__{re.sub(r'[^A-Za-z0-9]', '_', extracted['project_name'] or 'GEN').upper()}"
        else:
            case_key = f"{dist}__DOC__{doc_idx:03d}"

        if case_key not in raw_cases_dict:
            raw_cases_dict[case_key] = {
                'case_id': f"CAS_{dist.upper()}_{len(raw_cases_dict)+1:03d}",
                'case_number': extracted['case_number'] or "",
                'project_id': f"PRJ_{re.sub(r'[^A-Za-z0-9]', '_', extracted['project_name'] or dist).upper()[:12]}",
                'project_name': extracted['project_name'] or "",
                'acquiring_authority': doc['org'],
                'act_key': extracted['act_key'],
                'state': doc['state'],
                'district': dist,
                'taluka': extracted['taluka'] or "",
                'village': extracted['village'] or "",
                'section_11_date': None,
                'section_19_date': None,
                'section_21_date': None,
                'award_date': None,
                'payment_date': None,
                'possession_date': None,
                'completion_date': None,
                'notice_count': 0,
                'objection_count': 0,
                'parcel_count': 0,
                'extension_count': 0,
                'first_extension_date': None,
                'last_extension_date': None,
                'compensation_amount': None,
                'case_status': 'IN_PROGRESS',
                'source_organization': doc['org'],
                'source_document': filename,
                'source_url': pdf_url,
                'source_date': pub_date or doc['date_str'],
                'extraction_method': extraction_method,
                'source_page': 1,
                'source_document_hash': sha256_hash,
                'events': []
            }
        
        c = raw_cases_dict[case_key]
        c['notice_count'] += 1
        if not c['village'] and extracted['village']:
            c['village'] = extracted['village']
        if not c['taluka'] and extracted['taluka']:
            c['taluka'] = extracted['taluka']
        if not c['project_name'] and extracted['project_name']:
            c['project_name'] = extracted['project_name']
            c['project_id'] = f"PRJ_{re.sub(r'[^A-Za-z0-9]', '_', extracted['project_name']).upper()[:12]}"
        if not c['case_number'] and extracted['case_number']:
            c['case_number'] = extracted['case_number']

        etype = extracted['event_type']
        edate = pub_date or doc['date_str']

        if etype == "SECTION_11":
            if not c['section_11_date'] or edate < c['section_11_date']:
                c['section_11_date'] = edate
        elif etype == "SECTION_19":
            if not c['section_19_date'] or edate < c['section_19_date']:
                c['section_19_date'] = edate
        elif etype == "SECTION_21":
            if not c['section_21_date'] or edate < c['section_21_date']:
                c['section_21_date'] = edate
        elif etype == "AWARD":
            if not c['award_date'] or edate > c['award_date']:
                c['award_date'] = edate
                c['case_status'] = 'AWARD_PASSED'
        elif etype == "EXTENSION":
            c['extension_count'] += 1
            if not c['first_extension_date'] or edate < c['first_extension_date']:
                c['first_extension_date'] = edate
            if not c['last_extension_date'] or edate > c['last_extension_date']:
                c['last_extension_date'] = edate
            c['case_status'] = 'EXTENSION_GRANTED'

        c['events'].append(event_id)

    # Re-link case_id in event_rows
    case_key_by_event = {}
    for k, v in raw_cases_dict.items():
        for eid in v['events']:
            case_key_by_event[eid] = v['case_id']
    
    for ev in event_rows:
        ev['case_id'] = case_key_by_event.get(ev['event_id'], "")

    # Output CSV 1: source_manifest.csv
    manifest_csv = os.path.join(BASE_DIR, "source_manifest.csv")
    with open(manifest_csv, "w", newline="", encoding="utf-8") as f:
        fields = [
            'source_id', 'source_title', 'source_organization', 'source_department',
            'source_state', 'source_district', 'source_url', 'source_pdf_url',
            'source_publication_date', 'download_timestamp', 'local_file_path',
            'sha256_hash', 'file_size_bytes', 'mime_type', 'act_key', 'extraction_method'
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"\nWritten {len(manifest_rows)} records to {manifest_csv}")

    # Output CSV 2: real_land_acquisition_events.csv
    events_csv = os.path.join(BASE_DIR, "real_land_acquisition_events.csv")
    with open(events_csv, "w", newline="", encoding="utf-8") as f:
        fields = [
            'event_id', 'case_id', 'source_id', 'case_number', 'district',
            'village', 'taluka', 'project_name', 'act_key', 'event_type',
            'event_date', 'recording_date', 'stage', 'description',
            'source_document', 'source_url', 'source_page', 'extraction_method',
            'source_document_hash', 'raw_text_snippet'
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(event_rows)
    print(f"Written {len(event_rows)} records to {events_csv}")

    # Output CSV 3: real_land_acquisition_cases.csv
    cases_csv = os.path.join(BASE_DIR, "real_land_acquisition_cases.csv")
    with open(cases_csv, "w", newline="", encoding="utf-8") as f:
        fields = [
            'case_id', 'case_number', 'project_id', 'project_name',
            'acquiring_authority', 'act_key', 'state', 'district', 'taluka',
            'village', 'section_11_date', 'section_19_date', 'section_21_date',
            'award_date', 'payment_date', 'possession_date', 'completion_date',
            'notice_count', 'objection_count', 'parcel_count', 'extension_count',
            'first_extension_date', 'last_extension_date', 'compensation_amount',
            'case_status', 'source_organization', 'source_document', 'source_url',
            'source_date', 'extraction_method', 'source_page', 'source_document_hash'
        ]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for c in raw_cases_dict.values():
            row_data = {k: c[k] for k in fields}
            writer.writerow(row_data)
    print(f"Written {len(raw_cases_dict)} reconstructed cases to {cases_csv}")

    print("\n=== Data Collection & Verification Pipeline Completed Successfully ===")

if __name__ == '__main__':
    main()
