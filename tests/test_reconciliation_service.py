"""Unit test stubs for the reconciliation service scaffold."""

import pytest

from ops_summary.filters import SummaryFilters
from ops_summary.services.reconciliation_service import ReconciliationService


class DummyRepo:
    """Minimal in-memory repository double used for future tests."""

    def fetch_by_filters(self, filters):
        return []


@pytest.fixture
def service() -> ReconciliationService:
    """Provide a reconciliation service wired to dummy repositories."""
    production_repo = DummyRepo()
    inspection_repo = DummyRepo()
    shipping_repo = DummyRepo()
    return ReconciliationService(production_repo, inspection_repo, shipping_repo)


def test_build_summary_returns_expected_tuple_shape(service: ReconciliationService):
    """Placeholder test describing the expected build_summary contract."""
    pytest.skip("Implement once reconciliation logic is available")


def test_alignment_handles_missing_sources(service: ReconciliationService):
    """Placeholder ensuring AC2/AC4 behavior is validated later."""
    pytest.skip("Implement once reconciliation alignment exists")


def test_filters_apply_priority_rules(service: ReconciliationService):
    """Placeholder for AC6-AC8 filter/priority expectations."""
    pytest.skip("Implement once filtering logic exists")
