
import asyncio
from contextlib import asynccontextmanager

import anyio.to_thread
import redis
from fastapi import FastAPI

from app.worker.redis_client import redis_client
from app.core.config import settings
from app.worker.worker import JobWorker

@asynccontextmanager
async def lifespan(app: FastAPI):
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = 100

    redis_client.xgroup_create(
        stream_name=settings.STREAM_JOB,
        group_name=settings.GROUP_NAME,
    )

    worker = JobWorker(redis_client)
    worker_task = asyncio.create_task(worker.run())

    try:
        yield
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        await redis_client.aclose()
