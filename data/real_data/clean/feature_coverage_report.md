# BHUMISETU — Clean Feature Coverage & ML Readiness Report
**Generated**: September 29, 2026 | **Dataset Phase**: Cleaning and Preparation Only

---

## 1. Feature Taxonomy (Original vs Derived)

To maintain absolute data provenance, all features are partitioned into two strict categories:

1. **Original Government Features**: Extracted directly from official gazette text, portal headers, or cryptographic metadata without modification.
2. **Derived Features**: Explicitly computed via mathematical/chronological transformations of original government records. Every derived feature is prefixed with `derived_` to prevent confusion with raw facts.

---

## 2. Existing 7 Domain Features Status & Missingness Semantics

In accordance with strict missingness semantics (Task 7), unavailable fields are **never populated with zero** unless the government source affirmatively establishes zero. Instead, they are set to `NULL` with an explicit reason code recorded in a dedicated audit column:

| Feature Name | Status | Direct or Derived | Real Coverage | Missingness Representation | Reason Recorded in Column |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `days_in_current_stage` | **Available** | `DERIVED` | 100.0% (271/271) | Computed as $\Delta t = T - \text{latest\_stage\_date}$ | `N/A` (Fully populated) |
| `days_since_latest_notice` | **Available** | `DERIVED` | 100.0% (271/271) | Computed as $\Delta t = T - \text{latest\_notice\_date}$ | `N/A` (Fully populated) |
| `notice_count` | **Available** | `DERIVED` | 100.0% (271/271) | Count of verified notices linked to case (1 to 4) | `N/A` (Fully populated) |
| `award_recorded` | **Available** | `DIRECT` | 8.9% (24/271) | Boolean check: `award_date IS NOT NULL` | `N/A` (Fully populated) |
| `objection_count` | **Unavailable** | `DERIVED` | **0.0% (0/271)** | **`NULL`** | `NOT_PUBLISHED_IN_GAZETTE` |
| `parcel_count` | **Unavailable** | `DIRECT / DERIVED` | **0.0% (0/271)** | **`NULL`** | `NOT_PUBLISHED_IN_STRUCTURED_DATA` |
| `open_issue_count` | **Unavailable** | `DERIVED` | **0.0% (0/271)** | **`NULL`** | `NOT_APPLICABLE_IN_REAL_DATA` |

---

## 3. Additional Real Features Extracted with Provenance (Task 6)

Every feature row in [`real_land_acquisition_cases_clean.csv`](file:///Users/sakshantwaghmare/Projects/bhumisetu/data/real_data/clean/real_land_acquisition_cases_clean.csv) preserves full provenance tracking back to the source PDF:
* `feature_source_document`: Originating PDF filename
* `feature_source_page`: Specific page number inside document
* `feature_extraction_method`: Text extraction engine (`TEXT` or `OCR`)
* `source_documents`: Semicolon-delimited list of all PDFs linked to the case
* `source_document_hashes`: Semicolon-delimited list of all verified SHA-256 digests

### Summary of Additional Real Features:
* **Statutory Extension Information**: Explicitly tracks extension orders under Section 25 or Section 19(1) proviso.
  * `extension_count`: 4 cases with 1 to 2 statutory extensions
  * `has_statutory_extension`: Binary flag (True for 4 cases)
* **Project Type Categorization**:
  * `derived_project_type`: Ring Road, Highway / Widening, Metro Rail, Railway, Irrigation / Canal, Industrial (MIDC), Rural Public Works.
* **Direct Purchase Negotiation Flag**:
  * `derived_is_direct_purchase`: True for 16 cases acquired through consensual District Private Negotiation Committee.
* **Unparsed Document Table Features** (Left `NULL` to avoid fabrication):
  * `notified_area_hectares`: `NULL` (`missing_reason = UNPARSED_SCHEDULE_TABLE`)
  * `affected_landowner_count`: `NULL` (`missing_reason = UNPARSED_SCHEDULE_TABLE`)
  * `compensation_amount_inr`: `NULL` (`missing_reason = UNPARSED_FROM_PDF_AWARDS`)

---

## 4. Derived Timeline & Proximity Indicators (Task 8)

The following derived features capture statutory velocity and deadline proximity:

| Derived Feature | Formula / Logic | Availability | Empirical Distribution |
| :--- | :--- | :---: | :--- |
| `derived_days_since_case_initiation` | $\Delta t = T_{\text{ref}} - \text{first\_notice\_date}$ | 100.0% (271) | Mean: 412 days, Min: 7 days, Max: 1,012 days |
| `derived_days_since_latest_notice` | $\Delta t = T_{\text{ref}} - \text{latest\_notice\_date}$ | 100.0% (271) | Mean: 386 days, Min: 7 days, Max: 1,012 days |
| `derived_days_in_current_stage` | $\Delta t = T_{\text{ref}} - \text{current\_stage\_date}$ | 100.0% (271) | Mean: 386 days, Min: 7 days, Max: 1,012 days |
| `derived_sec11_to_sec19_duration` | $\text{date}_{\text{sec19}} - \text{date}_{\text{sec11}}$ | 17 cases | Mean: 74.8 days, Min: 0 days, Max: 241 days |
| `derived_statutory_sec19_proximity_ratio`| $(T_{\text{ref}} - \text{date}_{\text{sec11}}) / 365.0$ | 91 cases | Values $> 1.0$ indicate case has exceeded statutory 1-year declaration limit |
| `delay_evidence_type` | `EXPLICIT_EXTENSION` (4) \| `DATE_DERIVED_DELAY` (31) \| `NONE_OBSERVED` (236) | 100.0% (271) | Identifies ground-truth delay instances |

---

## 5. ML Formulation Suitability (Task 10)

### A. Suitability for Binary Delay Classification: **POOR / HIGH RISK OF SURVIVORSHIP BIAS**
* Only **24 cases (8.9%)** have reached completed awards.
* 247 cases (91.1%) are currently in-progress under active statutory acquisition.
* Treating in-progress cases as `NOT_DELAYED` causes label contamination (many will breach deadlines later); treating them as `DELAYED` mislabels normal active cases; dropping them loses 91% of data.
* Therefore, standard binary classification ($y \in \{0, 1\}$) on completed cases alone induces severe survivorship bias.

### B. Suitability for Survival Analysis / Time-to-Event: **EXCELLENT / RECOMMENDED**
* The real data naturally fits a **right-censored survival analysis formulation**:
  * **Event Indicator ($E$)**:
    * $E = 1$: Event observed (Section 19 published, or Award passed, or Extension granted).
    * $E = 0$: Right-censored (case is currently in-progress, observed up to observation date $T_{\text{ref}}$).
  * **Duration ($T$)**: Elapsed days in stage.
* Models supported:
  * **Cox Proportional Hazards**
  * **Gradient Boosted Survival Trees (Survival GBDT / XGBoost Survival)**
  * **Kaplan-Meier Stage Duration Estimators**
* Under this formulation, **100% of all 271 clean cases** provide valid signal without discarding active pipelines or fabricating labels.
