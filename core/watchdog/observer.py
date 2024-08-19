import inspect
import warnings
from typing import Callable, Coroutine, Union, Any
from core.watchdog.object import CallableObject, Callback


class EventObserver:
    def __init__(self, required_types: list[Any] = []) -> None:
        self.__event_handlers: list[CallableObject] = []
        self.required_types = required_types
        """Types that are required to call functions"""

    def register(self, fn: Union[Callable, Coroutine]):
        """Register callback."""
        if self.required_types:
            argspec = inspect.getfullargspec(fn)

            if argspec.args and not argspec.annotations:
                warnings.warn(
                    message=f"Ensure that function '{fn.__name__}' correctly handling "
                    f"arguments with types {self.required_types}. "
                    "Add annotations to hide this warning",
                    stacklevel=3
                )

            for argname, type in argspec.annotations.items():
                if not any(tuple(i for i in self.required_types if i == type)):
                    warnings.warn(
                        message=f"Ensure that function '{fn.__name__}' correctly handling "
                        f"argument '{argname}' for any of this types: {self.required_types}. "
                        "Add correct annotation to hide this warning",
                        stacklevel=3
                    )

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
