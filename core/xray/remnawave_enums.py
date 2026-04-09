from enum import Enum
from typing import Optional
from uuid import UUID

from core.db.enums import SubscriptionType


class InternalSquadEnum(Enum):
    DEFAULT = UUID("93a6aa32-037e-4511-8d98-8e4e416c5cfa")
    CANARY = UUID("4f7486ba-c9fd-40e5-b261-15fcc00227b8")
    CLEAR = UUID("b1aab75c-e3d2-4ce8-a04b-0630ebc672ce")

# TODO: think about correct mapping.
def remnawave_squads_list(subscription: SubscriptionType, include_canary: bool = False) -> list[UUID]:
    squads = []
    match subscription:
        case SubscriptionType.DEFAULT:
            squads.extend([InternalSquadEnum.DEFAULT.value])
        case SubscriptionType.CLEAR:
            squads.extend([InternalSquadEnum.DEFAULT.value, InternalSquadEnum.CLEAR.value])
        case _:
            ...

    if include_canary:
        squads.append(InternalSquadEnum.CANARY.value)

    return squads
