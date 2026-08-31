# Requirements Document

## Introduction

BHUMISETU is a government land acquisition management platform for India. The platform manages land acquisition cases end to end — projects, land parcels, ownership records, statutory notices, objections, compensation determination, and payout — and surfaces which cases are at risk of missing their statutory milestones so that acquisition officers can intervene before a delay materialises.

The platform exposes two distinct surfaces with different threat models, different data visibility, and different performance budgets:

- An **officer portal** for government staff: dashboard, case workspace, GIS map, document viewer, OCR review, validation issue queue, and intervention queue.
- A **citizen portal** for landowners: a mobile-first, text-first surface for looking up the status of their own case, viewing a timeline, and retrieving their own documents over poor rural connectivity.

Three capabilities sit behind both surfaces: document digitization (upload, asynchronous OCR, human correction), a validation engine that raises resolvable issues over extracted data, and a machine learning pipeline that predicts delay risk from an event timeline and produces per-case explanation factors.

An append-only event log is a first-class feature rather than an implementation detail: it is the sole source of both the citizen-visible case timeline and the point-in-time features consumed by the machine learning pipeline.

Two further concerns cut across every subsystem. A district arrives with an existing record base, so bulk migration of parcels, ownership records, and documents is a precondition of use rather than an afterthought. And the personal data the platform holds about landowners — names, contact numbers, government identifiers — carries retention, access, and correction obligations that coexist awkwardly with the permanence of a land record and of the event log.

This document defines **what** BHUMISETU must do. Architecture, data schemas, endpoint shapes, and library selection belong in the design document.

---

## Open Policy Decisions (Confirmation Required)

The following decisions carry legal, statistical, or user-safety consequences and cannot be inferred from the technical stack. Each has a **proposed default** so that the requirements below are concrete and testable, but every proposed default is provisional and requires user confirmation before design begins. Requirements that depend on an open decision are annotated `_Depends on: Qn_`.

**Q1 — Definition of the machine learning label (highest priority).**
What exactly counts as "delayed"? The whole ML pipeline depends on this answer.
*Proposed default:* the prediction target is binary and stage-scoped. For a case in Case_Stage S at prediction time T, the label is `DELAYED` if the case has not entered the successor stage of S within the Stage_Deadline for S, evaluated over a fixed horizon of 90 days after T, and `NOT_DELAYED` if the case entered the successor stage of S on or before the Stage_Deadline for S and that Stage_Deadline falls at or before the end of the horizon. The Stage_Deadline baseline is the configured statutory period for S; where no statutory period is configured for S, the baseline is the 75th percentile of historical completed durations for S within the same district.

*Right-censoring.* A candidate row whose outcome is not knowable at the end of the horizon is neither `DELAYED` nor `NOT_DELAYED`. Two situations produce such a row: the Stage_Deadline for S falls after the end of the horizon, so the deadline has not been reached when observation stops; and the end of the horizon falls after the current date, so the case is too recent to have been observed for the full horizon. Labelling either situation `NOT_DELAYED` records an absence of evidence as evidence of absence and biases the model towards optimism, which is the worst direction of error for a tool whose purpose is to warn. *Proposed default:* such a row is labelled `CENSORED`, is excluded from the training split and from the evaluation split, and the `CENSORED` row count and censoring rate are recorded with every training run so that the discarded fraction is visible rather than silent.

**RESOLVED (maintainer default):** Adopt the proposed default. Formulation is binary (DELAYED / NOT_DELAYED) with CENSORED rows excluded from both splits; the survival fields time_to_event_days and event_observed are populated on every row so a later survival formulation needs no relabelling. Stage transitions in scope: every transition out of a non-terminal Case_Stage to its declared successor. Deadline baseline: the configured statutory period for the stage, falling back to the 75th percentile of historical completed durations for that stage within the same district where no statutory period is configured. Prediction horizon: 90 days. Censoring treatment as the proposed default (CENSORED excluded, count and rate recorded per run).

**Q2 — Leakage prevention.**
*Proposed default:* every training row is reconstructed as of a past timestamp T using only Event records with an occurrence time at or before T; no attribute whose value became known after T, and no attribute derived from the labelled outcome, may appear in the row. **Confirm:** acceptance of this constraint as non-negotiable.

**Q3 — Citizen portal performance budget.**
*Proposed default:* reference network profile is 400 kbps downlink, 400 kbps uplink, 2000 ms round-trip time. Any Citizen_Portal API response is at most 50 KB uncompressed. Initial page weight is at most 150 KB transferred, compressed, counting markup, styles, scripts, and fonts, and excluding documents the citizen explicitly requests. First contentful paint occurs within 5 seconds and the case status view becomes interactive within 8 seconds at the 95th percentile over 100 consecutive cold loads of the case status view on the reference profile. Offline behaviour serves the last successfully fetched case view from local cache, labelled with its retrieval time. **Confirm:** the reference profile, each number, and the 95th percentile as the reporting statistic.

**Q4 — OCR confidence thresholds.**
*Proposed default:* per-field confidence at or above 0.95 auto-accepts the extracted value; confidence from 0.60 up to but excluding 0.95 routes the field to mandatory human review; confidence below 0.60 discards the extracted value and marks the field for manual entry. A document whose mean per-field confidence is below 0.50 is rejected as unusable and a re-upload is requested.

*Grounding the thresholds.* A confidence score is a model output, not an accuracy measurement. A threshold of 0.95 is defensible only against measured field-level extraction accuracy on a hand-labelled Holdout_Set, because the precision actually achieved at a given confidence varies by field name, by script, and by scan quality. *Proposed default:* the Holdout_Set contains at least 200 Documents per configured script, with at least 50 hand-labelled instances of every target field name, and the auto-accept threshold is admissible only where the measured precision at that threshold is at least 0.98. **RESOLVED (maintainer default):** Adopt the proposed default. auto-accept threshold 0.95; review threshold 0.60 (fields in [0.60, 0.95) route to PENDING_REVIEW); below 0.60 discards the value and marks MANUAL_ENTRY_REQUIRED; document-rejection mean-confidence threshold 0.50. Holdout_Set minimum 200 Documents per configured script and at least 50 hand-labelled instances per target field; auto-accept admissible only where measured precision at that threshold is at least 0.98. These are Policy_Config values seeded as defaults, never code literals, and AUTO_ACCEPTED remains gated behind a current non-superseded Extraction_Accuracy_Report.

**Q5 — Risk band cutoffs.**
*Proposed default:* calibrated probability p maps to LOW for p < 0.25, MEDIUM for 0.25 ≤ p < 0.50, HIGH for 0.50 ≤ p < 0.75, and CRITICAL for p ≥ 0.75. Cutoffs are platform-wide defaults, overridable per district. Per-district calibration is statistically unreliable where a district holds few closed cases, so the override carries a floor: *proposed default:* a district-specific cutoff set applies only where that district holds at least 500 labelled historical Acquisition_Cases, and the platform-wide cutoffs apply below that count. **Confirm:** the boundaries, whether per-district override is permitted, and the minimum count of labelled historical Acquisition_Cases required before a district-specific cutoff set may be applied.

**Q6 — Citizen identity and privacy.**
*Proposed default:* a landowner proves entitlement to a case view by presenting a Case_Reference plus a one-time passcode delivered to the mobile number recorded against an Ownership_Record on that case. Sessions expire 15 minutes after issue. From the citizen view the platform excludes other owners' personal data, all internal officer notes, the numeric Risk_Probability, and the Priority_Score. **Confirm:** the identity mechanism, session lifetime, and the redaction list.

**Q7 — Language and script coverage.**
*Proposed default:* OCR accepts Devanagari and Latin scripts plus one additional regional script configured per deployment. The Citizen_Portal renders English, Hindi, and the deployment's configured regional language. The Officer_Portal renders English and Hindi. **Confirm:** the target states and their languages and scripts.

**Q8 — Statutory timelines and governing act.**
*Proposed default:* the platform stores no legally significant period as a literal in code. Every notice period, objection window, and stage deadline is a Policy_Config value keyed by state and act, with an effective-from date. The presumed governing framework is the Right to Fair Compensation and Transparency in Land Acquisition, Rehabilitation and Resettlement Act, 2013 together with the applicable state rules. **RESOLVED (maintainer default):** Governing act is the RFCTLARR 2013 (act key RFCTLARR_2013). A platform-wide (state key '*') default baseline IS seeded, effective-dated, and per-state override remains supported; any state-and-act key with no effective value still triggers the refuse-and-report path of R28.5. No period is ever a literal in code, a column default, or a CHECK constraint. Default baseline period values, each flagged as requiring state-level legal review before production use because states amend these: Social Impact Assessment completion 180 days; Expert Group appraisal 60 days; preliminary notification after SIA appraisal 365 days; objection window 60 days from preliminary notification; declaration after preliminary notification 365 days; award after declaration 365 days; general statutory-notice response period 60 days; objection disposal target 60 days. State-specific values override the baseline where configured.

**Q9 — Scope of compensation determination.**
*Proposed default:* BHUMISETU records award amounts determined outside the platform and verifies internal arithmetic consistency between components and totals. The platform does not itself determine market value, multipliers, or solatium. **Confirm:** whether computing the award is in scope.

**Q10 — Personal data retention periods and governing data-protection framework.**
BHUMISETU stores owner names, contact numbers, and government identifiers, so a data-protection framework applies and the retention period for each Data_Category cannot be inferred from the technical stack. The framework also sits in tension with land-record permanence: a land record is a permanent public instrument, while contact and identity data attached to it is not.
*Proposed default:* the presumed governing framework is the Digital Personal Data Protection Act, 2023 together with the rules notified under it and any applicable state land-records retention rules. Every Retention_Period is a Policy_Config value carrying the same state key, act key, and effective-from date as a statutory period. Proposed default Data_Category set and Retention_Periods, each measured from the retention start date defined in Requirement 32: `OWNER_CONTACT` 3 years, `OWNER_IDENTITY` 8 years, `MODEL_FEATURE` 5 years, and `LAND_RECORD`, `DOCUMENT_CONTENT`, and `AUDIT_EVENT` retained without expiry. The erasable Data_Category set is `OWNER_CONTACT`, `OWNER_IDENTITY`, and `MODEL_FEATURE`; the remainder persist as statutory record. A Data_Subject_Request is answered within 30 days of receipt. **RESOLVED (maintainer default):** Governing framework is the Digital Personal Data Protection Act 2023 (act key DPDP_2023) together with applicable state land-records retention rules. Data_Category set and Retention_Periods as the proposed default: OWNER_CONTACT 3 years, OWNER_IDENTITY 8 years, MODEL_FEATURE 5 years; LAND_RECORD, DOCUMENT_CONTENT, and AUDIT_EVENT retained without expiry. Erasable set: OWNER_CONTACT, OWNER_IDENTITY, MODEL_FEATURE. Data_Subject_Request maximum response period 30 days. A DSAR access response does NOT carry the unmasked government identifier — the masking rule of R26.5 applies even to a data subject access response, because OTP-to-mobile authentication is too weak to justify releasing a full government identifier and the subject already holds their own identifier. The retention sweep ships DISABLED (retention.sweep_enabled false, no seeded retention.period.* rows outside test fixtures); erasure is irreversible, so a deployment enables the sweep explicitly only after confirming its state's land-record retention rules.

