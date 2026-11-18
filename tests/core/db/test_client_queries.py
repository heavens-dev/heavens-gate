import datetime

from core.db.client_queries import ClientSort, StatusFilter, select_users_page
from core.db.enums import ClientStatusChoices, SubscriptionType
from core.db.models import UserModel


def create_user(user_id: str, name: str,
                registered_at: datetime.datetime = datetime.datetime(2026, 1, 1),
                status: ClientStatusChoices = ClientStatusChoices.STATUS_CREATED,
                subscription: SubscriptionType | None = None,
                expiry: datetime.datetime | None = None) -> None:
    UserModel.create(
        user_id=user_id,
        name=name,
        registered_at=registered_at,
        status=status.value,
        subscription_type=subscription.value if subscription is not None else None,
        subscription_expiry=expiry
    )


def test_id_sort_is_numeric(db):
    create_user("9000000001", "garry")
    create_user("999999999", "boris")
    create_user("1000000000", "albert")

    page = select_users_page(sort=ClientSort.ID, descending=False)

    assert [user.user_id for user in page.items] == ["999999999", "1000000000", "9000000001"]


def test_name_sort_uses_ci_unicode_collation(db):
    create_user("1", "Борис")
    create_user("2", "алексей")

    page = select_users_page(sort=ClientSort.NAME, descending=False)

    assert [user.name for user in page.items] == ["алексей", "Борис"]


def test_registered_sort_directions(db):
    create_user("1", "a", registered_at=datetime.datetime(2026, 1, 10))
    create_user("2", "b", registered_at=datetime.datetime(2026, 1, 5))
    create_user("3", "c", registered_at=datetime.datetime(2026, 1, 1))

    asc = select_users_page(sort=ClientSort.REGISTERED, descending=False)
    desc = select_users_page(sort=ClientSort.REGISTERED, descending=True)

    assert [user.user_id for user in asc.items] == ["3", "2", "1"]
    assert [user.user_id for user in desc.items] == ["1", "2", "3"]


def test_expiry_sort_keeps_nulls_last_in_both_directions(db):
    create_user("1", "a", expiry=datetime.datetime(2026, 6, 1))
    create_user("2", "b", expiry=datetime.datetime(2026, 3, 1))
    create_user("3", "c")
    create_user("4", "d")

    asc = select_users_page(sort=ClientSort.EXPIRY, descending=False)
    desc = select_users_page(sort=ClientSort.EXPIRY, descending=True)

    assert [user.user_id for user in asc.items] == ["2", "1", "3", "4"]
    assert [user.user_id for user in desc.items] == ["1", "2", "3", "4"]


def test_subscription_filter(db):
    create_user("1", "a", subscription=SubscriptionType.DEFAULT)
    create_user("2", "b", subscription=SubscriptionType.CLEAR)
    create_user("3", "c")

    page = select_users_page(subscription=SubscriptionType.DEFAULT)

    assert page.total == 1
    assert [user.user_id for user in page.items] == ["1"]


def test_status_filter(db):
    create_user("1", "a", status=ClientStatusChoices.STATUS_ACCOUNT_BLOCKED)
    create_user("2", "b", status=ClientStatusChoices.STATUS_TIME_EXPIRED)
    create_user("3", "c", status=ClientStatusChoices.STATUS_CONNECTED)
    create_user("4", "d", status=ClientStatusChoices.STATUS_CREATED)
    create_user("5", "e", status=ClientStatusChoices.STATUS_DISCONNECTED)

    blocked = select_users_page(status=StatusFilter.BLOCKED)
    expired = select_users_page(status=StatusFilter.EXPIRED)
    active = select_users_page(status=StatusFilter.ACTIVE)

    assert [user.user_id for user in blocked.items] == ["1"]
    assert [user.user_id for user in expired.items] == ["2"]
    assert sorted(user.user_id for user in active.items) == ["3", "4", "5"]


def test_subscription_and_status_filters_combined(db):
    create_user("1", "a", subscription=SubscriptionType.CLEAR,
                status=ClientStatusChoices.STATUS_TIME_EXPIRED)
    create_user("2", "b", subscription=SubscriptionType.CLEAR,
                status=ClientStatusChoices.STATUS_CREATED)
    create_user("3", "c", subscription=SubscriptionType.DEFAULT,
                status=ClientStatusChoices.STATUS_CREATED)

    page = select_users_page(subscription=SubscriptionType.CLEAR,
                             status=StatusFilter.ACTIVE)

    assert [user.user_id for user in page.items] == ["2"]


def test_pagination_clips_page_and_counts(db):
    for index in range(8):
        create_user(str(index), f"user_{index}",
                    registered_at=datetime.datetime(2026, 1, 1 + index))

    first = select_users_page(sort=ClientSort.ID, descending=False, page=1)
    second = select_users_page(sort=ClientSort.ID, descending=False, page=2)
    overflow = select_users_page(sort=ClientSort.ID, descending=False, page=999)
    underflow = select_users_page(sort=ClientSort.ID, descending=False, page=0)

    assert first.total == 8
    assert first.pages == 2
    assert len(first.items) == 5
    assert len(second.items) == 3
    assert overflow.page == 2
    assert underflow.page == 1


def test_empty_result_page(db):
    create_user("1", "a", subscription=SubscriptionType.ENTERPRISE)

    page = select_users_page(subscription=SubscriptionType.DEFAULT)

    assert page.total == 0
    assert page.pages == 1
    assert page.items == []
