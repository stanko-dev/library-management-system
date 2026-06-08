from storage.interfaces import StudentRepository, PenaltyRepository
from utils.exceptions import StudentNotFoundError


class MembershipService:
    """Evaluates and enforces student blocking based on penalty points and missed deadlines."""

    def __init__(
        self,
        student_repo: StudentRepository,
        penalty_repo: PenaltyRepository,
        max_unresolved_points: int,
        max_missed_deadlines: int,
    ) -> None:
        self._student_repo = student_repo
        self._penalty_repo = penalty_repo
        self._max_unresolved_points = max_unresolved_points
        self._max_missed_deadlines = max_missed_deadlines

    def evaluate(self, student_id: str) -> bool:
        """Recompute blocking status and apply it.

        Blocks when: total unresolved points >= max_unresolved_points
                  OR missed_deadlines_count >= max_missed_deadlines.

        Returns True if the student ends up blocked, False otherwise.

        Raises:
            StudentNotFoundError: student does not exist.
        """
        student = self._student_repo.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(f"Student not found: {student_id!r}")

        total_points = self._penalty_repo.total_unresolved_by_student(student_id)
        should_block = (
            total_points >= self._max_unresolved_points
            or student.missed_deadlines_count >= self._max_missed_deadlines
        )
        student.is_blocked = should_block
        self._student_repo.update(student)
        return should_block

    def block(self, student_id: str) -> None:
        """Force-block a student.

        Raises:
            StudentNotFoundError: student does not exist.
        """
        student = self._student_repo.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(f"Student not found: {student_id!r}")
        student.is_blocked = True
        self._student_repo.update(student)

    def unblock(self, student_id: str) -> None:
        """Force-unblock a student.

        Raises:
            StudentNotFoundError: student does not exist.
        """
        student = self._student_repo.get_by_id(student_id)
        if student is None:
            raise StudentNotFoundError(f"Student not found: {student_id!r}")
        student.is_blocked = False
        self._student_repo.update(student)
