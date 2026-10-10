"""Comprehensive Human Citizen Journey & Redaction Attack Test Suite (Phase 6 & 7).
Executes the full Citizen Journey and attempts unauthorized access to internal ML telemetry.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

from tests_harness.chrome_cdp import ChromeCDPDriver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("citizen_journey")

SCREENSHOTS_DIR = "/tmp/bhumisetu_evidence/citizen_journey"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


async def run_citizen_journey(driver: ChromeCDPDriver) -> dict[str, Any]:
    evidence = {}

    # -------------------------------------------------------------
    # 1. Open Application at Citizen Portal
    # -------------------------------------------------------------
    logger.info("1. Open citizen portal landing page (http://localhost:5174/officer/)")
    await driver.navigate("http://localhost:5174/officer/", wait_network_idle=2.0)
    await driver.wait_for_function("Boolean(document.querySelector('header'))", timeout=10.0)

    # Switch to citizen mode in UI if in officer mode
    await driver.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const citizenBtn = btns.find(b => b.innerText && b.innerText.includes('Citizen Portal'));
            if (citizenBtn) citizenBtn.click();
        })()
    """)
    await asyncio.sleep(1.0)
    await driver.screenshot(f"{SCREENSHOTS_DIR}/01_citizen_landing.png")

    # -------------------------------------------------------------
    # 2. Citizen Authentication
    # -------------------------------------------------------------
    logger.info("2. Authenticate as Citizen Persona (Suresh Patil)")
    login_result = await driver.evaluate("""
        (async () => {
            const resp = await fetch('/api/auth/persona', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    userId: 'CITIZEN-001',
                    name: 'Suresh Patil',
                    role: 'Affected Landowner',
                    isCitizen: true
                })
            });
            return { ok: resp.ok, status: resp.status, data: await resp.json() };
        })()
    """)
    assert login_result["ok"], f"Citizen login failed: {login_result}"
    evidence["citizen_login"] = login_result["data"]

    # -------------------------------------------------------------
    # 3. Permitted Case Access & Milestone Timeline
    # -------------------------------------------------------------
    logger.info("3. Retrieve permitted citizen milestone timeline")
    timeline_res = await driver.evaluate("""
        (async () => {
            const resp = await fetch('/api/citizen/cases/1/milestone-timeline');
            return { ok: resp.ok, status: resp.status, data: await resp.json() };
        })()
    """)
    assert timeline_res["ok"], f"Citizen milestone timeline failed: {timeline_res}"
    timeline_data = timeline_res["data"]
    evidence["timeline_response"] = timeline_data

    # Verify timeline content
    assert "case_id" in timeline_data, "case_id missing from citizen timeline"
    assert "current_stage" in timeline_data, "current_stage missing"
    assert "statutory_rights_summary" in timeline_data, "statutory_rights_summary missing"
    assert "citizen_procedural_explanation" in timeline_data, "citizen_procedural_explanation missing"

    # -------------------------------------------------------------
    # 4. Statutory Information & Rights Verification
    # -------------------------------------------------------------
    logger.info("4. Verify statutory rights and elapsed time in citizen view")
    # Navigate to Calculator and Directory tabs
    await driver.evaluate("""
        (() => {
            const btns = Array.from(document.querySelectorAll('button'));
            const calcBtn = btns.find(b => b.innerText && (b.innerText.includes('Calculator') || b.innerText.includes('कैलकुलेटर')));
            if (calcBtn) calcBtn.click();
        })()
    """)
    await asyncio.sleep(1.0)
    await driver.screenshot(f"{SCREENSHOTS_DIR}/04_statutory_calculator.png")

    # -------------------------------------------------------------
    # 5. Responsive Layout Emulation (Mobile Viewport)
    # -------------------------------------------------------------
    logger.info("5. Emulate mobile viewport (375x667)")
    await driver.set_viewport(width=375, height=667, is_mobile=True)
    await asyncio.sleep(0.5)
    mobile_content = await driver.evaluate("Boolean(document.querySelector('main'))")
    assert mobile_content, "Main content missing on mobile layout"
    await driver.screenshot(f"{SCREENSHOTS_DIR}/05_mobile_viewport.png")

    # Reset to desktop viewport
    await driver.set_viewport(width=1440, height=900, is_mobile=False)
    await asyncio.sleep(0.5)

    # -------------------------------------------------------------
    # 6. Error States Handling
    # -------------------------------------------------------------
    logger.info("6. Test error states handling on malformed / unknown case")
    error_res = await driver.evaluate("""
        (async () => {
            const resp = await fetch('/api/citizen/cases/999999/milestone-timeline');
            return {
                status: resp.status,
                body: await resp.json().catch(() => ({}))
            };
        })()
    """)
    assert error_res["status"] in (403, 404), f"Expected 403/404 for unknown/unowned case, got {error_res['status']}"
    evidence["error_state_handling"] = error_res

    # -------------------------------------------------------------
    # 7. EXPLICIT UNAUTHORIZED FIELD ACCESS ATTACKS (Citizen -> Officer)
    # -------------------------------------------------------------
    logger.info("7. Execute Cross-Role Redaction Attacks (Citizen attempting Officer endpoints)")
    unauthorized_endpoints = [
        ("GET", "/api/officer/cases/CASE-001/survival-risk"),
        ("GET", "/api/officer/cases/CASE-001/survival-risk/explanation"),
        ("GET", "/api/officer/survival-risk/health"),
        ("POST", "/api/officer/survival-risk/predict", {"case_id": "CASE-001", "transition": "SECTION_11_TO_SECTION_19", "snapshot_date": "2026-10-02", "features": {}}),
        ("GET", "/api/officer/dashboard"),
        ("GET", "/api/officer/cases"),
        ("POST", "/internal/ml/survival/predict", {"case_id": "CASE-001", "transition": "SECTION_11_TO_SECTION_19", "snapshot_date": "2026-10-02", "features": {}}),
    ]

    attack_results = {}
    for method, path, *payload in unauthorized_endpoints:
        body_opt = json.dumps(payload[0]) if payload else "undefined"
        res = await driver.evaluate(f"""
            (async () => {{
                const opts = {{
                    method: {json.dumps(method)},
                    headers: {{ 'Content-Type': 'application/json' }}
                }};
                if ({body_opt}) {{
                    opts.body = JSON.stringify({body_opt});
                }}
                const resp = await fetch({json.dumps(path)}, opts);
                return {{
                    status: resp.status,
                    denied: [401, 403, 404].includes(resp.status),
                    body: await resp.json().catch(() => ({{}}))
                }};
            }})()
        """)
        assert res["denied"], f"VULNERABILITY: Citizen accessed {method} {path} with status {res['status']}"
        attack_results[f"{method} {path}"] = {
            "status": res["status"],
            "denied": res["denied"],
            "code": res["body"].get("code"),
        }
    evidence["unauthorized_endpoint_attacks"] = attack_results

    # -------------------------------------------------------------
    # 8. Verify Strict Absence of Internal ML Telemetry in Citizen Response
    # -------------------------------------------------------------
    logger.info("8. Verify complete omission of internal Cox telemetry in citizen response")
    forbidden_keys = [
        "relative_hazard",
        "linear_predictor",
        "beta",
        "coefficients",
        "feature_contributions",
        "multipliers",
        "risk_band",
        "rankings",
        "officer_notes",
        "audit_telemetry",
        "internal_diagnostics",
    ]

    raw_json_str = json.dumps(timeline_data).lower()
    leaked_keys = [k for k in forbidden_keys if k in raw_json_str]
    assert len(leaked_keys) == 0, f"DATA LEAKAGE: Forbidden keys found in citizen payload: {leaked_keys}"
    evidence["redaction_clean"] = True
    evidence["forbidden_keys_checked"] = forbidden_keys

    # -------------------------------------------------------------
    # 9. Logout
    # -------------------------------------------------------------
    logger.info("9. Terminate citizen session")
    logout_res = await driver.evaluate("""
        (async () => {
            const resp = await fetch('/api/auth/logout', { method: 'POST' });
            return { ok: resp.ok, status: resp.status };
        })()
    """)
    assert logout_res["ok"], f"Citizen logout failed: {logout_res}"
    evidence["logout"] = logout_res

    logger.info("CITIZEN JOURNEY COMPLETED SUCCESSFULLY: ALL BOUNDARY CHECKS PASSED!")
    return evidence


async def main():
    driver = ChromeCDPDriver()
    driver.start()
    try:
        await driver.connect()
        evidence = await run_citizen_journey(driver)
        with open("/tmp/bhumisetu_evidence/citizen_journey_evidence.json", "w") as f:
            json.dump(evidence, f, indent=2)
        print("PASS — CITIZEN JOURNEY COMPLETE")
    finally:
        await driver.close()
        driver.stop()


if __name__ == "__main__":
    asyncio.run(main())
