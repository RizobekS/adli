from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar, overload

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from asgiref.sync import sync_to_async
from django.db import close_old_connections

P = ParamSpec("P")
R = TypeVar("R")


@overload
def database_sync_to_async(
    func: Callable[P, R],
    *,
    thread_sensitive: bool = True,
) -> Callable[P, Awaitable[R]]:
    ...


@overload
def database_sync_to_async(
    func: None = None,
    *,
    thread_sensitive: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, Awaitable[R]]]:
    ...


def database_sync_to_async(
    func: Callable[P, R] | None = None,
    *,
    thread_sensitive: bool = True,
):
    def decorator(inner: Callable[P, R]) -> Callable[P, Awaitable[R]]:
        @wraps(inner)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            close_old_connections()
            try:
                return inner(*args, **kwargs)
            finally:
                close_old_connections()

        return sync_to_async(wrapper, thread_sensitive=thread_sensitive)

    if func is None:
        return decorator

    return decorator(func)


class DjangoDbConnectionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        close_old_connections()
        try:
            return await handler(event, data)
        finally:
            close_old_connections()
