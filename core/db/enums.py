from enum import Enum


class StatusChoices(Enum):
    STATUS_CREATED = 0
    STATUS_IP_BLOCKED = 1
    STATUS_ACCOUNT_BLOCKED = 2
    STATUS_TIME_EXPIRED = 3
