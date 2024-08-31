import asyncio
import contextvars
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Callable

Callback = Callable[..., Any]

@dataclass
class CallableObject:
    callback: Callback
    awaitable: bool = field(init=False)

    def __post_init__(self) -> None:
        self.awaitable = asyncio.iscoroutinefunction(self.callback)

    async def call(self, *args, **kwargs):
        wrapped = partial(self.callback, *args, **kwargs)

        if self.awaitable:
            return await wrapped()

        loop = asyncio.get_event_loop()
        context = contextvars.copy_context()
        wrapped = partial(context.run, wrapped)
        return await loop.run_in_executor(None, wrapped)
