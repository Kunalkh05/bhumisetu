"""Initial seed script for local BHUMISETU development environment.

Populates:
1. Platform & Maharashtra Policy Configuration
2. Administrative Hierarchy (MH -> Pune -> Haveli -> Wagholi)
3. Administrator Role with full permissions and jurisdiction scope
4. Dev Officer account
5. Sample Infrastructure Project
6. Sample Acquisition Cases across different lifecycle stages
7. Land Parcels, Case-Parcel associations, and Ownership Records
8. Active dev sessions in Redis for both Officer and Citizen portals
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

# Ensure api app is in PYTHONPATH
api_root = Path(__file__).resolve().parents[2] / "apps" / "api"
sys.path.insert(0, str(api_root))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models import load_all_models
load_all_models()
from app.models.jurisdiction import AdministrativeArea
from app.models.officer import Officer, Role, OfficerRole, JurisdictionScope
from app.models.policy import PolicyConfig, PLATFORM_WIDE
from app.models.project import Project
from app.models.acquisition_case import AcquisitionCase
from app.models.land_parcel import LandParcel
from app.models.case_parcel import CaseParcel
from app.models.ownership_record import OwnershipRecord
from app.models.dashboard import DashboardSnapshot
from app.models.extraction_accuracy_report import ExtractionAccuracyReport
from app.security.permissions import PERMISSIONS
from app.security.auth import (
    RedisOfficerSessionBackend,
    OFFICER_SESSION_SECONDS,
    CITIZEN_SESSION_SECONDS,
    _key,
    _citizen_key,
    _encode,
    _encode_citizen,
)
import redis


DEV_OFFICER_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
DEV_ROLE_ID = uuid.UUID("b0000000-0000-0000-0000-000000000001")
DEV_OFFICER_TOKEN = "dev_officer_session_token_12345"
DEV_OFFICER_CSRF = "dev_officer_csrf_token_12345"
DEV_CITIZEN_TOKEN = "dev_citizen_session_token_12345"


def seed_extraction_report(session: Session) -> int:
    report = session.execute(select(ExtractionAccuracyReport).where(ExtractionAccuracyReport.id == 1)).scalar_one_or_none()
    if not report:
        report = ExtractionAccuracyReport(
            id=1,
            extraction_model_version="v1.0.0",
            script_set_version="v1.0.0",
            holdout_manifest_hash="manifest_hash_dev_001",
            accuracy_by_field={"survey_number": 0.95, "extent": 0.94},
            accuracy_by_script={"devanagari": 0.93, "latin": 0.96},
            holdout_document_count=50,
            labelled_instance_count_by_field={"survey_number": 50, "extent": 50},
            precision_at_threshold={"0.92": 0.98},
            measurement_date=date(2021, 1, 1),
        )
        session.add(report)
        session.flush()
    return 1


def seed_policy_config(session: Session) -> int:
    from scripts.seed.policy_config import all_policy_fixture_rows

    count = 0
    existing = {
        (row.policy_key, row.state_key, row.act_key or "", row.effective_from)
        for row in session.execute(
            select(
                PolicyConfig.policy_key,
                PolicyConfig.state_key,
                PolicyConfig.act_key,
                PolicyConfig.effective_from,
            )
        ).all()
    }

    for row in all_policy_fixture_rows():
        key_tuple = (row.policy_key, row.state_key, row.act_key or "", row.effective_from)
        if key_tuple not in existing:
            just_id = 1 if row.policy_key.startswith('ocr.threshold.') else row.justification_report_id
            pc = PolicyConfig(
                policy_key=row.policy_key,
                state_key=row.state_key,
                act_key=row.act_key,
                effective_from=row.effective_from,
                value=row.value,
                justification_report_id=just_id,
                created_by=DEV_OFFICER_ID,
            )
            session.add(pc)
            count += 1
    
    # Also add for state "MH" mirroring "SYNTH-MH"
    synth_mh_rows = [
        row for row in all_policy_fixture_rows() if row.state_key == "SYNTH-MH"
    ]
    for row in synth_mh_rows:
        key_tuple = (row.policy_key, "MH", row.act_key or "", row.effective_from)
        if key_tuple not in existing:
            just_id = 1 if row.policy_key.startswith('ocr.threshold.') else row.justification_report_id
            pc = PolicyConfig(
                policy_key=row.policy_key,
                state_key="MH",
                act_key=row.act_key,
                effective_from=row.effective_from,
                value=row.value,
                justification_report_id=just_id,
                created_by=DEV_OFFICER_ID,
            )
            session.add(pc)
            count += 1

    session.flush()
    return count


def seed_administrative_areas(session: Session) -> None:
    areas = [
        # Root state
        {"code": "MH", "area_type": "state", "name": "Maharashtra", "parent_code": None},
        {"code": "SYNTH-MH", "area_type": "state", "name": "Synthetic State MH", "parent_code": None},
        # Districts
        {"code": "MH-PUN", "area_type": "district", "name": "Pune", "parent_code": "MH"},
        {"code": "SYNTH-DISTRICT-001", "area_type": "district", "name": "Synthetic District 001", "parent_code": "SYNTH-MH"},
        # Tehsils
        {"code": "MH-PUN-HAV", "area_type": "tehsil", "name": "Haveli", "parent_code": "MH-PUN"},
        {"code": "SYNTH-TALUKA-001", "area_type": "tehsil", "name": "Synthetic Taluka 001", "parent_code": "SYNTH-DISTRICT-001"},
        # Villages
        {"code": "MH-PUN-HAV-001", "area_type": "village", "name": "Wagholi", "parent_code": "MH-PUN-HAV"},
        {"code": "SYNTH-VILLAGE-001", "area_type": "village", "name": "Synthetic Village 001", "parent_code": "SYNTH-TALUKA-001"},
    ]

    for a in areas:
        exists = session.execute(
            select(AdministrativeArea.code).where(AdministrativeArea.code == a["code"])
        ).scalar_one_or_none()
        if not exists:
            if a["parent_code"] is None:
                session.execute(
                    text(
                        "INSERT INTO administrative_area (code, area_type, name, parent_code) "
                        "VALUES (:code, :area_type, :name, NULL)"
                    ),
                    a,
                )
            else:
                session.execute(
                    text(
                        "INSERT INTO administrative_area (code, area_type, name, parent_code) "
                        "VALUES (:code, :area_type, :name, :parent_code)"
                    ),
                    a,
                )
    session.flush()


def seed_officer_and_roles(session: Session) -> None:
    role = session.execute(select(Role).where(Role.id == DEV_ROLE_ID)).scalar_one_or_none()
    if not role:
        role = Role(
            id=DEV_ROLE_ID,
            key="super_admin",
            name="Super Administrator",
            permissions=list(PERMISSIONS),
        )
        session.add(role)
        session.flush()

        scope1 = JurisdictionScope(role_id=DEV_ROLE_ID, area_code="MH")
        scope2 = JurisdictionScope(role_id=DEV_ROLE_ID, area_code="SYNTH-MH")
        session.add_all([scope1, scope2])
        session.flush()

    officer = session.execute(select(Officer).where(Officer.id == DEV_OFFICER_ID)).scalar_one_or_none()
    if not officer:
        officer = Officer(
            id=DEV_OFFICER_ID,
            officer_code="admin",
            display_name="Super Admin Officer",
            designation="District Collector",
            credential_hash="$argon2id$v=19$m=65536,t=3,p=4$placeholder",
            is_active=True,
        )
        session.add(officer)
        session.flush()

        officer_role = OfficerRole(officer_id=DEV_OFFICER_ID, role_id=DEV_ROLE_ID)
        session.add(officer_role)
        session.flush()


def seed_projects_and_cases(session: Session) -> None:
    proj = session.execute(select(Project).where(Project.id == 1)).scalar_one_or_none()
    if not proj:
        proj = Project(
            id=1,
            name="Pune Ring Road Expressway Phase 1",
            implementing_authority="Maharashtra State Road Development Corp (MSRDC)",
            area_code="MH-PUN",
            purpose_category="Infrastructure / Transportation",
            sanctioned_extent=Decimal("450.5000"),
            extent_unit="hectare",
        )
        session.add(proj)
        session.flush()

    cases_data = [
        {
            "id": 1,
            "case_reference": "MH-PUN-2024-0001",
            "project_id": 1,
            "state_key": "MH",
            "act_key": "RFCTLARR_2013",
            "area_code": "MH-PUN-HAV-001",
            "stage_key": "intake",
            "stage_set_effective_from": date(2021, 1, 1),
            "stage_entered_on": date(2024, 6, 1),
            "stage_deadline": date(2025, 12, 31),
            "open_blocking_count": 0,
            "deadline_breached": False,
            "is_terminal": False,
            "entity_version": 1,
        },
        {
            "id": 2,
            "case_reference": "MH-PUN-2024-0002",
            "project_id": 1,
            "state_key": "MH",
            "act_key": "RFCTLARR_2013",
            "area_code": "MH-PUN-HAV-001",
            "stage_key": "preliminary_notice",
            "stage_set_effective_from": date(2021, 1, 1),
            "stage_entered_on": date(2024, 7, 15),
            "stage_deadline": date(2025, 12, 31),
            "open_blocking_count": 0,
            "deadline_breached": False,
            "is_terminal": False,
            "entity_version": 1,
        },
        {
            "id": 3,
            "case_reference": "MH-PUN-2024-0003",
            "project_id": 1,
            "state_key": "MH",
            "act_key": "RFCTLARR_2013",
            "area_code": "MH-PUN-HAV-001",
            "stage_key": "objection_window",
            "stage_set_effective_from": date(2021, 1, 1),
            "stage_entered_on": date(2024, 8, 1),
            "stage_deadline": date(2025, 12, 31),
            "open_blocking_count": 1,
            "deadline_breached": False,
            "is_terminal": False,
            "entity_version": 1,
        },
    ]

    for c in cases_data:
        exists = session.execute(
            select(AcquisitionCase.id).where(AcquisitionCase.id == c["id"])
        ).scalar_one_or_none()
        if not exists:
            case = AcquisitionCase(**c)
            session.add(case)
    session.flush()

    parcels_data = [
        {
            "id": 1,
            "state_key": "MH",
            "district": "Pune",
            "tehsil": "Haveli",
            "village": "Wagholi",
            "survey_number": "104",
            "sub_division": "1A",
            "classification": "Agricultural",
            "extent": Decimal("2.4500"),
            "extent_unit": "hectare",
            "area_code": "MH-PUN-HAV-001",
            "entity_version": 1,
        },
        {
            "id": 2,
            "state_key": "MH",
            "district": "Pune",
            "tehsil": "Haveli",
            "village": "Wagholi",
            "survey_number": "104",
            "sub_division": "1B",
            "classification": "Agricultural",
            "extent": Decimal("1.8000"),
            "extent_unit": "hectare",
            "area_code": "MH-PUN-HAV-001",
            "entity_version": 1,
        },
        {
            "id": 3,
            "state_key": "MH",
            "district": "Pune",
            "tehsil": "Haveli",
            "village": "Wagholi",
            "survey_number": "105",
            "sub_division": "2",
            "classification": "Agricultural",
            "extent": Decimal("3.1200"),
            "extent_unit": "hectare",
            "area_code": "MH-PUN-HAV-001",
            "entity_version": 1,
        },
    ]

    for p in parcels_data:
        exists = session.execute(
            select(LandParcel.id).where(LandParcel.id == p["id"])
        ).scalar_one_or_none()
        if not exists:
            parcel = LandParcel(**p)
            session.add(parcel)
    session.flush()

    cp_links = [(1, 1), (1, 2), (2, 3)]
    for cid, pid in cp_links:
        exists = session.execute(
            select(CaseParcel).where(CaseParcel.case_id == cid, CaseParcel.parcel_id == pid)
        ).scalar_one_or_none()
        if not exists:
            session.add(CaseParcel(case_id=cid, parcel_id=pid))
    session.flush()

    owners_data = [
        {
            "id": 1,
            "parcel_id": 1,
            "owner_name": "Ramesh Kisan Patil",
            "owner_identity_key": "AADHAAR_HASH_001",
            "interest_type": "title_holder",
            "share": Decimal("0.5000"),
            "valid_from": date(2020, 1, 1),
            "contact_mobile": "9876543210",
            "contact_mobile_hash": b"MOBILE_HASH_001",
            "entity_version": 1,
        },
        {
            "id": 2,
            "parcel_id": 1,
            "owner_name": "Suresh Kisan Patil",
            "owner_identity_key": "AADHAAR_HASH_002",
            "interest_type": "title_holder",
            "share": Decimal("0.5000"),
            "valid_from": date(2020, 1, 1),
            "contact_mobile": "9876543211",
            "contact_mobile_hash": b"MOBILE_HASH_002",
            "entity_version": 1,
        },
        {
            "id": 3,
            "parcel_id": 2,
            "owner_name": "Anand Rao Deshmukh",
            "owner_identity_key": "AADHAAR_HASH_003",
            "interest_type": "title_holder",
            "share": Decimal("1.0000"),
            "valid_from": date(2019, 6, 1),
            "contact_mobile": "9876543212",
            "contact_mobile_hash": b"MOBILE_HASH_003",
            "entity_version": 1,
        },
    ]
    for o in owners_data:
        exists = session.execute(
            select(OwnershipRecord.id).where(OwnershipRecord.id == o["id"])
        ).scalar_one_or_none()
        if not exists:
            session.add(OwnershipRecord(**o))
    session.flush()


def seed_redis_sessions(redis_url: str = "redis://localhost:6379/0") -> None:
    client = redis.from_url(redis_url)

    client.setex(
        _key(DEV_OFFICER_TOKEN),
        OFFICER_SESSION_SECONDS * 24,
        _encode(DEV_OFFICER_ID, DEV_OFFICER_CSRF),
    )
    print(f"Officer session seeded: token={DEV_OFFICER_TOKEN}")

    client.setex(
        _citizen_key(DEV_CITIZEN_TOKEN),
        CITIZEN_SESSION_SECONDS * 24,
        _encode_citizen(subject_id="CITIZEN_001", case_id=1, owner_record_ids=(1, 2)),
    )
    print(f"Citizen session seeded: token={DEV_CITIZEN_TOKEN}")


def main() -> None:
    engine = get_engine()
    with Session(bind=engine) as session:
        print("Seeding Administrative Hierarchy...")
        seed_administrative_areas(session)

        print("Seeding Officers and Roles...")
        seed_officer_and_roles(session)

        print("Seeding Extraction Accuracy Report...")
        seed_extraction_report(session)

        print("Seeding Policy Configuration...")
        count = seed_policy_config(session)
        print(f"  Added {count} policy config rows.")

        print("Seeding Projects, Cases, and Parcels...")
        seed_projects_and_cases(session)

        session.commit()
        print("Database seed committed successfully!")

    try:
        seed_redis_sessions()
    except Exception as exc:
        print(f"Warning: Could not seed Redis: {exc}")


if __name__ == "__main__":
    main()
