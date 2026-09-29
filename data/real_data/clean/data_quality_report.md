# BHUMISETU — Clean Dataset Quality Report
**Generated**: September 29, 2026 | **Dataset Phase**: Cleaning and Preparation Only

---

## 1. Executive Summary

This report documents the execution and verification of the **Data Cleaning and Preparation Phase** for the authentic Maharashtra government land acquisition dataset in BHUMISETU.

* **Raw Documents Ingested**: **344 PDF files** (**915.94 MB**)
* **Duplicate Documents Pruned**: **7 records** (identified by SHA-256 byte digest equality)
* **Irrelevant Documents Excluded**: **26 unique records** (30 total in raw ingest) from Yavatmal Collectorate classified as `NOT_LAND_ACQUISITION`
* **Clean Relevant Land Acquisition Documents**: **311 documents**
* **Clean Structured Events**: **311 verified statutory events**
* **Reconstructed Cases**: **271 distinct acquisition cases**
* **Contradictory Ordering Instances**: **0** (eliminated via hierarchical `District + Taluka + Village + Case Number` clustering)
* **Provenance**: 100% auditable from official NIC S3WaaS source URLs down to SHA-256 hashes and local files.

---

## 2. Ingestion & Cleaning Funnel

| Stage | Record Count | Notes |
| :--- | :---: | :--- |
| **Raw Documents Ingested** | **344** | Initial harvest across Nagpur, Pune, Nashik, Solapur, Yavatmal Collectorates |
| **Duplicates Removed (SHA-256)** | **-7** | Removed duplicate downloads caused by portal pagination overlaps |
| **Unique Ingested Documents** | **337** | Verified unique cryptographic digests |
| **Irrelevant Documents Flagged** | **-26** | Classified as `NOT_LAND_ACQUISITION` in manifest (Yavatmal personnel & well subsidy lists) |
| **Clean Land Acquisition Documents** | **311** | Authentic, statutory land acquisition gazette files |
| **Clean Statutory Events Generated** | **311** | Exactly 1 event per verified statutory document |
| **Reconstructed Clean Cases** | **271** | Clustered by `(District, Taluka, Village, Case Number)` |

---

## 3. Duplicate Records Cleaned (Task 1)

Exactly 7 documents (14 rows in raw manifest) shared identical SHA-256 hashes due to duplicate links across consecutive web pages on official portals. One canonical copy was retained for each, and the duplicates were pruned from the clean event/case tables while preserving original raw files:

| Duplicate SHA-256 Digest | Canonical Document ID | Duplicate Document ID | District | Title / Description |
| :--- | :--- | :--- | :--- | :--- |
| `377801b5c8bcf313...` | `SRC_NAGPUR_013` | `SRC_NAGPUR_021` | Nagpur | Notice 11(1) in Land Acquisition Case No 22/A-65/2025-26 |
| `dc080802a80b8966...` | `SRC_NAGPUR_012` | `SRC_NAGPUR_018` | Nagpur | Notice 11(1) in Land Acquisition Case No 27/A-65/2025-26 |
| `608e60c4ee5e9b10...` | `SRC_NAGPUR_150` | `SRC_NAGPUR_153` | Nagpur | Proposal for Direct Purchase Bhiwapur Case 37/A-65/2023-24 |
| `8b961ad22e9bb6e8...` | `SRC_YAVATMAL_318` | `SRC_YAVATMAL_325` | Yavatmal | Group C Compassionate Waiting List (Yavatmal Collector Office) |
| `41cc00a32f255bb5...` | `SRC_YAVATMAL_319` | `SRC_YAVATMAL_324` | Yavatmal | Group D Compassionate Waiting List (Yavatmal Collector Office) |
| `02098e0e78e4857c...` | `SRC_YAVATMAL_320` | `SRC_YAVATMAL_323` | Yavatmal | Group D Common Compassionate Candidates List |
| `0f7edbb951b51360...` | `SRC_YAVATMAL_321` | `SRC_YAVATMAL_322` | Yavatmal | Group C Common Compassionate Candidates List |

---

## 4. Irrelevant Documents Removed (Task 2)