**Q11 — Scope of proactive citizen notification.**
Requirement 25.1 requires the Citizen_Portal to present the next expected step, which means a Citizen learns of a Case_Stage change only by opening the portal. Whether BHUMISETU also pushes an outbound message when a case event occurs is stated nowhere and cannot be inferred: it carries per-message cost, consent obligations, and delivery-failure handling that change the scope of several subsystems.
*Proposed default:* out of scope. The Citizen_Portal is pull-only, and the sole outbound message BHUMISETU sends is the one-time passcode of Requirement 3.1. **Confirm:** whether proactive citizen notification is in scope; and if it is, the event set that triggers a notification (for example Case_Stage change, Statutory_Notice service, Award recorded, Payout recorded, Stage_Deadline breach), the channel (SMS, voice, email, postal), the consent record required before a message is sent, the language selection rule for an outbound message, and the behaviour on delivery failure. No notification requirement is stated in this document until this is confirmed.

---

## Glossary

- **BHUMISETU**: The complete platform, comprising all subsystems named below.
- **Officer_Portal**: The authenticated interface used by government staff.
- **Citizen_Portal**: The low-bandwidth interface used by landowners.
- **Auth_Service**: The subsystem that authenticates officers and issues and revokes sessions.
- **Access_Control**: The subsystem that decides, for a given actor and resource, whether access is permitted and which fields are visible.
- **Citizen_Access_Service**: The subsystem that verifies a landowner's entitlement to view a specific Acquisition_Case and issues short-lived citizen sessions.
- **Event_Log**: The append-only store of Event records. The Event_Log is the sole source of the citizen timeline and of machine learning features.
- **Event**: An immutable record of one state change, carrying the actor, the affected entity, the change, the occurrence time, and the recording time.
- **Concurrency_Control**: The subsystem that detects a conflicting concurrent modification of one entity and rejects the losing write.
- **Entity_Version**: A marker held against a mutable entity that increases on every committed modification of that entity, used to detect a conflicting concurrent modification.
- **Case_Service**: The subsystem that manages Acquisition_Case records and Case_Stage transitions.
- **Acquisition_Case**: The unit of work for acquiring one set of Land_Parcels for one Project.
- **Case_Reference**: The human-quotable unique identifier of an Acquisition_Case.
- **Project**: A government undertaking for which land is acquired.
- **Land_Parcel**: A demarcated area of land identified by survey number within a village, with an associated geometry.
- **Ownership_Record**: A recorded interest of one person or entity in one Land_Parcel, including share, contact details, and validity period.
- **Case_Stage**: A named position in the acquisition lifecycle, for example social impact assessment, preliminary notification, declaration, award, payout, possession. The stage set is a Policy_Config value.
- **Stage_Deadline**: The date by which an Acquisition_Case must leave its current Case_Stage, derived from Policy_Config.
- **Notice_Service**: The subsystem that manages statutory notices and their deadlines.
- **Statutory_Notice**: A legally mandated communication tied to a Case_Stage, with an issue date, a service date, and a response window.
- **Objection_Service**: The subsystem that records objections raised against an Acquisition_Case and their disposal.
- **Objection**: A recorded challenge by an interested person to an acquisition, with a receipt date, grounds, and a disposal outcome.
- **Compensation_Service**: The subsystem that records award amounts and tracks payout.
- **Award**: The recorded compensation determination for an Ownership_Record, comprising itemised components and a total.
- **Payout**: A recorded disbursement against an Award.
- **Document_Service**: The subsystem that accepts, stores, and serves scanned land records and derived artefacts.
- **Document**: An uploaded file representing a land record, together with its metadata, checksum, and processing state.
- **OCR_Service**: The subsystem that asynchronously extracts text, field values, bounding boxes, and confidence scores from a Document.
- **Extraction**: The output of OCR_Service for one Document, comprising full text and a set of Extracted_Fields.
- **Extracted_Field**: One named value derived from a Document, with a bounding box, a confidence score, and a review state.
- **Review_State**: The position of an Extracted_Field in the human-in-the-loop flow: `AUTO_ACCEPTED`, `PENDING_REVIEW`, `CORRECTED`, `CONFIRMED`, or `MANUAL_ENTRY_REQUIRED`.
- **Holdout_Set**: A set of Documents whose correct field values are recorded by hand, independently of any OCR_Service output, and which is withheld from every process that tunes the OCR_Service.
- **Extraction_Accuracy_Report**: The recorded measurement of OCR_Service field-level extraction accuracy against a Holdout_Set, stating exact-match accuracy per field name and per detected script and the precision observed at each configured confidence threshold.
- **Validation_Engine**: The subsystem that evaluates rules over case, parcel, ownership, and Extracted_Field data and emits Validation_Issues.
- **Validation_Issue**: A recorded rule violation, carrying a rule identifier, a Severity, the offending entities, and a resolution state.
- **Severity**: The consequence class of a Validation_Issue: `BLOCKING`, `MAJOR`, `MINOR`, or `ADVISORY`.
- **GIS_Service**: The subsystem that stores and serves Project and Land_Parcel geometry.
- **Import_Service**: The subsystem that accepts a bulk submission of existing Land_Parcel, Ownership_Record, and Document data, validates it row by row, and commits the rows that pass.
- **Import_Batch**: One bulk submission handled by the Import_Service, carrying the submitting Officer, the submission time, the row count, a content checksum, and the batch report.
- **Feature_Builder**: The subsystem that reconstructs a feature row for an Acquisition_Case as of a specified timestamp using only the Event_Log and other point-in-time sources.
- **Model_Trainer**: The subsystem that trains, calibrates, evaluates, and versions the delay prediction model.
- **Censored_Row**: A candidate training row whose delay outcome is not knowable at the end of the prediction horizon, either because the Stage_Deadline falls after the end of the horizon or because the end of the horizon falls after the current date. A Censored_Row carries the label `CENSORED`.
- **Label_Base_Rate**: The proportion of rows labelled `DELAYED` within a labelled split, computed over the rows labelled `DELAYED` or `NOT_DELAYED` only.
- **Model_Monitor**: The subsystem that observes a promoted model version after promotion, comparing realized outcomes against predictions and detecting Feature_Drift.
- **Realized_Delay_Rate**: The observed proportion of Acquisition_Cases labelled `DELAYED` within a set of cases whose prediction horizon has elapsed.
- **Feature_Drift**: The divergence between the distribution of one feature over a promoted model version's training window and the distribution of that feature over current inference inputs, expressed as the population stability index over 10 quantile bins of the training-window distribution.
- **Prediction_Service**: The subsystem that produces a Risk_Probability, a Risk_Band, and Explanation_Factors for an Acquisition_Case.
- **Risk_Probability**: The calibrated probability, between 0 and 1, that an Acquisition_Case meets the delay definition of Q1 within the prediction horizon.
- **Risk_Band**: The ordinal classification of a Risk_Probability as `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.
- **Explanation_Factors**: The ranked per-case contributions that drove a Risk_Probability, each with a direction, a magnitude, and a plain-language label.
- **Priority_Engine**: The subsystem that computes a Priority_Score for an Acquisition_Case.
- **Priority_Score**: A bounded numeric ranking value combining Risk_Probability, Stage_Deadline pressure, and case value.
- **Intervention_Service**: The subsystem that produces the ranked queue of Acquisition_Cases needing officer attention, each with recommended actions.
- **Recommended_Action**: A suggested officer step attached to an Acquisition_Case in the intervention queue, with an accept, reject, or defer disposition.
- **Policy_Config**: The versioned, effective-dated store of configurable policy values: stage sets, statutory periods, OCR thresholds, Risk_Band cutoffs, Priority_Score weights, model promotion and monitoring thresholds, Retention_Periods, and language sets.
- **Retention_Service**: The subsystem that assigns stored attributes to Data_Categories, erases personal data whose Retention_Period has lapsed, and handles Data_Subject_Requests.
- **Data_Category**: A named class of stored data to which one Retention_Period applies, for example land record, owner contact, owner identity, document content, audit event, or model feature.
- **Retention_Period**: The configured duration for which data in one Data_Category is retained, measured from that data's retention start date, held in Policy_Config with an effective-from date.
- **Data_Subject_Request**: A request by a Citizen for access to, or correction of, the personal data BHUMISETU holds about that Citizen.
- **Localization_Service**: The subsystem that resolves display text and formats dates, numbers, and currency for a requested language.
- **Officer**: An authenticated government user of the Officer_Portal.
- **Citizen**: A landowner accessing the Citizen_Portal for a case in which the Citizen holds an Ownership_Record.

---

## Requirements

### Requirement 1: Officer Authentication and Session Management

**User Story:** As an acquisition officer, I want to sign in to a protected portal, so that land acquisition data is reachable only by authorised government staff.

#### Acceptance Criteria

1. WHEN an Officer submits a valid credential set, THE Auth_Service SHALL establish a session and record an Event of type `OFFICER_SIGNED_IN` carrying the officer identifier and the occurrence time.
2. IF an Officer submits an invalid credential set, THEN THE Auth_Service SHALL reject the attempt, return a response that distinguishes neither whether the account exists nor which field was wrong, and record an Event of type `OFFICER_SIGNIN_FAILED`.
3. IF 5 consecutive invalid credential submissions occur for one officer identifier within 15 minutes, THEN THE Auth_Service SHALL refuse further attempts for that identifier for 15 minutes and record an Event of type `OFFICER_ACCOUNT_LOCKED`.
4. THE Auth_Service SHALL expire an officer session 60 minutes after the most recent authenticated request on that session.
5. WHEN an Officer signs out, THE Auth_Service SHALL invalidate the session such that a subsequent request presenting the same session credential receives an unauthenticated response.
6. WHEN a request presents an expired or invalidated session credential, THE Auth_Service SHALL return an unauthenticated response and SHALL omit any Acquisition_Case data from that response.

### Requirement 2: Role-Based Access Control and Data Scope

**User Story:** As a district administrator, I want each government role to see only the cases within its jurisdiction, so that data access matches administrative authority.

#### Acceptance Criteria

1. THE Access_Control SHALL assign every Officer at least one role and, for each role, a jurisdiction scope expressed as a set of administrative areas.
2. WHEN an Officer requests a list of Acquisition_Cases, THE Access_Control SHALL restrict the result to cases whose administrative area falls within the requesting Officer's jurisdiction scope.
3. IF an Officer requests an Acquisition_Case outside the requesting Officer's jurisdiction scope, THEN THE Access_Control SHALL return a not-authorised response, SHALL omit case attributes from the response, and SHALL record an Event of type `ACCESS_DENIED`.
4. THE Access_Control SHALL permit only roles holding the stage-transition permission to change the Case_Stage of an Acquisition_Case.
5. THE Access_Control SHALL permit only roles holding the configuration permission to change a Policy_Config value.
6. WHEN a role's permission set or jurisdiction scope changes, THE Access_Control SHALL apply the new scope to the next request on any existing session for an Officer holding that role.
7. THE Access_Control SHALL evaluate every request against the same permission model regardless of whether the request originates from the Officer_Portal, the Citizen_Portal, or a direct interface call.
8. THE Access_Control SHALL permit only roles holding the import permission to submit an Import_Batch.

### Requirement 3: Citizen Case Access and Identity Verification

**User Story:** As a landowner, I want to reach my own case status without a full government login, so that I can follow my acquisition without visiting an office.

#### Acceptance Criteria

1. WHEN a Citizen submits a Case_Reference together with a mobile number recorded against an Ownership_Record on that Acquisition_Case, THE Citizen_Access_Service SHALL send a one-time passcode to that mobile number and record an Event of type `CITIZEN_PASSCODE_ISSUED`.
2. WHEN a Citizen submits a one-time passcode that matches the passcode issued for the presented Case_Reference within the passcode validity period, THE Citizen_Access_Service SHALL issue a citizen session scoped to that single Acquisition_Case.
3. THE Citizen_Access_Service SHALL expire a citizen session 15 minutes after issue.
4. IF a Citizen presents a Case_Reference for which the submitted mobile number matches no Ownership_Record, THEN THE Citizen_Access_Service SHALL return a response identical in content and within 200 ms of the median latency of the response returned for a matching pair, and SHALL send no passcode.
5. IF more than 5 passcode requests are submitted for one mobile number within 60 minutes, THEN THE Citizen_Access_Service SHALL refuse further passcode requests for that mobile number for 60 minutes.
6. IF 10 invalid passcode submissions occur for one Case_Reference within 24 hours, THEN THE Citizen_Access_Service SHALL refuse further passcode verification for that Case_Reference for 24 hours and record an Event of type `CITIZEN_ACCESS_LOCKED`.
7. WHILE a citizen session is active, THE Access_Control SHALL reject any request from that session for an Acquisition_Case other than the one to which the session is scoped.
8. THE Citizen_Access_Service SHALL record an Event for every citizen session issue, every citizen document retrieval, and every refused citizen access attempt.

_Depends on: Q6_

### Requirement 4: Immutable Event Log and Audit Trail

**User Story:** As a compliance auditor, I want every state change recorded once and never altered, so that the case history is defensible and reusable.

#### Acceptance Criteria

1. WHEN any subsystem changes the state of an Acquisition_Case, a Land_Parcel, an Ownership_Record, a Statutory_Notice, an Objection, an Award, a Payout, a Document, an Extracted_Field, a Validation_Issue, or a Policy_Config value, THE Event_Log SHALL append an Event recording the actor identifier, the affected entity identifier, the changed attributes with their prior and new values, the occurrence time, and the recording time.
2. THE Event_Log SHALL accept append operations only, such that a request to update or delete a stored Event returns a rejection.
3. THE Event_Log SHALL preserve the distinction between occurrence time and recording time on every Event.
4. WHEN an Event is appended with an occurrence time earlier than the occurrence time of an existing Event for the same entity, THE Event_Log SHALL store the Event and SHALL order the entity's history by occurrence time.
5. THE Event_Log SHALL return, for any entity identifier and any timestamp T, the ordered set of Events for that entity whose occurrence time is at or before T.
6. WHEN an erroneous Event is identified, THE Event_Log SHALL record the correction as a new compensating Event that references the erroneous Event identifier.
7. THE Event_Log SHALL be the single source from which the Citizen_Portal timeline and the Feature_Builder derive case history.
8. IF an Event append fails, THEN THE originating subsystem SHALL abandon the associated state change so that stored state and Event_Log content remain consistent.

### Requirement 5: Project and Acquisition Case Records

**User Story:** As an acquisition officer, I want to create and progress acquisition cases against a project, so that the statutory process is tracked in one place.

#### Acceptance Criteria

1. WHEN an Officer creates a Project, THE Case_Service SHALL record the project name, the implementing authority, the administrative area, the purpose category, and the sanctioned extent.
2. WHEN an Officer creates an Acquisition_Case for a Project, THE Case_Service SHALL assign a unique Case_Reference, set the Case_Stage to the first stage in the configured stage set, and record an Event of type `CASE_CREATED`.
3. THE Case_Service SHALL permit a Case_Stage transition only to a stage that the configured stage set declares as a successor of the current Case_Stage.
4. IF an Officer requests a Case_Stage transition that the configured stage set does not declare as a successor of the current Case_Stage, THEN THE Case_Service SHALL reject the transition and return the set of permitted successor stages.
5. WHEN a Case_Stage transition succeeds, THE Case_Service SHALL record an Event carrying the prior stage, the new stage, the transition occurrence date entered by the Officer, and the Officer identifier.
6. WHEN a Case_Stage transition succeeds, THE Notice_Service SHALL recompute the Stage_Deadline for the new Case_Stage from the Policy_Config values effective on the transition occurrence date.
7. IF a Case_Stage transition is requested WHILE an unresolved `BLOCKING` Validation_Issue exists on the Acquisition_Case, THEN THE Case_Service SHALL reject the transition and return the identifiers of the blocking issues.
8. THE Case_Service SHALL associate an Acquisition_Case with at least one Land_Parcel before permitting a transition out of the first Case_Stage.

_Depends on: Q8_

### Requirement 6: Land Parcel and Ownership Records

**User Story:** As an acquisition officer, I want parcel and ownership details recorded per case, so that notices and compensation reach the right people.

#### Acceptance Criteria

1. WHEN an Officer records a Land_Parcel, THE Case_Service SHALL record the state, district, tehsil, village, survey number, sub-division, classification, and extent with the extent unit.
2. THE Case_Service SHALL treat the combination of state, district, tehsil, village, survey number, and sub-division as unique across Land_Parcels.
3. IF an Officer records a Land_Parcel whose state, district, tehsil, village, survey number, and sub-division match an existing Land_Parcel, THEN THE Case_Service SHALL reject the record and return the identifier of the matching Land_Parcel.
4. WHEN an Officer records an Ownership_Record against a Land_Parcel, THE Case_Service SHALL record the owner name, the interest type, the ownership share, the validity start date, the optional validity end date, and the contact details.
5. THE Case_Service SHALL require that the ownership shares of the Ownership_Records concurrently valid for one Land_Parcel sum to 1 within a tolerance of 0.0001.
6. IF the concurrently valid ownership shares for a Land_Parcel sum to a value outside 1 ± 0.0001, THEN THE Validation_Engine SHALL raise a `BLOCKING` Validation_Issue against that Land_Parcel.
7. WHEN an Ownership_Record is superseded, THE Case_Service SHALL set the validity end date of the superseded record and retain the superseded record in a retrievable state.
8. THE Case_Service SHALL return, for any Land_Parcel and any date D, the set of Ownership_Records whose validity period includes D.

### Requirement 7: Statutory Notice Lifecycle and Deadline Tracking

**User Story:** As an acquisition officer, I want every statutory notice and its deadline tracked against configured legal periods, so that no legally mandated window is missed.

#### Acceptance Criteria

1. THE Notice_Service SHALL read every notice period, objection window, and Stage_Deadline from Policy_Config keyed by state, act, and effective-from date.
2. THE Notice_Service SHALL compute no legally significant date from a period value embedded in application code.
3. WHEN an Officer records the issue of a Statutory_Notice, THE Notice_Service SHALL record the notice type, the issuing authority, the issue date, the publication mode, and the affected Land_Parcels, and SHALL record an Event of type `NOTICE_ISSUED`.
4. WHEN a Statutory_Notice issue date is recorded, THE Notice_Service SHALL compute the response deadline as the issue date advanced by the Policy_Config response period effective on the issue date.
5. WHEN an Officer records service of a Statutory_Notice on an interested person, THE Notice_Service SHALL record the service date, the service mode, and the recipient Ownership_Record.
6. WHILE the current date is at or after the Stage_Deadline of an Acquisition_Case and the Acquisition_Case remains in the corresponding Case_Stage, THE Notice_Service SHALL mark the Acquisition_Case as deadline-breached and record an Event of type `DEADLINE_BREACHED`.
7. WHEN the current date reaches 30, 14, and 7 days before a Stage_Deadline, THE Notice_Service SHALL record an Event of type `DEADLINE_APPROACHING` carrying the remaining day count.
8. IF a Policy_Config period value changes, THEN THE Notice_Service SHALL retain the deadlines already computed for Statutory_Notices issued before the new effective-from date and SHALL apply the new value only to notices issued on or after that date.
9. THE Notice_Service SHALL return, for any Acquisition_Case, the ordered set of Statutory_Notices with each issue date, service date, response deadline, and breach state.

_Depends on: Q8_

### Requirement 8: Objection Intake and Disposal

**User Story:** As an acquisition officer, I want objections recorded and disposed within the statutory window, so that landowners' representations are answered on record.

#### Acceptance Criteria

1. WHEN an Officer records an Objection, THE Objection_Service SHALL record the objecting person, the related Ownership_Record where one exists, the receipt date, the grounds category, and the free-text substance.
2. WHEN an Objection receipt date is recorded, THE Objection_Service SHALL evaluate the receipt date against the response deadline of the governing Statutory_Notice and SHALL mark the Objection as within-window or out-of-window.
3. WHEN an Officer disposes of an Objection, THE Objection_Service SHALL record the disposal outcome, the disposal date, the reasons, the deciding Officer, and an Event of type `OBJECTION_DISPOSED`.
4. IF an Officer requests disposal of an Objection without recorded reasons, THEN THE Objection_Service SHALL reject the disposal and return the missing-field identifier.
5. WHILE an Objection remains undisposed and the current date is at or after the configured disposal deadline for that Objection, THE Objection_Service SHALL mark the Objection as disposal-overdue.
6. THE Objection_Service SHALL return, for any Acquisition_Case, the count of Objections by disposal state and the count marked disposal-overdue.

_Depends on: Q8_

### Requirement 9: Compensation Award and Payout Tracking

**User Story:** As an acquisition officer, I want award and payout records tracked per owner, so that disbursement progress is visible and arithmetically sound.

#### Acceptance Criteria

1. WHEN an Officer records an Award against an Ownership_Record, THE Compensation_Service SHALL record the itemised components with each component label and amount, the total amount, the currency, the determination date, and the determining authority.
2. THE Compensation_Service SHALL require that the recorded total amount of an Award equals the sum of the recorded component amounts within a tolerance of 0.01 in the recorded currency.
3. IF the recorded total amount of an Award differs from the sum of the recorded component amounts by more than 0.01, THEN THE Validation_Engine SHALL raise a `BLOCKING` Validation_Issue against that Award.
4. WHEN an Officer records a Payout against an Award, THE Compensation_Service SHALL record the amount, the payout date, the instrument reference, and the beneficiary, and SHALL record an Event of type `PAYOUT_RECORDED`.
5. IF the sum of Payouts against an Award would exceed the Award total amount, THEN THE Compensation_Service SHALL reject the Payout and return the remaining disbursable amount.
6. THE Compensation_Service SHALL derive the disbursement state of an Award as `UNPAID` when the Payout sum is 0, `PART_PAID` when the Payout sum is greater than 0 and less than the total, and `FULLY_PAID` when the Payout sum equals the total.
7. THE Compensation_Service SHALL return, for any Acquisition_Case, the aggregate awarded amount, the aggregate disbursed amount, and the count of Awards in each disbursement state.

_Depends on: Q9_

### Requirement 10: Document Upload and Storage

**User Story:** As an acquisition officer, I want to upload scanned land records against a case, so that source evidence is retrievable and digitizable.

#### Acceptance Criteria

1. WHEN an Officer uploads a Document against an Acquisition_Case or a Land_Parcel, THE Document_Service SHALL store the file, record the document type, the original filename, the byte size, the content type, the uploading Officer, the upload time, and a content checksum, and SHALL record an Event of type `DOCUMENT_UPLOADED`.
2. THE Document_Service SHALL accept files of content type PDF, JPEG, PNG, and TIFF, up to 25 MB per file.
3. IF an uploaded file exceeds 25 MB or presents a content type outside the accepted set, THEN THE Document_Service SHALL reject the upload and return the applicable limit or the accepted content type set.
4. IF an uploaded file produces a content checksum matching a Document already stored against the same Acquisition_Case, THEN THE Document_Service SHALL reject the upload and return the identifier of the existing Document.
5. WHEN a Document is stored, THE Document_Service SHALL set the processing state to `QUEUED` and enqueue an extraction job for the OCR_Service.
6. THE Document_Service SHALL serve a Document only over a time-limited access grant that expires within 15 minutes of issue.
7. WHEN a Document is served, THE Document_Service SHALL record an Event carrying the requesting actor identifier and the Document identifier.
8. THE Document_Service SHALL retain the uploaded bytes unchanged for the life of the Document, such that a later checksum computation over the stored bytes reproduces the recorded checksum.

### Requirement 11: Asynchronous OCR Extraction

**User Story:** As an acquisition officer, I want scanned records converted to structured field values without blocking my work, so that data entry effort falls.

#### Acceptance Criteria

1. WHEN an extraction job is dequeued, THE OCR_Service SHALL set the Document processing state to `PROCESSING` and record an Event of type `EXTRACTION_STARTED`.
2. WHEN extraction completes, THE OCR_Service SHALL record an Extraction carrying the full recognised text, the recognised script, and one Extracted_Field per configured target field.
3. THE OCR_Service SHALL record, for every Extracted_Field, the field name, the extracted value, the bounding box as page number with four page-relative coordinates, and a confidence score between 0 and 1.
4. THE OCR_Service SHALL accept documents in the scripts configured in Policy_Config and SHALL record the detected script on the Extraction.
5. IF the detected script of a Document falls outside the configured script set, THEN THE OCR_Service SHALL set the Document processing state to `UNSUPPORTED_SCRIPT` and SHALL record the detected script.
6. IF an extraction job fails, THEN THE OCR_Service SHALL retry the job up to 3 times with exponentially increasing delays and, on the final failure, SHALL set the Document processing state to `EXTRACTION_FAILED` and record the failure reason.
7. WHILE a Document processing state is `QUEUED` or `PROCESSING`, THE Officer_Portal SHALL present that state and SHALL remain responsive to other Officer requests.
8. THE OCR_Service SHALL complete extraction for a single-page Document of at most 2 MB within 60 seconds of job dequeue at the 95th percentile, measured over the trailing 100 completed jobs.
9. THE OCR_Service SHALL leave the stored Document bytes unchanged and SHALL write extraction output as separate records.
10. THE OCR_Service SHALL measure field-level extraction accuracy against a Holdout_Set of Documents whose correct field values are recorded by hand independently of any OCR_Service output.
11. THE OCR_Service SHALL treat an extracted value as an exact match to a hand-labelled value only WHERE the two values are equal character for character after leading and trailing whitespace is removed from each.
12. WHEN an extraction accuracy measurement completes, THE OCR_Service SHALL record an Extraction_Accuracy_Report stating the exact-match accuracy per field name, the exact-match accuracy per detected script, the Holdout_Set Document count, the labelled instance count per field name, and the measurement date.
13. THE Extraction_Accuracy_Report SHALL state, for every confidence threshold held in Policy_Config, the precision observed on the Holdout_Set across the Extracted_Fields that the threshold admits, reported per field name and per detected script.
14. WHEN the configured script set changes or the OCR_Service extraction model version changes, THE OCR_Service SHALL mark the current Extraction_Accuracy_Report as superseded and SHALL record a superseding Extraction_Accuracy_Report before an Extracted_Field produced under the changed configuration is set to Review_State `AUTO_ACCEPTED`.
15. THE OCR_Service SHALL retain every Extraction_Accuracy_Report with its measurement date and the extraction model version measured, such that the accuracy history of the OCR_Service is retrievable.

_Depends on: Q4, Q7_

### Requirement 12: OCR Confidence Routing and Human Correction

**User Story:** As an acquisition officer, I want low-confidence extractions routed to me for correction, so that unreliable machine output never enters the case record unchecked.

#### Acceptance Criteria

1. WHEN an Extracted_Field carries a confidence score at or above the configured auto-accept threshold, THE OCR_Service SHALL set the Review_State to `AUTO_ACCEPTED`.
2. WHEN an Extracted_Field carries a confidence score at or above the configured review threshold and below the configured auto-accept threshold, THE OCR_Service SHALL set the Review_State to `PENDING_REVIEW`.
3. WHEN an Extracted_Field carries a confidence score below the configured review threshold, THE OCR_Service SHALL discard the extracted value and set the Review_State to `MANUAL_ENTRY_REQUIRED`.
4. IF the mean confidence score across an Extraction's Extracted_Fields falls below the configured document-rejection threshold, THEN THE OCR_Service SHALL set the Document processing state to `REJECTED_LOW_QUALITY` and SHALL record a re-upload request against the Acquisition_Case.
5. WHEN an Officer opens an Extracted_Field for review, THE Officer_Portal SHALL present the extracted value together with the source Document region identified by the recorded bounding box.
6. WHEN an Officer confirms an Extracted_Field without changing the value, THE OCR_Service SHALL set the Review_State to `CONFIRMED` and record an Event carrying the Officer identifier.
7. WHEN an Officer changes the value of an Extracted_Field, THE OCR_Service SHALL set the Review_State to `CORRECTED`, retain the original extracted value and its confidence score, and record an Event carrying the prior value, the new value, and the Officer identifier.
8. THE Case_Service SHALL admit an Extracted_Field value into an Acquisition_Case, Land_Parcel, or Ownership_Record record only WHILE the Review_State of that Extracted_Field is `AUTO_ACCEPTED`, `CONFIRMED`, or `CORRECTED`.
9. THE Officer_Portal SHALL present the count of Extracted_Fields in Review_State `PENDING_REVIEW` and `MANUAL_ENTRY_REQUIRED` per Acquisition_Case.

_Depends on: Q4_

### Requirement 13: Validation Rule Execution and Duplicate Detection

**User Story:** As an acquisition officer, I want data problems detected automatically, so that defects surface before they reach a statutory milestone.

#### Acceptance Criteria

1. WHEN an Extracted_Field Review_State changes, an Ownership_Record changes, a Land_Parcel changes, an Award changes, or a Case_Stage changes, THE Validation_Engine SHALL evaluate the configured rule set for the affected Acquisition_Case.
2. THE Validation_Engine SHALL evaluate required-field rules that assert the presence of a non-empty value for every field the configured rule set marks mandatory at the current Case_Stage.
3. THE Validation_Engine SHALL evaluate date-chronology rules that assert each recorded date is at or after every date the configured rule set declares as its predecessor.
4. THE Validation_Engine SHALL evaluate cross-document consistency rules that assert a field appearing in more than one Document of the same Acquisition_Case carries the same admitted value in every Document.
5. THE Validation_Engine SHALL evaluate duplicate-detection rules that identify Land_Parcels sharing state, district, tehsil, village, and survey number, and Ownership_Records sharing an owner identity on the same Land_Parcel with overlapping validity periods.
6. WHEN a rule evaluates to a violation, THE Validation_Engine SHALL create a Validation_Issue carrying the rule identifier, the Severity declared by the rule, the identifiers of the offending entities, the observed values, and the detection time.
7. WHEN a rule that previously produced an open Validation_Issue evaluates without violation, THE Validation_Engine SHALL set that Validation_Issue resolution state to `RESOLVED_BY_CORRECTION` and record an Event.
8. THE Validation_Engine SHALL produce the same set of Validation_Issues for the same input data on repeated evaluation, such that a second evaluation with unchanged data creates no additional Validation_Issue.
9. THE Validation_Engine SHALL complete a full rule-set evaluation for one Acquisition_Case within 5 seconds at the 95th percentile, measured over the trailing 100 evaluations.

### Requirement 14: Validation Issue Severity and Resolution Audit

**User Story:** As an acquisition officer, I want a prioritised queue of data issues with a recorded resolution trail, so that I know what blocks progress and who resolved what.

#### Acceptance Criteria

1. THE Validation_Engine SHALL assign every Validation_Issue exactly one Severity from `BLOCKING`, `MAJOR`, `MINOR`, and `ADVISORY`.
2. THE Case_Service SHALL treat an open Validation_Issue of Severity `BLOCKING` as preventing a Case_Stage transition and SHALL treat Severities `MAJOR`, `MINOR`, and `ADVISORY` as permitting a Case_Stage transition.
3. WHEN an Officer requests the validation issue queue, THE Officer_Portal SHALL return open Validation_Issues ordered by Severity descending and then by detection time ascending, restricted to the Officer's jurisdiction scope.
4. WHEN an Officer resolves a Validation_Issue by correcting the underlying data, THE Validation_Engine SHALL set the resolution state to `RESOLVED_BY_CORRECTION` on the next rule evaluation.
5. WHEN an Officer waives a Validation_Issue, THE Validation_Engine SHALL require a waiver reason, SHALL set the resolution state to `WAIVED`, and SHALL record an Event carrying the Officer identifier, the reason, and the occurrence time.
6. THE Validation_Engine SHALL permit a waiver of a Validation_Issue of Severity `BLOCKING` only by an Officer holding the waiver permission for `BLOCKING` Severity.
7. THE Validation_Engine SHALL retain every Validation_Issue and its resolution history in a retrievable state after resolution.
8. THE Officer_Portal SHALL return, for any Validation_Issue, the ordered resolution history comprising each state change, the acting Officer, the reason where recorded, and the occurrence time.

### Requirement 15: Parcel and Project Geometry

**User Story:** As an acquisition officer, I want parcel and project boundaries stored as geometry, so that acquisitions can be examined spatially.

#### Acceptance Criteria

1. WHEN an Officer records a geometry for a Land_Parcel or a Project, THE GIS_Service SHALL store the geometry with its coordinate reference system identifier.
2. THE GIS_Service SHALL accept polygon and multipolygon geometries for Land_Parcels and Projects and point geometries for Statutory_Notice service locations.
3. IF a submitted geometry is not topologically valid, THEN THE GIS_Service SHALL reject the geometry and return the coordinates of the first detected invalidity.
4. THE GIS_Service SHALL return geometry to a requesting client in GeoJSON form with coordinates expressed in the WGS 84 coordinate reference system.
5. WHEN a Land_Parcel geometry is stored, THE GIS_Service SHALL compute the geodesic area and SHALL compare the computed area against the recorded extent.
6. IF the geodesic area computed from a Land_Parcel geometry differs from the recorded extent by more than 5 percent of the recorded extent, THEN THE Validation_Engine SHALL raise a `MAJOR` Validation_Issue against that Land_Parcel.
7. WHEN Land_Parcel geometries of one Acquisition_Case overlap by more than 1 percent of the smaller parcel's area, THE Validation_Engine SHALL raise a `MAJOR` Validation_Issue naming both Land_Parcels.
8. THE GIS_Service SHALL return the set of Land_Parcels whose geometry intersects a supplied bounding box within 2 seconds at the 95th percentile for a bounding box containing at most 5000 Land_Parcels.

### Requirement 16: Map Visualization and Case Navigation

**User Story:** As an acquisition officer, I want a map of projects and parcels with risk shading, so that I can see where problems cluster geographically.

#### Acceptance Criteria

1. WHEN an Officer opens the map view, THE Officer_Portal SHALL render the Land_Parcels and Projects within the current viewport that fall inside the Officer's jurisdiction scope.
2. WHILE the count of Land_Parcels in the current viewport exceeds 200, THE Officer_Portal SHALL render aggregated cluster markers carrying the contained parcel count in place of individual parcel geometries.
3. WHEN an Officer changes the map viewport, THE Officer_Portal SHALL request only the geometry intersecting the new viewport.
4. WHEN an Officer selects a rendered Land_Parcel or cluster member, THE Officer_Portal SHALL navigate to the case workspace of the associated Acquisition_Case.
5. WHERE the risk overlay is enabled, THE Officer_Portal SHALL shade each rendered Land_Parcel according to the Risk_Band of the associated Acquisition_Case and SHALL present the band-to-shade legend.
6. WHILE the risk overlay is enabled and an Acquisition_Case carries no current Risk_Probability, THE Officer_Portal SHALL render the associated Land_Parcels in a distinct not-scored shade and SHALL label that shade in the legend.
7. THE Officer_Portal SHALL render the initial map view within 4 seconds of the map view request at the 95th percentile on a connection of at least 5 Mbps downlink.
8. THE Officer_Portal SHALL present parcel identity, extent, Case_Reference, and Case_Stage for a selected Land_Parcel without a further map viewport request.

### Requirement 17: Point-in-Time Feature Generation

**User Story:** As a data engineer, I want features reconstructed exactly as they stood at a past moment, so that the delay model trains on information that was genuinely available.

#### Acceptance Criteria

1. WHEN the Feature_Builder is asked for a feature row for an Acquisition_Case as of timestamp T, THE Feature_Builder SHALL derive every feature value using only Events whose occurrence time is at or before T.
2. THE Feature_Builder SHALL exclude from a feature row as of T every attribute whose value first became known after T.
3. THE Feature_Builder SHALL exclude from a feature row every attribute derived from the outcome that the row is labelled with.
4. WHEN the Feature_Builder produces a feature row, THE Feature_Builder SHALL record the reference timestamp T, the feature set version, and the identifier of every Event consumed.
5. THE Feature_Builder SHALL produce identical feature values on repeated generation for the same Acquisition_Case and the same timestamp T, given an unchanged Event_Log.
6. THE Feature_Builder SHALL derive elapsed-duration features as the difference between T and the occurrence time of the relevant Event, expressed in whole days.
7. IF a feature cannot be derived for an Acquisition_Case as of T because the required Event is absent, THEN THE Feature_Builder SHALL emit an explicit missing marker for that feature rather than a substituted value, and SHALL record the reason.
8. THE Feature_Builder SHALL use the same code path to generate training rows and inference rows, such that a row generated for inference at time T equals the row generated for training at the same T.

_Depends on: Q1, Q2_

### Requirement 18: Delay Prediction Model Training and Evaluation

**User Story:** As a data scientist, I want the delay model trained and evaluated against declared thresholds, so that a weak model never reaches officers.

#### Acceptance Criteria

1. THE Model_Trainer SHALL label a candidate row according to the delay definition recorded in Policy_Config, comprising the stage transition in scope, the deadline baseline, and the prediction horizon.
2. THE Model_Trainer SHALL assign every candidate row exactly one label from `DELAYED`, `NOT_DELAYED`, and `CENSORED`.
3. WHERE the Stage_Deadline applicable to a candidate row falls after the end of that row's prediction horizon, THE Model_Trainer SHALL label that row `CENSORED`.
4. THE Model_Trainer SHALL label a candidate row `DELAYED` or `NOT_DELAYED` only WHERE the full prediction horizon measured from that row's reference timestamp has elapsed relative to the current date, and SHALL label the row `CENSORED` otherwise.
5. THE Model_Trainer SHALL exclude every row labelled `CENSORED` from the training split and from the evaluation split.
6. THE Model_Trainer SHALL record, with every recorded model version, the count of rows labelled `CENSORED` and the censoring rate expressed as that count divided by the total candidate row count.
7. THE Model_Trainer SHALL split training and evaluation data by time, such that every evaluation row carries a reference timestamp later than every training row's reference timestamp.
8. THE Model_Trainer SHALL record, with every recorded model version, the Label_Base_Rate of the training split and the Label_Base_Rate of the evaluation split.
9. THE Model_Trainer SHALL calibrate the model output so that the reported Risk_Probability is a calibrated probability.
10. THE Model_Trainer SHALL compute, on the temporally held-out evaluation split, the area under the precision-recall curve, the area under the receiver operating characteristic curve, the Brier score, and the expected calibration error over 10 equal-width probability bins.
11. THE Model_Trainer SHALL compute the precision-recall lift of an evaluation as the evaluation area under the precision-recall curve minus the evaluation split Label_Base_Rate, divided by the quantity 1 minus the evaluation split Label_Base_Rate.
12. THE Model_Trainer SHALL record a model version only WHEN the precision-recall lift is at least 0.30, the evaluation area under the precision-recall curve is at least 0.65, the area under the receiver operating characteristic curve is at least 0.75, and the expected calibration error is at most 0.05.
13. IF an evaluation metric falls below its configured threshold, THEN THE Model_Trainer SHALL withhold promotion of that model version, retain the evaluation report, and record an Event of type `MODEL_PROMOTION_WITHHELD`.
14. THE Model_Trainer SHALL present in the evaluation report, alongside every reported metric, the Label_Base_Rate of the split on which that metric was computed and the row count of that split.
15. IF the evaluation split Label_Base_Rate differs from the training split Label_Base_Rate by more than 0.10 in absolute value, THEN THE Model_Trainer SHALL record an Event of type `LABEL_BASE_RATE_SHIFT` carrying both Label_Base_Rates and SHALL state that Event identifier in the evaluation report.
16. WHEN a model version is promoted, THE Model_Trainer SHALL record the training data time range, the feature set version, the hyperparameters, the evaluation metrics, the Label_Base_Rate of each split, the censored row count, the censoring rate, and the promoting actor.
17. THE Model_Trainer SHALL compute a baseline metric set from a rule that predicts delay whenever the elapsed stage duration exceeds the Stage_Deadline, and SHALL record the promoted model's metrics alongside that baseline.
18. WHILE no model version is promoted, THE Prediction_Service SHALL return no Risk_Probability and THE Officer_Portal SHALL present the not-scored state for every Acquisition_Case.

_Depends on: Q1, Q2_

### Requirement 19: Risk Scoring and Risk Bands

**User Story:** As an acquisition officer, I want each case carrying a current risk score and band, so that I can rank my attention.

#### Acceptance Criteria

1. WHEN an Event is appended for an Acquisition_Case that changes a value in the current feature set, THE Prediction_Service SHALL generate a new Risk_Probability for that Acquisition_Case.
2. THE Prediction_Service SHALL generate a Risk_Probability for every Acquisition_Case not in a terminal Case_Stage at least once every 24 hours.
3. WHEN a Risk_Probability is generated, THE Prediction_Service SHALL record the probability, the model version, the feature set version, the reference timestamp, and the generation time.
4. THE Prediction_Service SHALL map a Risk_Probability to exactly one Risk_Band using the cutoffs held in Policy_Config.
5. THE Prediction_Service SHALL map Risk_Probabilities monotonically to Risk_Bands, such that a higher Risk_Probability never yields a lower Risk_Band under one cutoff set.
6. WHERE a district-specific Risk_Band cutoff set is configured WHILE the count of labelled historical Acquisition_Cases for that district is at or above the minimum district calibration count held in Policy_Config, THE Prediction_Service SHALL apply that district's cutoffs to Acquisition_Cases in that district and the platform-wide cutoffs to all other Acquisition_Cases.
7. WHERE a district-specific Risk_Band cutoff set is configured WHILE the count of labelled historical Acquisition_Cases for that district is below the minimum district calibration count held in Policy_Config, THE Prediction_Service SHALL apply the platform-wide cutoffs to Acquisition_Cases in that district and SHALL record an Event of type `DISTRICT_CUTOFFS_WITHHELD` carrying the district identifier, the observed labelled case count, and the configured minimum.
8. THE Prediction_Service SHALL count an Acquisition_Case towards a district's labelled historical case count only WHERE that Acquisition_Case carries a label of `DELAYED` or `NOT_DELAYED` under the delay definition recorded in Policy_Config.
9. WHEN a Risk_Band cutoff set changes, THE Prediction_Service SHALL recompute the Risk_Band of every affected Acquisition_Case from the stored Risk_Probability without regenerating the Risk_Probability.
10. THE Prediction_Service SHALL retain every generated Risk_Probability with its generation time, such that the score history of an Acquisition_Case is retrievable.
11. THE Officer_Portal SHALL present, alongside a displayed Risk_Band, whether the Risk_Band was derived from district-specific cutoffs or from the platform-wide cutoffs.
12. IF a Risk_Probability generation fails for an Acquisition_Case, THEN THE Prediction_Service SHALL retain the previous Risk_Probability, mark the score as stale with its generation time, and record an Event of type `SCORING_FAILED`.

_Depends on: Q1, Q5_

### Requirement 20: Prediction Explanation and Human-in-the-Loop Safeguards

**User Story:** As an acquisition officer, I want to see why a case scored as it did and to be able to disagree on record, so that the model advises rather than decides.

#### Acceptance Criteria

1. WHEN a Risk_Probability is generated, THE Prediction_Service SHALL generate Explanation_Factors comprising the ranked per-case feature contributions for that prediction.
2. THE Prediction_Service SHALL record, for every Explanation_Factor, the feature name, the plain-language label, the direction of the contribution, and the magnitude of the contribution.
3. WHEN the Officer_Portal presents a Risk_Probability or a Risk_Band, THE Officer_Portal SHALL present the top 5 Explanation_Factors for that prediction in the same view.
4. THE Officer_Portal SHALL present the model version and the prediction generation time alongside every displayed Risk_Probability.
5. THE BHUMISETU SHALL require a recorded Officer decision for every action that affects a Citizen, such that no Case_Stage transition, Objection disposal, Award change, Payout, or notice issue is initiated by a Risk_Probability, a Risk_Band, a Priority_Score, or a Recommended_Action.
6. WHEN an Officer disagrees with a Risk_Band or a Recommended_Action, THE Intervention_Service SHALL record an override carrying the Officer identifier, the overridden value, the Officer's stated reason, and the occurrence time.
7. WHILE an Officer override is in force for an Acquisition_Case, THE Officer_Portal SHALL present the override alongside the model output and SHALL retain the model output in the view.
8. THE Prediction_Service SHALL exclude the Risk_Probability, the Risk_Band, the Explanation_Factors, and the Priority_Score from every Citizen_Portal response.

_Depends on: Q6_

### Requirement 21: Priority Scoring and Intervention Queue

**User Story:** As a district administrator, I want a ranked queue of cases needing attention with suggested actions, so that scarce officer time goes to the cases where it changes the outcome.

#### Acceptance Criteria

1. WHEN a Risk_Probability, a Stage_Deadline, or a case value changes for an Acquisition_Case, THE Priority_Engine SHALL recompute the Priority_Score for that Acquisition_Case.
2. THE Priority_Engine SHALL compute the Priority_Score as a weighted combination of the Risk_Probability, the Stage_Deadline pressure expressed as remaining days normalised against the configured stage period, and the case value expressed as the aggregate awarded amount normalised against the configured reference amount.
3. THE Priority_Engine SHALL read every weight from Policy_Config and SHALL record the weight set version with each computed Priority_Score.
4. THE Priority_Engine SHALL produce a Priority_Score in the closed interval 0 to 100.
5. THE Priority_Engine SHALL produce a Priority_Score that does not decrease when the Risk_Probability increases and all other inputs are unchanged.
6. THE Priority_Engine SHALL produce a Priority_Score that does not decrease when the remaining days to the Stage_Deadline decrease and all other inputs are unchanged.
7. WHEN an Officer requests the intervention queue, THE Intervention_Service SHALL return Acquisition_Cases within the Officer's jurisdiction scope ordered by Priority_Score descending, and SHALL present for each the Case_Reference, the Case_Stage, the Risk_Band, the remaining days to the Stage_Deadline, and the Priority_Score.
8. WHEN an Acquisition_Case enters the intervention queue, THE Intervention_Service SHALL attach the Recommended_Actions that the configured action rules match to that Acquisition_Case's open Validation_Issues, undisposed Objections, pending Extracted_Field reviews, and breached or approaching Stage_Deadlines.
9. WHEN an Officer accepts, rejects, or defers a Recommended_Action, THE Intervention_Service SHALL record the disposition, the Officer identifier, and the occurrence time, and SHALL retain the Recommended_Action in a retrievable state.
10. THE Intervention_Service SHALL return the intervention queue for a jurisdiction containing at most 10000 Acquisition_Cases within 3 seconds at the 95th percentile.

### Requirement 22: Officer Dashboard

**User Story:** As a district administrator, I want a dashboard of case throughput and risk, so that I can see the state of the programme at a glance.

#### Acceptance Criteria

1. WHEN an Officer opens the dashboard, THE Officer_Portal SHALL present the count of Acquisition_Cases by Case_Stage, the count by Risk_Band, the count with a breached Stage_Deadline, the count of open Validation_Issues by Severity, the count of undisposed Objections, and the aggregate awarded and disbursed amounts, each restricted to the Officer's jurisdiction scope.
2. THE Officer_Portal SHALL present the distribution of Acquisition_Cases across Case_Stages and the trend of case counts by Risk_Band over the trailing 12 months as charts.
3. WHEN an Officer selects a dashboard metric, THE Officer_Portal SHALL navigate to the filtered list of Acquisition_Cases that the metric counts.
4. THE Officer_Portal SHALL present, alongside every dashboard metric, the time at which the underlying data was computed.
5. THE Officer_Portal SHALL render the dashboard within 3 seconds of the dashboard request at the 95th percentile for a jurisdiction containing at most 10000 Acquisition_Cases.
6. IF a dashboard metric cannot be computed, THEN THE Officer_Portal SHALL present the remaining metrics and SHALL label the uncomputed metric as unavailable with the failure time.

### Requirement 23: Officer Case Workspace and Document Viewer

**User Story:** As an acquisition officer, I want one workspace holding everything about a case, so that I can act without assembling context from separate systems.

#### Acceptance Criteria

1. WHEN an Officer opens an Acquisition_Case, THE Officer_Portal SHALL present the Case_Reference, the Project, the Case_Stage, the Stage_Deadline with remaining days, the Land_Parcels, the currently valid Ownership_Records, the Statutory_Notices, the Objections, the Awards with disbursement state, the open Validation_Issues, the current Risk_Band with Explanation_Factors, and the Documents.
2. WHEN an Officer opens a Document in the viewer, THE Officer_Portal SHALL render the Document pages and SHALL permit page navigation and zoom.
3. WHILE an Extracted_Field is selected in the viewer, THE Officer_Portal SHALL highlight the recorded bounding box region on the corresponding Document page.
4. WHEN an Officer opens the case timeline, THE Officer_Portal SHALL present the Events for that Acquisition_Case ordered by occurrence time, each with the event type, the occurrence time, and the acting actor.
5. THE Officer_Portal SHALL present internal officer notes only to actors holding an officer role.
6. THE Officer_Portal SHALL render the case workspace within 3 seconds of the case request at the 95th percentile for an Acquisition_Case holding at most 100 Land_Parcels and at most 200 Documents.

### Requirement 24: Citizen Portal Performance Budget

**User Story:** As a landowner on a weak rural mobile connection, I want the citizen portal to load and work, so that connectivity does not decide whether I can follow my own case.

#### Acceptance Criteria

1. THE Citizen_Portal SHALL transfer at most 150 KB of compressed markup, styles, scripts, and fonts to render the case status view, excluding Documents the Citizen requests.
2. THE Citizen_Portal SHALL produce a response body of at most 50 KB uncompressed for every Citizen_Portal interface response other than a Document transfer.
3. THE Citizen_Portal SHALL reach first contentful paint within 5 seconds and interactivity of the case status view within 8 seconds at the 95th percentile, measured over 100 consecutive cold loads of the case status view with an empty local cache on a network profile of 400 kbps downlink, 400 kbps uplink, and 2000 ms round-trip time.
4. THE Citizen_Portal SHALL render every Citizen-facing view legibly at a viewport width of 320 CSS pixels.
5. THE Citizen_Portal SHALL present the complete case status and timeline content as text, such that the content is readable when images and web fonts fail to load.
6. WHEN a Citizen request fails through a network error, THE Citizen_Portal SHALL retry the request up to 3 times with exponentially increasing delays starting at 1 second.
7. WHILE the device reports no network connectivity, THE Citizen_Portal SHALL present the most recently retrieved case status view from local storage together with the retrieval time and an explicit stale-data label.
8. IF no previously retrieved case status view exists in local storage WHILE the device reports no network connectivity, THEN THE Citizen_Portal SHALL present an offline message naming the action to retry.
9. WHEN a Citizen requests a Document, THE Citizen_Portal SHALL present the Document byte size before transfer begins and SHALL start the transfer on explicit Citizen confirmation.
10. THE Citizen_Portal SHALL paginate the case timeline at 20 Events per response.

_Depends on: Q3_

### Requirement 25: Citizen Case Status, Timeline, and Documents

**User Story:** As a landowner, I want to see where my case stands, what happened so far, and my own papers, so that I do not depend on office visits for information.

#### Acceptance Criteria

1. WHILE a citizen session is active, THE Citizen_Portal SHALL present the Case_Reference, the Project name, the current Case_Stage in plain language, the date the current Case_Stage began, and the next expected step in plain language.
2. WHILE a citizen session is active, THE Citizen_Portal SHALL present the Citizen's own Ownership_Records with the Land_Parcel identity, the recorded extent, and the ownership share.
3. WHILE a citizen session is active, THE Citizen_Portal SHALL present the Award total and the disbursement state for the Citizen's own Ownership_Records.
4. WHEN a Citizen opens the timeline, THE Citizen_Portal SHALL present the Events for that Acquisition_Case that the configured citizen-visible event set includes, ordered by occurrence time, each with a plain-language description and the occurrence date.
5. WHEN a Citizen opens the documents list, THE Citizen_Portal SHALL present the Documents attached to the Citizen's own Ownership_Records and Land_Parcels, each with the document type, the upload date, and the byte size.
6. WHEN a Citizen requests one of those Documents, THE Citizen_Portal SHALL serve the Document over a time-limited access grant and SHALL record an Event carrying the citizen session identifier and the Document identifier.
7. WHILE a citizen session is active, THE Citizen_Portal SHALL present the Statutory_Notices served on the Citizen with each notice type, service date, and response deadline.
8. WHILE an Objection raised by the Citizen is recorded, THE Citizen_Portal SHALL present that Objection's receipt date, disposal state, and disposal date where recorded.
9. THE Citizen_Portal SHALL present, for the current Case_Stage, the configured statutory period and the remaining days as plain-language text.

_Depends on: Q3, Q6, Q11_

_Note: criteria 1 to 9 describe a pull-only surface, so a Citizen learns of a change only by opening the Citizen_Portal. Whether BHUMISETU also pushes an outbound message when a case event occurs is Q11 and is unresolved. No notification requirement is stated until Q11 is confirmed._

### Requirement 26: Citizen Data Redaction and Privacy

**User Story:** As a landowner, I want other people's details and the government's internal notes kept out of my view, so that the portal does not leak data about me or others.

#### Acceptance Criteria

1. THE Citizen_Portal SHALL exclude from every response the personal data of Ownership_Records other than those held by the Citizen holding the session, comprising owner name, contact details, and government identifier.
2. THE Citizen_Portal SHALL present, for co-owned Land_Parcels, only the count of other Ownership_Records and the aggregate remaining ownership share.
3. THE Citizen_Portal SHALL exclude internal officer notes, Validation_Issue detail, Recommended_Actions, and Officer identity from every response.
4. THE Citizen_Portal SHALL exclude the Risk_Probability, the Risk_Band, the Explanation_Factors, and the Priority_Score from every response.
5. THE Citizen_Portal SHALL mask every government identifier presented to a Citizen such that at most the trailing 4 characters are rendered.
6. THE Citizen_Portal SHALL exclude the Awards and Payouts of Ownership_Records other than those held by the Citizen holding the session from every response.
7. WHEN a citizen session requests a resource, THE Access_Control SHALL evaluate the redaction rules at the interface boundary, such that a redacted attribute is absent from the response body rather than hidden in the rendered view.
8. THE Citizen_Portal SHALL record an Event for every Citizen data retrieval, carrying the citizen session identifier, the Acquisition_Case identifier, and the retrieval time.

_Depends on: Q6_

### Requirement 27: Localization and Multilingual Support

**User Story:** As a landowner who does not read English, I want the portal in my own language, so that the information is actually usable.

#### Acceptance Criteria

1. THE Localization_Service SHALL resolve every Citizen-facing display string in each language configured for the deployment.
2. THE Localization_Service SHALL resolve every Officer-facing display string in each language configured for the Officer_Portal.
3. WHEN a Citizen selects a configured language, THE Citizen_Portal SHALL render display strings, dates, numbers, and currency amounts in that language and its conventions, and SHALL retain that selection for the citizen session.
4. IF a display string has no translation in the requested language, THEN THE Localization_Service SHALL return the string in the deployment's default language and SHALL record the missing translation key.
5. THE BHUMISETU SHALL store, transmit, and render owner names, village names, and free-text fields in the scripts configured for the deployment without character substitution, such that a stored value read back equals the value written.
6. THE Citizen_Portal SHALL render the selected language without transferring a font file exceeding 40 KB compressed.
7. THE Officer_Portal SHALL present the recognised script of an Extraction alongside the Extracted_Fields.

_Depends on: Q7_

### Requirement 28: Policy Configuration and Change Control

**User Story:** As a district administrator, I want statutory periods, thresholds, and weights held as governed configuration, so that the platform can serve more than one state without a code change.

#### Acceptance Criteria

1. THE Policy_Config SHALL hold the Case_Stage set with declared successors, the statutory periods per state and act, the OCR confidence thresholds, the delay definition comprising the stage transition in scope, the deadline baseline and the prediction horizon, the model promotion metric thresholds, the model monitoring thresholds and cadence, the Risk_Band cutoffs, the minimum district calibration count, the Priority_Score weights, the Retention_Period per Data_Category, the erasable Data_Category set, the maximum Data_Subject_Request response period, the validation rule set with per-rule Severity, the citizen-visible event set, and the language and script sets.
2. THE Policy_Config SHALL store every value with a state key, an act key where applicable, and an effective-from date.
3. WHEN an Officer holding the configuration permission changes a Policy_Config value, THE Policy_Config SHALL retain the prior value with its effective period and SHALL record an Event carrying the key, the prior value, the new value, the effective-from date, and the Officer identifier.
4. THE Policy_Config SHALL return, for any key and any date D, the value effective on D.
5. IF a requested Policy_Config key has no value effective on the requested date, THEN THE requesting subsystem SHALL refuse the dependent operation and SHALL return the missing key and date.
6. THE Notice_Service SHALL apply the Policy_Config value effective on the relevant statutory event date rather than the current date when computing a deadline.
7. THE Policy_Config SHALL reject a Risk_Band cutoff set whose bands do not partition the interval 0 to 1 into contiguous non-overlapping ranges covering every probability.
8. THE Policy_Config SHALL reject an OCR threshold set in which the review threshold is not below the auto-accept threshold.
9. THE Policy_Config SHALL reject a change to an OCR confidence threshold that carries no reference to an Extraction_Accuracy_Report stating the precision observed on a Holdout_Set at the new threshold, and SHALL record that reference with the change as the recorded justification for the change.
10. THE Retention_Service SHALL apply the Retention_Period effective on the retention start date of an attribute rather than the Retention_Period effective on the current date when computing the erasure date for that attribute.

_Depends on: Q4, Q5, Q8, Q10_

### Requirement 29: Concurrent Modification Control

**User Story:** As an acquisition officer, I want a conflicting simultaneous edit rejected rather than silently applied over mine, so that a colleague's work is never lost without either of us being told.

#### Acceptance Criteria

1. THE Concurrency_Control SHALL maintain an Entity_Version for every Acquisition_Case, Land_Parcel, Ownership_Record, Statutory_Notice, Objection, Award, Payout, Document, Extracted_Field, and Validation_Issue, and SHALL increase that Entity_Version on every committed modification of the entity.
2. WHEN an Officer opens an entity for modification, THE Officer_Portal SHALL retain the Entity_Version observed at open time and SHALL present that Entity_Version with the subsequent modification request.
3. IF a modification request presents an Entity_Version other than the current Entity_Version of the target entity, THEN THE Concurrency_Control SHALL reject the modification and return a conflict response.
4. WHEN a modification is rejected as conflicting, THE Concurrency_Control SHALL return the name of every attribute whose stored value differs from the value the request presented as the prior value, the current stored value of each such attribute, the identifier of the actor whose modification produced the current Entity_Version, and the occurrence time of that modification.
5. WHEN a modification is rejected as conflicting, THE Event_Log SHALL append no Event for the rejected modification and THE Concurrency_Control SHALL leave the stored state of the target entity as it stood immediately before the rejected request.
6. WHEN two modification requests for one entity present the same Entity_Version, THE Concurrency_Control SHALL commit exactly one of the two requests and SHALL reject the other as conflicting.
7. WHEN two Officers request a Case_Stage transition out of the same Case_Stage of one Acquisition_Case, THE Case_Service SHALL record exactly one transition and THE Concurrency_Control SHALL reject the other request as conflicting.
8. WHERE two Officers submit a review of one Extracted_Field, THE Concurrency_Control SHALL commit the first submitted review, SHALL reject the second submitted review as conflicting, and SHALL return with the rejection the Review_State recorded by the first review, the value the first review recorded, and the identifier of the Officer who submitted the first review.
9. WHEN an Officer receives a conflict response, THE Officer_Portal SHALL present the current stored value of every conflicting attribute alongside the value the Officer submitted, and SHALL require the Officer to resubmit against the current Entity_Version.
10. THE Concurrency_Control SHALL apply the same conflict detection rule to a modification arriving from the Officer_Portal, the Citizen_Portal, the Import_Service, or a direct interface call.

### Requirement 30: Bulk Import of Existing Records

**User Story:** As a district administrator, I want the district's existing land records loaded in bulk, so that the platform can be adopted without re-entering the record base by hand.

#### Acceptance Criteria

1. WHEN an Officer holding the import permission submits a bulk record set, THE Import_Service SHALL create an Import_Batch recording the submitting Officer, the submission time, the submitted row count, and a checksum of the submitted content, and SHALL record an Event of type `IMPORT_BATCH_CREATED`.
2. THE Import_Service SHALL accept within one Import_Batch Land_Parcel rows, Ownership_Record rows, and Document attachment rows, each row naming the entity type it creates and the Acquisition_Case or Land_Parcel it attaches to.
3. THE Import_Service SHALL evaluate every submitted row against the same Validation_Engine rule set that applies to a manually entered record of the same entity type before committing that row.
4. WHERE a submitted row fails a Validation_Engine rule, THE Import_Service SHALL withhold the commit of that row and SHALL record a rejected-row entry carrying the submitted row identifier, the identifier of the failing rule, the offending attribute name, and the observed value.
5. THE Import_Service SHALL commit every submitted row that passes validation and SHALL withhold the commit of every submitted row that fails validation, such that a failing row does not withhold the commit of a passing row in the same Import_Batch.
6. WHEN an Import_Batch completes, THE Import_Service SHALL record a batch report stating the submitted row count, the committed row count, the rejected row count, and every rejected-row entry, and SHALL record an Event of type `IMPORT_BATCH_COMPLETED`.
7. THE Import_Service SHALL retain the batch report and every rejected-row entry in a retrievable state after the Import_Batch completes.
8. WHEN a row is committed by the Import_Service, THE Event_Log SHALL append an Event for the created entity carrying a provenance value of `IMPORTED` and the Import_Batch identifier.
9. IF a submitted Land_Parcel row carries a state, district, tehsil, village, survey number, and sub-division matching an existing Land_Parcel, THEN THE Import_Service SHALL withhold the commit of that row and SHALL record the identifier of the matching Land_Parcel in the rejected-row entry.
10. WHEN an Import_Batch attaches a Document, THE Document_Service SHALL apply the content type restriction, the size limit, the duplicate checksum rejection, the checksum recording, and the extraction enqueue that apply to an Officer upload.
11. THE Import_Service SHALL commit at least 10000 Land_Parcel rows per minute at the 95th percentile, measured over the trailing 10 completed Import_Batches of at least 10000 rows each.
12. IF an Import_Batch is interrupted before completion, THEN THE Import_Service SHALL retain every row already committed, SHALL mark the Import_Batch as interrupted with the identifier of the last processed row, and SHALL permit resumption from that row such that an already committed row is not committed a second time.
13. THE Officer_Portal SHALL present, for any Import_Batch, the batch state, the submitted, committed, and rejected row counts, and the rejected-row entries filtered by failing rule identifier.

_Proposed default: partial-commit semantics, as stated in criteria 5, 6, and 12. All-or-nothing commit is rejected as the default because a single malformed row would discard an entire district-scale submission and leave the operator no incremental path forward._

### Requirement 31: Post-Promotion Model Monitoring and Retraining Triggers

**User Story:** As a data scientist, I want a promoted model watched after it goes live, so that officers do not keep acting on scores from a model that has quietly stopped working.

#### Acceptance Criteria

1. THE Model_Monitor SHALL compute, at the cadence held in Policy_Config and at least once every 7 days, the Realized_Delay_Rate over the Acquisition_Cases whose prediction horizon elapsed since the previous computation, grouped by the Risk_Band that was assigned to each case at prediction time.
2. THE Model_Monitor SHALL compute, for each Risk_Band group, the divergence between the Realized_Delay_Rate of that group and the mean Risk_Probability predicted for that group, expressed as the absolute difference between the two.
3. IF the divergence for a Risk_Band group exceeds the calibration divergence threshold held in Policy_Config, THEN THE Model_Monitor SHALL record an Event of type `MODEL_CALIBRATION_DIVERGED` carrying the Risk_Band, the Realized_Delay_Rate, the mean predicted Risk_Probability, the case count, and the threshold, and SHALL notify every Officer holding the model-administration permission.
4. WHILE the count of Acquisition_Cases whose prediction horizon elapsed since the previous computation is below the minimum evaluable case count held in Policy_Config, THE Model_Monitor SHALL withhold the divergence comparison and SHALL record the observed evaluable case count with the withholding reason.
5. THE Model_Monitor SHALL compute, at the cadence held in Policy_Config and for every feature in the promoted model version's feature set, the Feature_Drift between the distribution of that feature over the promoted model version's training window and the distribution of that feature over the inference inputs of the trailing cadence period.
6. IF the Feature_Drift for a feature exceeds the drift threshold held in Policy_Config, THEN THE Model_Monitor SHALL record an Event of type `FEATURE_DRIFT_DETECTED` carrying the feature name, the computed Feature_Drift value, the threshold, and the boundaries of both compared windows, and SHALL notify every Officer holding the model-administration permission.
7. WHEN a `MODEL_CALIBRATION_DIVERGED` Event is recorded, THE Model_Monitor SHALL record an Event of type `RETRAINING_TRIGGERED` carrying the triggering condition and SHALL enqueue a training run for the Model_Trainer.
8. WHEN a `FEATURE_DRIFT_DETECTED` Event is recorded for at least the minimum drifted feature count held in Policy_Config within one drift computation, THE Model_Monitor SHALL record an Event of type `RETRAINING_TRIGGERED` carrying the drifted feature names and SHALL enqueue a training run for the Model_Trainer.
9. WHEN the elapsed period since the training data end date of the promoted model version reaches the maximum model age held in Policy_Config, THE Model_Monitor SHALL record an Event of type `RETRAINING_TRIGGERED` carrying the elapsed day count and SHALL enqueue a training run for the Model_Trainer.
10. WHEN a model version supersedes a previously promoted model version, THE Model_Trainer SHALL retain the superseded model version, its evaluation report, its Label_Base_Rates, its censored row count, its censoring rate, and its feature set version in a retrievable state.
11. THE Prediction_Service SHALL retain the model version recorded against every generated Risk_Probability, such that a Risk_Probability generated by a superseded model version remains attributable to that version and to that version's evaluation report.
12. THE Access_Control SHALL permit only roles holding the model-administration permission to promote a model version, to retire a model version, or to change a monitoring threshold or cadence.
13. IF a scheduled monitoring computation fails or does not complete within its configured cadence, THEN THE Model_Monitor SHALL record an Event of type `MODEL_MONITORING_UNAVAILABLE` carrying the failure reason and the time of the last successful computation, and THE Officer_Portal SHALL label every displayed Risk_Probability as unmonitored with that last successful computation time.
14. THE Officer_Portal SHALL present, for the promoted model version, the Realized_Delay_Rate and the mean predicted Risk_Probability per Risk_Band from the most recent completed computation together with that computation's time.

_Depends on: Q1, Q5_

### Requirement 32: Personal Data Retention and Data Subject Rights

**User Story:** As a landowner, I want to know what personal data the platform holds about me, to have it corrected through an officer, and to have my contact and identity data removed once its retention period lapses, so that my personal data is not held indefinitely without cause.

#### Acceptance Criteria

1. THE Policy_Config SHALL hold a Retention_Period for every Data_Category, keyed by state and by act where applicable, with an effective-from date, under the same storage and change-control rules that apply to every other Policy_Config value.
2. THE Retention_Service SHALL assign every stored attribute to exactly one Data_Category and SHALL return, for any attribute name, the Data_Category assigned to that attribute.
3. THE Retention_Service SHALL set the retention start date of a stored attribute to the occurrence time of the Event that moved the associated Acquisition_Case into a terminal Case_Stage.
4. WHILE an Acquisition_Case has not entered a terminal Case_Stage, THE Retention_Service SHALL hold the retention start date of every attribute associated with that Acquisition_Case as undetermined and SHALL withhold erasure of those attributes.
5. WHEN a Citizen submits a Data_Subject_Request of access type through an active citizen session, THE Retention_Service SHALL return the personal data recorded about that Citizen, comprising the owner name, the contact details, the government identifier masked under the rule of Requirement 26.5, the Ownership_Records held by that Citizen, and the Awards and Payouts recorded against those Ownership_Records, and SHALL record an Event of type `DATA_ACCESS_REQUEST_SERVED`.
6. THE Retention_Service SHALL complete a Data_Subject_Request within the maximum response period held in Policy_Config and SHALL record the receipt time and the completion time of every Data_Subject_Request.
7. WHEN a Citizen submits a Data_Subject_Request of correction type, THE Retention_Service SHALL record the target attribute, the currently recorded value, the value the Citizen asserts, and the receipt time, and SHALL route the request to the Officers whose jurisdiction scope contains the affected Acquisition_Case.
8. THE Retention_Service SHALL apply no Citizen-submitted value directly to a stored attribute, such that a change to recorded personal data reaches stored state only through an Officer modification recorded under Requirement 6 or Requirement 12.
9. WHEN an Officer disposes of a Data_Subject_Request of correction type, THE Retention_Service SHALL record the disposal outcome, the reasons, the deciding Officer, and the disposal time, and SHALL record an Event of type `CORRECTION_REQUEST_DISPOSED`.
10. WHEN the Retention_Period for a Data_Category lapses relative to the retention start date of a stored attribute in that Data_Category, THE Retention_Service SHALL erase the value of that attribute and SHALL record an Event of type `PERSONAL_DATA_ERASED` carrying the affected entity identifier, the attribute name, the Data_Category, and the erasure time.
11. THE Retention_Service SHALL restrict erasure to attributes in the Data_Categories that Policy_Config marks erasable, such that the Land_Parcel identity and geometry, the Ownership_Record share and validity period, the Award and Payout amounts, and the Event_Log persist after an erasure.
12. THE Retention_Service SHALL record an erasure as a compensating Event appended to the Event_Log, such that no stored Event is updated or deleted to effect an erasure.
13. WHEN an attribute is erased, THE Event_Log SHALL cease to return the value of that attribute in any Event payload and SHALL continue to return every Event with its actor, its affected entity identifier, its occurrence time, its recording time, and its ordering unchanged.
14. IF no Retention_Period value is effective on the retention start date of an attribute, THEN THE Retention_Service SHALL withhold erasure of that attribute and SHALL record the missing key and the retention start date.
15. THE Retention_Service SHALL return, for any Ownership_Record, the Data_Categories held against that record, the retention start date where determined, and the erasure date computed from the effective Retention_Period for each Data_Category.

_Depends on: Q6, Q10_

---

## Traceability of Scope Areas to Requirements

| Scope area | Requirements |
|---|---|
| Government officer portal | 1, 2, 16, 22, 23, 29, 30 |
| Low-bandwidth citizen portal | 3, 24, 25, 26, 27 |
| Document digitization | 10, 11, 12, 30 |
| Extraction accuracy measurement | 11, 28 |
| Validation engine | 13, 14, 30 |
| GIS | 15, 16 |
| ML delay prediction | 17, 18, 19, 20 |
| Model observability after promotion | 18, 31 |
| Priority and intervention queue | 21 |
| Auth and RBAC | 1, 2, 3, 26, 31 |
| Audit and immutability | 4, 12, 14, 20, 28, 29, 30, 32 |
| Concurrency and lost-update prevention | 29 |
| Core land acquisition domain | 5, 6, 7, 8, 9 |
| Record migration and bulk import | 30 |
| Personal data protection and retention | 3, 26, 32 |
| Configurability | 7, 12, 19, 21, 27, 28, 31, 32 |
