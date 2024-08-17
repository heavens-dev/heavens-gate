from enum import Enum
from typing import Type


class StatusChoices(Enum):
    STATUS_CREATED = 0
    STATUS_IP_BLOCKED = 1
    STATUS_ACCOUNT_BLOCKED = 2
    STATUS_TIME_EXPIRED = 3


    @staticmethod
    def to_string(status: Type["StatusChoices"]):
        """Converts Enum to human-readable status."""
        match status:
            case status.STATUS_CREATED:
                return "Аккаунт создан"
            case status.STATUS_IP_BLOCKED:
                return "IP адрес заблокирован. Обратись к администратору"
            case status.STATUS_ACCOUNT_BLOCKED:
                return "Аккаунт заблокирован"
            case status.STATUS_TIME_EXPIRED:
                return "Время пользования VPN вышло. Иди погуляй"
            case _:
                return "Ты как сюда попал, дурной?"
