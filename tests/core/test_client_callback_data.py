from bot.utils.callback_data import ClientListCallbackData
from core.db.client_queries import ClientSort, StatusFilter
from core.db.enums import SubscriptionType


def test_client_list_callback_data_roundtrip_with_none_subscription():
    cd = ClientListCallbackData(sub=SubscriptionType.CLEAR, page=3, page_size=10)
    restored = ClientListCallbackData.unpack(cd.pack())

    assert restored == cd


def test_client_list_callback_data_defaults_roundtrip():
    restored = ClientListCallbackData.unpack(ClientListCallbackData().pack())

    assert restored.sort == ClientSort.REGISTERED
    assert restored.descending is True
    assert restored.sub is None
    assert restored.status == StatusFilter.ANY
    assert restored.page == 1
    assert restored.page_size == 5


def test_client_list_callback_data_packed_size():
    packed = ClientListCallbackData(
        sub=SubscriptionType.ENTERPRISE,
        status=StatusFilter.BLOCKED,
        page=99
    ).pack()

    assert len(packed.encode("utf-8")) <= 64