A total of 26 unique documents (30 rows in raw manifest) from Yavatmal Collectorate were identified as administrative non-acquisition files and marked as `NOT_LAND_ACQUISITION` in [`source_manifest_clean.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/source_manifest_clean.csv). These are excluded from events and cases:

1. **Compassionate Employment Waiting Lists & Seniority Objections (13 docs)**:
   * `SRC_YAVATMAL_315` to `SRC_YAVATMAL_326` (Group C & D recruitment lists for Collector's office staff).
2. **Agricultural Well Subsidy Lists (13 docs)**:
   * `SRC_YAVATMAL_328` to `SRC_YAVATMAL_340` (Dhadak Sinchan Vihir farmer subsidy beneficiary lists across 13 talukas).
3. **General District Road Development Master Plans (5 docs)**:
   * `SRC_YAVATMAL_341` to `SRC_YAVATMAL_345` (20-year master road development draft plans and taluka road maps from 2017-2018).

*Note*: 5 genuine Land Acquisition Office files in Yavatmal (`SRC_YAVATMAL_311`, `312`, `313`, `314`, `327` — Bembla Project Citizen Charters and LA office promulgations) were retained in the clean dataset.

---

## 5. Case Clustering & Reconstruction (Task 3)

The previous naive clustering grouped notices solely by `case_number`, causing different villages sharing serials like `4/A-65/2025-2026` to merge inappropriately and create artificial date reversals.

### The New Hierarchical Key:
$$\textbf{Cluster Key} = \textbf{District} + \textbf{Taluka} + \textbf{Mouza/Village} + \textbf{Case Number}$$

* **Official Case Number Identified**: **163 cases (60.1%)** carry verified official case numbers (`case_id_type = OFFICIAL_CASE_NUMBER`).
* **Derived Identifier Used**: **108 cases (39.9%)** represent scanned notices without a recognized LAC number (`case_id_type = DERIVED`). For these cases, `case_number` is recorded as `NULL` (empty), never fabricated.
* **Resulting Case Distribution**:
  * **Total Cases**: **271**
  * **Single-Event Cases**: **245 (90.4%)**
  * **Multi-Event Cases**: **26 (9.6%)** (13 two-event cases, 12 three-event cases, 1 four-event case)

---

## 6. Event Chronology & Contradiction Resolution (Task 4)

In the clean dataset [`real_land_acquisition_events_clean.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/real_land_acquisition_events_clean.csv):
* All events are sorted strictly by `(case_id, event_date, event_id)`.
* Every multi-event sequence was audited against statutory milestone ordering:
  $$\text{SECTION\_11} \longrightarrow \text{SECTION\_19} \longrightarrow \text{SECTION\_21} \longrightarrow \text{AWARD}$$
* **Contradictory Stage Orders**: **0** (`contradiction_flag = NORMAL` for all 311 events).
* All 26 multi-event cases progress forward in statutory time.

---

## 7. Milestone & Feature Distribution in Clean Cases

| Milestone / Feature | Case Count | % of Clean Cases (271) | Notes |
| :--- | :---: | :---: | :--- |
| **Section 11(1) Notice** | **91** | 33.6% | Preliminary acquisition notices |
| **Section 19(1) Declaration** | **47** | 17.3% | Resettlement area declarations |
| **Section 21 Hearing / Claims** | **19** | 7.0% | Claims submission notices |
| **Final Compensation Award** | **24** | 8.9% | Completed awards passed |
| **Statutory Extensions** | **4** | 1.5% | Explicit Sec 25 / Sec 19(1) extension orders |
| **Complete Sec 11 $\rightarrow$ Sec 19** | **17** | 6.3% | Both milestones present on record |
| **Complete Sec 11 $\rightarrow$ 19 $\rightarrow$ Award** | **0** | 0.0% | No single case has all 3 published in current 2024-2026 portal scrape |

---

## 8. Missing-Value Statistics in `real_land_acquisition_cases_clean.csv`

| Field | Non-Null Count | Missing Count | Missing % | Missing Semantics / Reason |
| :--- | :---: | :---: | :---: | :--- |
| `case_id` | 271 | 0 | 0.0% | Fully populated deterministic primary key |
| `case_id_type` | 271 | 0 | 0.0% | `OFFICIAL_CASE_NUMBER` (163) or `DERIVED` (108) |
| `case_number` | 163 | 108 | 39.9% | NULL for notices lacking standard LAC header |
| `district` | 271 | 0 | 0.0% | 100% available |
| `taluka` | 165 | 106 | 39.1% | NULL where not specified in notice title/header |
| `village` | 174 | 97 | 35.8% | NULL where notice covers general district work |
| `project_name` | 36 | 235 | 86.7% | Specified for major ring roads, highways, canals |
| `acquiring_authority` | 271 | 0 | 0.0% | 100% available from portal metadata |
| `act_key` | 271 | 0 | 0.0% | 100% available |
| `case_status` | 271 | 0 | 0.0% | `COMPLETED` (24) or `IN_PROGRESS` (247) |
| `section_11_date` | 91 | 180 | 66.4% | NULL where case entered at later/earlier stage |
| `section_19_date` | 47 | 224 | 82.7% | NULL where declaration not yet gazetted |
| `award_date` | 24 | 247 | 91.1% | NULL where award not yet passed |
| `objection_count` | 0 | 271 | 100.0% | `NOT_PUBLISHED_IN_GAZETTE` (Never populated with 0) |
| `parcel_count` | 0 | 271 | 100.0% | `NOT_PUBLISHED_IN_STRUCTURED_DATA` (Unparsed from PDF) |
| `open_issue_count` | 0 | 271 | 100.0% | `NOT_APPLICABLE_IN_REAL_DATA` (Synthetic feature) |
| `compensation_amount_inr` | 0 | 271 | 100.0% | `UNPARSED_FROM_PDF_AWARDS` (In award tables) |
| `notified_area_hectares` | 0 | 271 | 100.0% | `UNPARSED_SCHEDULE_TABLE` (In schedule tables) |

---

## 9. Extraction Methods

Across the 311 clean event documents:
* **Apple Vision OCR**: **178 documents (57.2%)** — Required for scanned physical paper notices and non-Unicode Devanagari font encodings.
* **Native Digital PDF Text**: **133 documents (42.8%)** — Direct text extraction via PDF parser.
