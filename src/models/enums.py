from enum import Enum


class StudentRole(Enum):
    LEADER = "leader"
    MEMBER = "member"


class ProjectStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MilestoneStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    LATE = "late"
    MISSED = "missed"


class QueueRequestStatus(Enum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
