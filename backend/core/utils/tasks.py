from typing import Any, Callable

from core.database import get_db


async def with_db(func: Callable, *args: Any, **kwargs: Any):
    """Open an async DB session, call `func(db, *args, **kwargs)`, and close the session.

    The helper returns whatever the called function returns. It ensures the
    generator returned by `get_db()` is properly closed.
    """
    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        return await func(db, *args, **kwargs)
    finally:
        await db_gen.aclose()
