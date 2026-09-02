from __future__ import annotations

import ast
from pathlib import Path


API_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = API_ROOT.parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
APP_SERVICES = API_ROOT / "app" / "services"

CHECKED_FILES = tuple(ML_SRC.rglob("*.py")) + tuple(
    path
    for path in (
        APP_SERVICES / "prediction.py",
        APP_SERVICES / "priority.py",
        APP_SERVICES / "intervention.py",
    )
    if path.exists()
)
BANNED_DOMAIN_SERVICES = frozenset(
    {
        "app.services.case",
        "app.services.compensation",
        "app.services.objection",
    }
)


def test_model_and_decision_services_import_no_mutating_domain_service() -> None:
    offences: list[str] = []
    for path in CHECKED_FILES:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            module_names = _imported_modules(node)
            for module in module_names:
                if any(
                    module == banned or module.startswith(f"{banned}.")
                    for banned in BANNED_DOMAIN_SERVICES
                ):
                    offences.append(f"{path.relative_to(REPO_ROOT)} imports {module}")

    assert not offences, "mutating domain imports found: " + "; ".join(offences)


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module:
        return (node.module,)
    return ()
