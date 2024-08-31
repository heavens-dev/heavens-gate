import inspect
import warnings
from typing import Any, Callable, Coroutine, Union

from core.watchdog.object import CallableObject, Callback


class EventObserver:
    def __init__(self, required_types: list[Any] = None) -> None:
        self.__event_handlers: list[CallableObject] = []
        self.required_types = required_types or []
        """Types that are required to call functions"""

    def register(self, fn: Union[Callable, Coroutine]):
        """Registers a callback. Checks for correctness of annotations if `required_types` is present."""
        if self.required_types:
            argspec = inspect.getfullargspec(fn)

            if argspec.args and not argspec.annotations:
                warnings.warn(
                    message=f"Ensure that function '{fn.__name__}' correctly handles "
                    f"arguments with types {self.required_types}. "
                    "Add annotations to hide this warning",
                    stacklevel=3
                )

            for argname, argtype in argspec.annotations.items():
                if not any(tuple(i for i in self.required_types if i == argtype)):
                    warnings.warn(
                        message=f"Ensure that function '{fn.__name__}' correctly handles "
                        f"argument '{argname}' for any of these types: {self.required_types}. "
                        "Add correct annotation to hide this warning",
                        stacklevel=3
                    )

        self.__event_handlers.append(CallableObject(callback=fn))

    # TODO: check arguments if required_types is present.
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
