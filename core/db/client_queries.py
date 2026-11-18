from dataclasses import dataclass
from enum import StrEnum
from math import ceil
from typing import Generic, TypeVar

from peewee import Cast

from core.db.enums import ClientStatusChoices, SubscriptionType
from core.db.model_serializer import User
from core.db.models import UserModel

T = TypeVar("T")


class ClientSort(StrEnum):
    REGISTERED = "reg"
    EXPIRY = "exp"
    NAME = "name"
    ID = "id"


class StatusFilter(StrEnum):
    ANY = "-"
    BLOCKED = "b"
    ACTIVE = "u"
    EXPIRED = "x"

    def statuses(self) -> tuple[ClientStatusChoices, ...] | None:
        match self:
            case StatusFilter.BLOCKED:
                return (ClientStatusChoices.STATUS_ACCOUNT_BLOCKED,)
            case StatusFilter.EXPIRED:
                return (ClientStatusChoices.STATUS_TIME_EXPIRED,)
            case StatusFilter.ACTIVE:
                return (
                    ClientStatusChoices.STATUS_CREATED,
                    ClientStatusChoices.STATUS_CONNECTED,
                    ClientStatusChoices.STATUS_DISCONNECTED
                )
            case _:
                return None


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        return max(1, ceil(self.total / self.page_size))


ID_KEY = Cast(UserModel.user_id, "INTEGER")

SORT_KEYS = {
    ClientSort.REGISTERED: UserModel.registered_at,
    ClientSort.EXPIRY: UserModel.subscription_expiry,
    ClientSort.NAME: UserModel.name.collate("ci_unicode"),
    ClientSort.ID: ID_KEY,
}

def build_criteria(
    subscription: SubscriptionType | None,
    status: StatusFilter
) -> list:
    criteria = []
    if subscription is not None:
        criteria.append(UserModel.subscription_type == subscription.value)
    if status.statuses() is not None:
        criteria.append(UserModel.status.in_(
            [status_choice.value for status_choice in status.statuses()]
        ))
    return criteria

def build_order(sort: ClientSort, descending: bool) -> list:
    key = SORT_KEYS[sort]
    order = [key.desc() if descending else key.asc()]
    if sort is ClientSort.EXPIRY:
        order.insert(0, UserModel.subscription_expiry.is_null().asc())
    return order + [ID_KEY.asc()]

def select_users_page(
    sort: ClientSort = ClientSort.REGISTERED,
    descending: bool = True,
    subscription: SubscriptionType | None = None,
    status: StatusFilter = StatusFilter.ANY,
    page: int = 1,
    page_size: int = 5
) -> Page[User]:
    query = UserModel.select()
    criteria = build_criteria(subscription, status)
    if criteria:
        query = query.where(*criteria)

    total = query.count()
    pages = max(1, ceil(total / page_size))
    page = min(max(page, 1), pages)

    rows = (query
            .order_by(*build_order(sort, descending))
            .limit(page_size)
            .offset((page - 1) * page_size))

    return Page(
        items=[User.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size
    )
