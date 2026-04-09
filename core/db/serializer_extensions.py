from typing import Optional, Union

from peewee import DoesNotExist

from core.db.model_serializer import BasePeer, User
from core.db.models import PeerModel, UserModel
from core.logs import core_logger


class SerializerExtensions:
    @staticmethod
    def serialize_user(model: UserModel) -> User:
        """Serialize DB user model to Pydantic user model."""
        return User.model_validate(model)

    @staticmethod
    def serialize_peer(model: PeerModel) -> BasePeer:
        """Serialize DB peer model to Pydantic base peer model."""
        return BasePeer.model_validate(model)

    @staticmethod
    def get_user_from_peer_model(peer_model: PeerModel) -> Optional[User]:
        """Resolve and serialize the user related to the provided peer DB model."""
        try:
            return User.model_validate(peer_model.user)
        except DoesNotExist:
            return None
        except Exception as error:
            core_logger.exception(f"Error while getting user from peer model: {error}")
            return None

    @staticmethod
    def get_user_from_peer(peer: Union[BasePeer, PeerModel]) -> Optional[User]:
        """Resolve and serialize a user for a serialized peer or peer DB model."""
        if isinstance(peer, PeerModel):
            return SerializerExtensions.get_user_from_peer_model(peer)

        try:
            model = UserModel.get(UserModel.user_id == str(peer.user_id))
            return User.model_validate(model)
        except DoesNotExist:
            return None
        except Exception as error:
            core_logger.exception(f"Error while getting user from peer: {error}")
            return None
