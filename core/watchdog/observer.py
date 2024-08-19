from typing import Callable, Coroutine, Union
from core.watchdog.object import CallableObject, Callback


class EventObserver:
    def __init__(self) -> None:
        self.__event_handlers: list[CallableObject] = []

    def register(self, fn: Union[Callable, Coroutine]):
        """Register callback."""

        self.__event_handlers.append(CallableObject(callback=fn))

    async def trigger(self, *args, **kwargs):
        """Propagate event to handlers."""
        for handler in self.__event_handlers:
            await handler.call(*args, **kwargs)

    def __call__(self):
        """Decorator for registering event handlers."""
        def wrapper(fn: Callback):
            self.register(fn)
            return fn
        return wrapper
