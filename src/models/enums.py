from enum import Enum


class BookStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RESERVED = "reserved"
    LOST = "lost"
    MAINTENANCE = "maintenance"


class MembershipType(Enum):
    PREMIUM = "premium"
    STANDARD = "standard"


class ReservationStatus(Enum):
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
