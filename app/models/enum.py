from enum import Enum

class TaskStatus(str, Enum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"

class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class TransactionType(str, Enum):
    TOPUP = "TOPUP"
    CHARGE = "CHARGE"

class FactorGroup(str, Enum):
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    POSITIVE = "POSITIVE"
