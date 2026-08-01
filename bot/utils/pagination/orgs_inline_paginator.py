from aiogram import Router
from aiogram.types import InlineKeyboardButton

from bot.utils.callback_data import (GetOrgCallbackData,
                                     OrgActionsCallbackData, OrgActionsEnum,
                                     OrgMemberSelectionCallbackData)
from bot.utils.pagination.base_inline_paginator import \
    BaseInlineKeyboardPaginator
from core.db.db_works import Client, ClientFactory, OrganizationFactory
from core.db.model_serializer import Organization


class OrgsInlineKeyboardPaginator(BaseInlineKeyboardPaginator[Organization]):
    def __init__(
        self,
        data: list[Organization],
        router: Router,
        chat_id: int,
        caller_user_id: int,
        items_per_page: int = 5,
        current_page: int = 1,
        callback_prefix: str = "orgs_",
    ) -> None:
        super().__init__(
            data,
            router,
            chat_id,
            items_per_page=items_per_page,
            current_page=current_page,
            callback_prefix=callback_prefix,
        )
        self.caller_user_id = caller_user_id

    def item_to_button(self, org: Organization) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=f"{org.name} ({org.org_id})",
            callback_data=GetOrgCallbackData(
                org_id=org.org_id,
                user_id=self.caller_user_id
            ).pack()
        )

    def refresh_data(self) -> list[Organization]:
        return [org.orgdata for org in OrganizationFactory.select_organizations()]


class OrgMembersInlineKeyboardPaginator(BaseInlineKeyboardPaginator[Client]):
    def __init__(
        self,
        data: list[Client],
        router: Router,
        chat_id: int,
        org_id: int,
        action: OrgActionsEnum,
        is_admin: bool,
        items_per_page: int = 5,
        current_page: int = 1,
        callback_prefix: str = "org_members_",
        allow_manual_input: bool = False,
    ) -> None:
        super().__init__(
            data,
            router,
            chat_id,
            items_per_page=items_per_page,
            current_page=current_page,
            callback_prefix=callback_prefix,
        )
        self.org_id = org_id
        self.action = action
        self.is_admin = is_admin
        self.allow_manual_input = allow_manual_input

    def item_to_button(self, client: Client) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text=f"{client.userdata.name} ({client.userdata.user_id})",
            callback_data=OrgMemberSelectionCallbackData(
                org_id=self.org_id,
                action=self.action,
                member_id=client.userdata.user_id
            ).pack()
        )

    def _extra_rows(self) -> list[list[InlineKeyboardButton]]:
        if not self.allow_manual_input:
            return []

        manual_action = {
            OrgActionsEnum.ADD_MEMBER: OrgActionsEnum.ADD_MEMBER_MANUAL,
            OrgActionsEnum.REMOVE_MEMBER: OrgActionsEnum.REMOVE_MEMBER_MANUAL,
            OrgActionsEnum.ADD_OWNER: OrgActionsEnum.ADD_OWNER_MANUAL,
            OrgActionsEnum.REMOVE_OWNER: OrgActionsEnum.REMOVE_OWNER_MANUAL,
        }.get(self.action)

        if manual_action is None:
            return []

        return [[InlineKeyboardButton(
            text="✏️ Ввести ID вручную",
            callback_data=OrgActionsCallbackData(
                org_id=self.org_id,
                action=manual_action,
                is_admin=self.is_admin
            ).pack()
        )]]

    def refresh_data(self) -> list[Client]:
        org = OrganizationFactory.get_by_id(self.org_id)
        if not org:
            return []

        if self.action == OrgActionsEnum.ADD_MEMBER:
            return [
                client for client in ClientFactory.select_clients()
                if not org.is_user_member(client.userdata.user_id)
            ]
        if self.action in (OrgActionsEnum.REMOVE_MEMBER, OrgActionsEnum.VIEW_MEMBERS):
            return org.get_members(as_client=True)
        if self.action == OrgActionsEnum.ADD_OWNER:
            return [
                client for client in ClientFactory.select_clients()
                if not org.is_user_owner(client.userdata.user_id)
            ]
        if self.action == OrgActionsEnum.REMOVE_OWNER:
            return org.get_owners(as_client=True)
        return []
