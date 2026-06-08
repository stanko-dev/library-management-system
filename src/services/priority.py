from models.queue_request import QueueRequest
from storage.interfaces import StudentRepository


def queue_priority_key(req: QueueRequest, student_repo: StudentRepository) -> tuple:
    """Sort key for the team join queue.

    Students with fewer active projects (lower count) are served first.
    Within the same count, the longest-waiting student (smallest created_at)
    is served first. A student that cannot be found defaults to count 999.
    """
    student = student_repo.get_by_id(req.student_id)
    count = student.active_projects_count if student else 999
    return (count, req.created_at)
