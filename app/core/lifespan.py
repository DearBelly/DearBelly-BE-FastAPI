
import asyncio
from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi import FastAPI

from app.worker.redis_client import redis_client
from app.core.config import settings
from app.worker.worker import JobWorker

@asynccontextmanager
async def lifespan(app: FastAPI):
    limiter = asyncio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = 50

    try:
        await redis_client.xgroup_create(
            name=settings.STREAM_JOB,
            groupname=settings.GROUP_NAME,
            id="$",
            mkstream=True
        )
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

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
