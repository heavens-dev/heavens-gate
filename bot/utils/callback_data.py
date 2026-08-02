from enum import StrEnum

from aiogram.filters.callback_data import CallbackData

from core.db.enums import ProtocolType, SubscriptionType


class UserActionsEnum(StrEnum):
    BAN_USER = "ban"
    PARDON_USER = "pardon"
    GET_CONFIGS = "configs"
    UPDATE_DATA = "update"
    CHANGE_PEER_NAME = "change_peer_name"
    CONTACT_ADMIN = "contact_admin"
    CHANGE_SUBSCRIPTION = "change_subscription"
    EXTEND_SUBSCRIPTION_TIME = "extend_subscription_time"
    WHISPER_USER = "whisper"
    ADD_PEER = "add_peer"
    REGEN_SUBSCRIPTION_TOKEN = "regen_sub_token"


class YesOrNoEnum(StrEnum):
    ANSWER_YES = "yes"
    ANSWER_NO = "no"


class PeerCallbackData(CallbackData, prefix="peer"):
    """Peer callback data for keyboards.

    Args:
        peer_id (int): integer if we want to get a single peer. Set to -1 to get ALL peers that are related to some user
    """
    peer_id: int
    user_id: int

class TimeExtenderCallbackData(CallbackData, prefix="time_extender"):
    """Time extender callback data for keyboards.

    Args:
        user_id (int): user id
        extend_for (str): time to extend for. Example: 1d, 1w, 1M, 3M, 6M, 1Y
    """
    user_id: int
    extend_for: str

class UserActionsCallbackData(CallbackData, prefix="user_action"):
    user_id: int
    action: UserActionsEnum
    is_admin: bool

class PreviewCallbackData(CallbackData, prefix="preview"):
    answer: YesOrNoEnum

class GetUserCallbackData(CallbackData, prefix="get_user"):
    user_id: int

class ProtocolChoiceCallbackData(CallbackData, prefix="protocol_choice"):
    protocol: ProtocolType

class SubscriptionChoiceCallbackData(CallbackData, prefix="subscription_choice"):
    user_id: int
    subscription: SubscriptionType


class OrgActionsEnum(StrEnum):
    VIEW_ORG = "view_org"
    ADD_MEMBER = "add_member"
    ADD_MEMBER_MANUAL = "add_member_manual"
    REMOVE_MEMBER = "remove_member"
    REMOVE_MEMBER_MANUAL = "remove_member_manual"
    VIEW_MEMBERS = "view_members"
    ADD_OWNER = "add_owner"
    ADD_OWNER_MANUAL = "add_owner_manual"
    REMOVE_OWNER = "remove_owner"
    REMOVE_OWNER_MANUAL = "remove_owner_manual"
    EXTEND_SUBSCRIPTION_TIME = "extend_sub_time"
    CONTACT_ADMINS = "contact_admins"
    CONTACT_ORG = "contact_org"
    REFRESH_ORG = "refresh_org"


class OrgActionsCallbackData(CallbackData, prefix="org_action"):
    org_id: int
    action: OrgActionsEnum
    is_admin: bool


class OrgMemberSelectionCallbackData(CallbackData, prefix="org_member_select"):
    """Callback data for selecting a user from a paginated list (add/remove/view member).

    Args:
        org_id (int): organization id
        action (OrgActionsEnum): action to perform with the selected user
        member_id (int): user id of the selected user
    """
    org_id: int
    action: OrgActionsEnum
    member_id: int


class GetOrgCallbackData(CallbackData, prefix="get_org"):
    user_id: int
    org_id: int

class OrgTimeExtenderCallbackData(CallbackData, prefix="org_time_extender"):
    """Time extender callback data for organizations.

    Args:
        org_id (int): organization id
        extend_for (str): time to extend for. Example: 1d, 1w, 1M, 3M, 6M, 1Y
    """
    org_id: int
    extend_for: str
