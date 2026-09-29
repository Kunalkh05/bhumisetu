# Testing Strategy — BHUMISETU Platform

## Overview
This document describes the testing strategy for the BHUMISETU platform,
covering unit tests, integration tests, end-to-end tests, and specialized
compliance tests.

## Test Pyramid

```
        ┌─────────┐
        │   E2E   │  ~10% — Browser-based workflows
        ├─────────┤
        │  Integ  │  ~30% — API endpoint + database tests
        ├─────────┤
        │  Unit   │  ~60% — Service logic, validators, utilities
        └─────────┘
```

## Test Categories

### Unit Tests
- **Location**: `bhumi-setu/apps/api/tests/test_*.py`
- **Framework**: pytest with hypothesis for property-based testing
- **Coverage Target**: 80% line coverage
- **Examples**:
  - `test_utils.py` — Utility helper functions
  - `test_compensation_calc.py` — Compensation calculation logic
  - `test_policy_validators.py` — Business rule validation
  - `test_validation_rules.py` — Input validation rules

### Integration Tests
- **Location**: `bhumi-setu/apps/api/tests/`
- **Database**: PostgreSQL test database with fixtures
- **Examples**:
  - `test_case_service.py` — Case CRUD with database
  - `test_import_service.py` — Data import pipeline
  - `test_citizen_access.py` — Citizen data access control
  - `test_gated_route.py` — Response gating middleware

### Compliance Tests
- **Purpose**: Verify regulatory requirements are met
- **Examples**:
  - `test_route_table.py` — Verify all endpoints have proper auth
  - `test_version_uniformity.py` — All responses include version
  - `test_field_coverage.py` — Required fields are populated
  - `test_rbac_matrix.py` — Role permissions enforced correctly
  - `test_signin_indistinguishability.py` — Auth timing side-channel prevention

### Performance Tests
- **Location**: `bhumi-setu/apps/api/tests/perf/`
- **Purpose**: Benchmark critical endpoints
- **Run**: On-demand, not in CI pipeline

### Property-Based Tests
- **Framework**: Hypothesis
- **Location**: Integrated into existing test files
- **Purpose**: Generate random inputs to find edge cases
- **Strategies**: `bhumi-setu/apps/api/tests/strategies.py`

## Running Tests

```bash
# Run all tests
cd bhumi-setu/apps/api
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_utils.py -v

# Run specific test class
pytest tests/test_compensation_calc.py::TestBasicCompensation -v

# Run with hypothesis (property-based) examples
pytest tests/ -k "hypothesis" --hypothesis-show-statistics

# Run only compliance tests
pytest tests/test_route_table.py tests/test_version_uniformity.py tests/test_rbac_matrix.py -v
```

## CI/CD Integration

Tests run automatically on:
1. **Pull Request**: All unit and integration tests
2. **Merge to main**: Full test suite including compliance
3. **Nightly**: Soak tests and performance benchmarks

### CI Pipeline Stages
```
1. Lint (ruff, mypy) → 2. Unit Tests → 3. Integration Tests → 4. Compliance → 5. Build
```

## Test Data Management

### Fixtures
- `tests/conftest.py` — Shared fixtures for database, auth, and test clients
- `tests/seed/` — Seed data for integration tests
- `tests/strategies.py` — Hypothesis strategies for property-based tests

### Database Fixtures
- Tests use a separate PostgreSQL database
- Fixtures create and tear down test data per test function
- No shared mutable state between test functions

## Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<Feature>` (e.g., `TestBasicCompensation`)
- Test methods: `test_<behavior>` (e.g., `test_market_value_uses_higher_rate`)
