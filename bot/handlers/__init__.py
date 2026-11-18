from aiogram import Router


def get_handlers_router() -> Router:
    from . import admin, user
    from .callbacks import (clients_list, observers, query_callbacks,
                            state_callbacks)

    router = Router()
    router.include_router(admin.router)
    router.include_router(user.router)
    router.include_router(state_callbacks.router)
    router.include_router(observers.router)
    router.include_router(clients_list.router)
    router.include_router(query_callbacks.router)

    return router
