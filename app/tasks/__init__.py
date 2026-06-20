"""Celery background task modules."""

import asyncio


def run_async(coro):
    """Run an async coroutine from sync Celery worker processes."""
    return asyncio.run(coro)
