from models.enums import MembershipType
from models.reservation import Reservation
from storage.interfaces import ReaderRepository

_MEMBERSHIP_RANK: dict[MembershipType, int] = {
    MembershipType.PREMIUM: 0,
    MembershipType.STANDARD: 1,
}


def reservation_priority_key(res: Reservation, reader_repo: ReaderRepository) -> tuple:
    """Sort key for the reservation queue.

    PREMIUM readers (rank 0) are served before STANDARD readers (rank 1).
    Within the same tier, the longest-waiting reader (smallest created_at)
    is served first.  A reader that cannot be found defaults to STANDARD rank.
    """
    reader = reader_repo.get_by_id(res.reader_id)
    rank = _MEMBERSHIP_RANK.get(
        reader.membership if reader else MembershipType.STANDARD, 1
    )
    return (rank, res.created_at)
