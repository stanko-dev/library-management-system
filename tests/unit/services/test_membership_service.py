"""TDD unit tests for MembershipService — all repos mocked."""
import pytest
from decimal import Decimal

from models.reader import Reader
from models.enums import MembershipType
from storage.interfaces import ReaderRepository, FineRepository
from services.membership_service import MembershipService
from utils.exceptions import ReaderNotFoundError

# ── Helpers ───────────────────────────────────────────────────────────────────

def _reader(
    is_blocked: bool = False,
    overdue_count: int = 0,
    membership: MembershipType = MembershipType.STANDARD,
) -> Reader:
    return Reader("r1", "Alice", membership,
                  is_blocked=is_blocked, overdue_count=overdue_count)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def reader_repo(mocker):
    m = mocker.MagicMock(spec=ReaderRepository)
    m.get_by_id.return_value = _reader()
    return m


@pytest.fixture
def fine_repo(mocker):
    m = mocker.MagicMock(spec=FineRepository)
    m.total_unpaid_by_reader.return_value = Decimal("0")
    return m


@pytest.fixture
def svc(reader_repo, fine_repo) -> MembershipService:
    return MembershipService(
        reader_repo, fine_repo,
        max_unpaid_amount=Decimal("10.00"),
        max_overdue_count=3,
    )


# ── evaluate() ────────────────────────────────────────────────────────────────

class TestEvaluate:
    def test_reader_not_found_raises(self, svc, reader_repo):
        reader_repo.get_by_id.return_value = None
        with pytest.raises(ReaderNotFoundError):
            svc.evaluate("r1")

    def test_unpaid_above_threshold_blocks(self, svc, reader_repo, fine_repo):
        fine_repo.total_unpaid_by_reader.return_value = Decimal("15.00")
        reader = _reader()
        reader_repo.get_by_id.return_value = reader
        assert svc.evaluate("r1") is True
        assert reader.is_blocked is True

    def test_unpaid_exactly_at_threshold_blocks(self, svc, reader_repo, fine_repo):
        fine_repo.total_unpaid_by_reader.return_value = Decimal("10.00")
        reader = _reader()
        reader_repo.get_by_id.return_value = reader
        assert svc.evaluate("r1") is True

    def test_unpaid_below_threshold_does_not_block(self, svc, reader_repo, fine_repo):
        fine_repo.total_unpaid_by_reader.return_value = Decimal("9.99")
        reader = _reader()
        reader_repo.get_by_id.return_value = reader
        assert svc.evaluate("r1") is False
        assert reader.is_blocked is False

    def test_overdue_count_at_threshold_blocks(self, svc, reader_repo):
        reader = _reader(overdue_count=3)
        reader_repo.get_by_id.return_value = reader
        assert svc.evaluate("r1") is True

    def test_overdue_count_above_threshold_blocks(self, svc, reader_repo):
        reader = _reader(overdue_count=5)
        reader_repo.get_by_id.return_value = reader
        assert svc.evaluate("r1") is True

    def test_overdue_count_below_threshold_does_not_block(self, svc, reader_repo):
        reader = _reader(overdue_count=2)
        reader_repo.get_by_id.return_value = reader
        assert svc.evaluate("r1") is False

    def test_both_thresholds_exceeded_blocks(self, svc, reader_repo, fine_repo):
        fine_repo.total_unpaid_by_reader.return_value = Decimal("50.00")
        reader = _reader(overdue_count=10)
        reader_repo.get_by_id.return_value = reader
        assert svc.evaluate("r1") is True

    def test_unblocks_previously_blocked_reader_when_below_thresholds(
        self, svc, reader_repo, fine_repo
    ):
        reader = _reader(is_blocked=True, overdue_count=0)
        reader_repo.get_by_id.return_value = reader
        fine_repo.total_unpaid_by_reader.return_value = Decimal("0")
        result = svc.evaluate("r1")
        assert result is False
        assert reader.is_blocked is False

    def test_reader_repo_updated(self, svc, reader_repo, fine_repo):
        reader_repo.get_by_id.return_value = _reader()
        fine_repo.total_unpaid_by_reader.return_value = Decimal("0")
        svc.evaluate("r1")
        reader_repo.update.assert_called_once()

    def test_returns_true_when_blocked(self, svc, reader_repo, fine_repo):
        fine_repo.total_unpaid_by_reader.return_value = Decimal("99.00")
        reader_repo.get_by_id.return_value = _reader()
        assert svc.evaluate("r1") is True

    def test_returns_false_when_not_blocked(self, svc, reader_repo, fine_repo):
        fine_repo.total_unpaid_by_reader.return_value = Decimal("0")
        reader_repo.get_by_id.return_value = _reader(overdue_count=0)
        assert svc.evaluate("r1") is False

    def test_zero_unpaid_zero_overdue_does_not_block(self, svc, reader_repo, fine_repo):
        reader = _reader(overdue_count=0)
        reader_repo.get_by_id.return_value = reader
        fine_repo.total_unpaid_by_reader.return_value = Decimal("0")
        assert svc.evaluate("r1") is False


# ── block() ───────────────────────────────────────────────────────────────────

class TestBlock:
    def test_reader_not_found_raises(self, svc, reader_repo):
        reader_repo.get_by_id.return_value = None
        with pytest.raises(ReaderNotFoundError):
            svc.block("r1")

    def test_sets_is_blocked_true(self, svc, reader_repo):
        reader = _reader(is_blocked=False)
        reader_repo.get_by_id.return_value = reader
        svc.block("r1")
        assert reader.is_blocked is True

    def test_already_blocked_stays_blocked(self, svc, reader_repo):
        reader = _reader(is_blocked=True)
        reader_repo.get_by_id.return_value = reader
        svc.block("r1")
        assert reader.is_blocked is True

    def test_reader_repo_updated(self, svc, reader_repo):
        reader_repo.get_by_id.return_value = _reader()
        svc.block("r1")
        reader_repo.update.assert_called_once()


# ── unblock() ─────────────────────────────────────────────────────────────────

class TestUnblock:
    def test_reader_not_found_raises(self, svc, reader_repo):
        reader_repo.get_by_id.return_value = None
        with pytest.raises(ReaderNotFoundError):
            svc.unblock("r1")

    def test_sets_is_blocked_false(self, svc, reader_repo):
        reader = _reader(is_blocked=True)
        reader_repo.get_by_id.return_value = reader
        svc.unblock("r1")
        assert reader.is_blocked is False

    def test_already_unblocked_stays_unblocked(self, svc, reader_repo):
        reader = _reader(is_blocked=False)
        reader_repo.get_by_id.return_value = reader
        svc.unblock("r1")
        assert reader.is_blocked is False

    def test_reader_repo_updated(self, svc, reader_repo):
        reader_repo.get_by_id.return_value = _reader(is_blocked=True)
        svc.unblock("r1")
        reader_repo.update.assert_called_once()
