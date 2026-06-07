from decimal import Decimal

from storage.interfaces import ReaderRepository, FineRepository
from utils.exceptions import ReaderNotFoundError


class MembershipService:
    """Evaluates and enforces reader blocking rules based on unpaid fines and
    overdue-return counts.

    Thresholds are injected, keeping the policy out of the code and making
    this class trivially testable without touching storage.
    """

    def __init__(
        self,
        reader_repo: ReaderRepository,
        fine_repo: FineRepository,
        max_unpaid_amount: Decimal,
        max_overdue_count: int,
    ) -> None:
        self._reader_repo = reader_repo
        self._fine_repo = fine_repo
        self._max_unpaid_amount = max_unpaid_amount
        self._max_overdue_count = max_overdue_count

    def evaluate(self, reader_id: str) -> bool:
        """Recompute whether reader_id should be blocked and apply the change.

        Blocks when: total unpaid fines >= max_unpaid_amount
                  OR overdue_count >= max_overdue_count.
        Unblocks when neither condition holds (handles readers who cleared debt).

        Returns True if the reader ends up blocked, False otherwise.

        Raises:
            ReaderNotFoundError: reader does not exist.
        """
        reader = self._reader_repo.get_by_id(reader_id)
        if reader is None:
            raise ReaderNotFoundError(f"Reader not found: {reader_id!r}")

        unpaid = self._fine_repo.total_unpaid_by_reader(reader_id)
        should_block = (
            unpaid >= self._max_unpaid_amount
            or reader.overdue_count >= self._max_overdue_count
        )
        reader.is_blocked = should_block
        self._reader_repo.update(reader)
        return should_block

    def block(self, reader_id: str) -> None:
        """Force-block a reader regardless of current thresholds.

        Raises:
            ReaderNotFoundError: reader does not exist.
        """
        reader = self._reader_repo.get_by_id(reader_id)
        if reader is None:
            raise ReaderNotFoundError(f"Reader not found: {reader_id!r}")
        reader.is_blocked = True
        self._reader_repo.update(reader)

    def unblock(self, reader_id: str) -> None:
        """Force-unblock a reader regardless of current thresholds.

        Raises:
            ReaderNotFoundError: reader does not exist.
        """
        reader = self._reader_repo.get_by_id(reader_id)
        if reader is None:
            raise ReaderNotFoundError(f"Reader not found: {reader_id!r}")
        reader.is_blocked = False
        self._reader_repo.update(reader)
