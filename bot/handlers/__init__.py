from aiogram import Router


def get_handlers_router() -> Router:
    from . import admin, callbacks, user

    router = Router()
    router.include_router(admin.router)
    router.include_router(callbacks.router)
    router.include_router(user.router)

    return router
