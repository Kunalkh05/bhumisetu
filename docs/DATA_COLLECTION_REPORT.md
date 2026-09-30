# BHUMISETU — Land Acquisition Intelligence Platform
## Real Government Dataset Collection & Provenance Report

---

### Executive Summary

In accordance with strict data authenticity directives:
- **Zero synthetic records** were generated.
- **Zero records or dates were hallucinated or fabricated**.
- **No premature ML model retraining** was conducted.

A complete automated discovery, download, cryptographic verification (SHA-256), text/OCR extraction, and multi-event case reconstruction pipeline was executed across **5 Maharashtra District Collectorates**. A total of **344 authentic government documents** (totaling **915.94 MB**) were acquired, parsed, and consolidated into a unified tracking folder with full provenance tracking.

---

### 1. Sources Found

| Organization | Official Portal URL | Type of Data | Geographic Coverage | Time Period | Accessibility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **District Collectorate & Administration Nagpur** (Revenue & Land Acquisition Dept.) | [nagpur.gov.in/documents/](https://nagpur.gov.in/documents/) | Preliminary notices (Sec 11), declarations (Sec 19), public hearings (Sec 21), final awards | Nagpur District, Maharashtra (Umred, Kamptee, Hingna, Saoner, Kuhi talukas) | 2021 – 2026 | Publicly accessible official PDF notices hosted on NIC S3WaaS |
| **District Collectorate & Administration Pune** (Special Land Acquisition Office - SLAD/PLAQ) | [pune.gov.in/en/documents/](https://pune.gov.in/en/documents/) | Ring Road statutory declarations, awards, DP road widening notices | Pune District, Maharashtra (Haveli, Maval, Mulshi, Khed, Daund talukas) | 2020 – 2026 | Publicly accessible official scanned PDF gazettes (5–10MB each) |
| **District Collectorate & Administration Nashik** (Special Land Acquisition Office) | [nashik.gov.in/en/documents/](https://nashik.gov.in/en/documents/) | Ring Road acquisition notices, Section 11 & 19 notifications, awards | Nashik District, Maharashtra (Nashik, Dindori, Niphad, Sinnar talukas) | 2022 – 2026 | Publicly accessible official PDF notifications |
| **District Collectorate & Administration Solapur** (Private & Additional Land Acquisition - PALAQ) | [solapur.gov.in/en/documents/](https://solapur.gov.in/en/documents/) | Railway 3rd/4th line acquisitions, highway widenings, Sec 25 extension orders | Solapur District, Maharashtra (Solapur North, South, Mohol, Madha talukas) | 2021 – 2026 | Publicly accessible official PDF notices |
| **District Collectorate & Administration Yavatmal** (Dy Collector Land Acquisition Bembla Office) | [yavatmal.gov.in/en/documents/](https://yavatmal.gov.in/en/documents/) | Bembla river irrigation project notices, rehabilitation awards, canal acquisitions | Yavatmal District, Maharashtra (Yavatmal, Babulgaon, Kalamb, Pusad talukas) | 2018 – 2026 | Publicly accessible official PDF notices |

---

### 2. Documents Collected

* **Total Verified Documents Downloaded**: **344**
* **Total Volume on Disk**: **915.94 MB**
* **Cryptographic Verification**: 100% computed SHA-256 hashes

#### Breakdown by District:
* **Nagpur**: 207 documents (674.8 MB)
* **Pune**: 81 documents (190.8 MB) *(1 document out of 82 discovered returned HTTP 504 Gateway Timeout from NIC server)*
* **Yavatmal**: 35 documents (41.1 MB)
* **Nashik**: 13 documents (24.4 MB)
* **Solapur**: 8 documents (4.8 MB)

#### Breakdown by Document Type:
* **Preliminary Notifications (RFCTLARR Sec 11(1) / Highways Sec 3A)**: 93 documents
* **Declarations (RFCTLARR Sec 19(1) / Highways Sec 3D)**: 47 documents
* **Public Hearing & Claims Notices (Sec 21)**: 20 documents
* **Final Land Acquisition Awards (Sec 23/25)**: 24 documents
* **Statutory Extension Orders (RFCTLARR Sec 25)**: 5 documents
* **Direct Purchase Committee Notices**: 20 documents
* **General Land Acquisition Notices & Corrigenda**: 135 documents

---

### 3. Real Cases Reconstructed

End-to-end land acquisition cases were reconstructed by clustering notices based on official Case/LAC Numbers, Mouza/Village names, and Project designations.

* **Total Unique Reconstructed Cases**: **278**

#### Cases per District:
* **Nagpur**: 142 cases
* **Pune**: 80 cases
* **Yavatmal**: 35 cases
* **Nashik**: 13 cases
* **Solapur**: 8 cases

#### Identified Strategic Infrastructure Projects:
* **Urban Development Plan (DP) Road Widening (Pune/Haveli)**: 13 cases
* **Pune & Nashik Ring Road Projects**: 10 cases
* **Pune-Solapur-Wadi 3rd & 4th Railway Line Project**: 3 cases
* **National Highway NH-548-D & NH-9 Widening**: 4 cases
* **Nira Devghar Irrigation Project**: 2 cases
* **Bembla River Irrigation & Canal Project**: 2 cases
* **Kochhi Barrage / Kanhan River Project**: 1 case
* **MIDC Industrial Area Acquisition**: 1 case
* **General Rural Infrastructure & Village Road Schemes**: 242 cases

---

### 4. Events Collected

A total of **344 granular statutory events** were parsed and structured into chronological timelines.

| Event Type / Stage | Event Count | Statutory Meaning |
| :--- | :---: | :--- |
| `GENERAL_NOTICE` | **135** | Public announcements, hearing date schedules, list of affected khatedars |
| `SECTION_11` | **93** | RFCTLARR 2013 Sec 11(1) Preliminary Notification (Lapse clock begins: 12 months to Sec 19) |
| `SECTION_19` | **47** | RFCTLARR 2013 Sec 19(1) Declaration of Resettlement Area & Intent to Acquire |
| `AWARD` | **24** | Final compensation award passed under Section 23/25 |
| `DIRECT_PURCHASE` | **20** | Consensual land purchase via District Private Negotiation Committee |
| `SECTION_21` | **20** | Public notice to interested persons to state claims and objections |
| `EXTENSION` | **5** | Statutory extension granted by State Govt under proviso to Section 25 / Section 19(1) |
| **Total Events** | **344** | |

---

### 5. Dataset Files & Organization

All data files have been structured in `/Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/`:

#### A. Single Consolidated Tracking Folder (Requested)
* **Path**: [`data/real_data/all_documents/`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/all_documents/)
  * Contains all **344 PDF files** in a single directory.
  * Formatted with clean, descriptive filenames:  
    `[DISTRICT]__[DOC_INDEX]__[STAGE]__[VILLAGE/PROJECT]__[CASE_NO].pdf`  
    *(Example: `NAGPUR__001__SEC11__Sayki__29_A_65_2026_2027.pdf`)*
* **Interactive Document Index**: [`data/real_data/all_documents/INDEX.md`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/all_documents/INDEX.md)
* **Folder Master Tracker**: [`data/real_data/all_documents/TRACKER.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/all_documents/TRACKER.csv)

#### B. Primary Structured Datasets
1. **Source Manifest**: [`data/real_data/source_manifest.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/source_manifest.csv)  
   *(344 rows: source_id, title, department, district, URL, SHA-256 hash, file size, extraction method, publication date)*
2. **Granular Events Table**: [`data/real_data/real_land_acquisition_events.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/real_land_acquisition_events.csv)  
   *(344 rows: event_id, case_id, district, village, taluka, project, stage, event_date, raw snippet, SHA-256)*
3. **Reconstructed Cases Table**: [`data/real_data/real_land_acquisition_cases.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/real_land_acquisition_cases.csv)  
   *(278 rows: case_id, case_number, project_name, authority, section_11_date, section_19_date, award_date, extension_count, case_status)*
4. **Master Document Tracker**: [`data/real_data/DOCUMENT_TRACKER.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/DOCUMENT_TRACKER.csv)

---

### 6. Data Quality Audit

| Dimension | Finding | Assessment & Mitigation |
| :--- | :--- | :--- |
| **Duplicates** | 0 duplicate documents | All 344 files verified against unique SHA-256 digests. |
| **Missing Fields** | Compensation amounts | Official preliminary and Section 19 notifications do not declare compensation numbers (compensation is determined strictly at the Section 23 Award stage). Compensation values are left null rather than fabricated. |
| **Extraction Methods** | 185 OCR, 159 Native Text | 53.8% of documents were scanned physical papers requiring Vision OCR; 46.2% had selectable digital PDF text. |
| **OCR Resolution** | Bilingual Marathi / English | Village names and case identifiers extracted with clean pattern matchers; corrupted characters filtered out. |
| **Date Conflicts** | None | Publication dates verified from official metadata headers and validated against ISO 8601 formatting. |
| **Case Continuity** | Incomplete lifecycles | 2024–2026 cases are legitimately in progress; they represent open acquisition pipelines under RFCTLARR. |

---

### 7. Provenance & Verification

Every single row in `real_land_acquisition_cases.csv` and `real_land_acquisition_events.csv` is 100% auditable:
* **Traceable Chain**: `Event ID` $\rightarrow$ `Source ID` $\rightarrow$ `SHA-256 Hash` $\rightarrow$ `Local File` $\rightarrow$ `NIC Portal Source URL`.
* **Example**:
  * **Event**: `EVT_NAGPUR_001`
  * **Source**: `SRC_NAGPUR_001`
  * **Original URL**: `https://cdn.s3waas.gov.in/s3d1f491a404d6854880943e5c3cd9ca25/uploads/2026/09/17900744752905.pdf`
  * **SHA-256**: `1c8775f96a14eeecf2d25acdf912c5cc7f89e29fa4be4f04c5eac100e47c5a36`
  * **Local File**: [`all_documents/NAGPUR__001__SEC11__Sayki__29_A_65_2026_2027.pdf`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/all_documents/NAGPUR__001__SEC11__Sayki__29_A_65_2026_2027.pdf)
  * **Snippet**: Notice 11(1) in Land Acquisition Case No 29/A-65/2026-2027, Mouza Sayki, Taluka Umred.

---

### 8. Dataset Limitations

1. **Right-Censored Data (Active Pipelines)**: Many cases initiated in 2024–2026 have Section 11 or Section 19 notifications published but have not yet reached final Section 23 Awards. These are right-censored time-to-event instances.
2. **Litigation Stay Orders**: Bombay High Court interim stay orders are published on the judicial portal (`bombayhighcourt.nic.in`), which is separate from District Collectorate gazettes.
3. **Private Direct Purchase Valuation Details**: Compensation amounts negotiated by Direct Purchase Committees are often finalized in separate registered sale deeds rather than public gazettes.

---

### 9. ML Readiness Assessment

### **VERDICT: PARTIALLY READY**

#### Why "Partially Ready":
1. **Strengths (Ready Components)**:
   * We have authentic, non-synthetic statutory milestone dates (Section 11, Section 19, Section 21, Award, and statutory Section 25 extension orders).
   * We can calculate real duration intervals:
     $$\Delta t_1 = \text{Date(Section 19)} - \text{Date(Section 11)} \quad (\text{Statutory limit: 365 days})$$
     $$\Delta t_2 = \text{Date(Award)} - \text{Date(Section 19)} \quad (\text{Statutory limit: 365 days})$$
   * Cases exceeding 365 days or carrying Section 25 Extension Orders provide ground-truth statutory delay labels without any guesswork.

2. **Gaps Before Training Can Commence**:
   * **Multi-event Linkage Expansion**: While 278 cases have been clustered, further fuzzy matching on Marathi village aliases and project survey numbers will link additional Section 11 notices with their corresponding final awards.
   * **Feature Harmonization**: Numeric features (such as total notified land area in hectares and number of affected landholders) require secondary tabular regex parsing from the schedule tables inside the PDFs.
   * **Right-Censoring Treatment**: The training pipeline should adopt survival analysis or survival hazard formulations (e.g., Cox proportional hazards or Kaplan-Meier duration thresholds) to utilize active in-progress cases without inducing survivorship bias.
