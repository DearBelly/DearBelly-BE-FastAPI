
import asyncio
from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi import FastAPI

from app.core.config import settings
from app.worker.worker import JobWorker

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

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

    app.state.redis_client = redis_client
    app.state.worker_task = worker_task

    try:
        yield
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        await redis_client.aclose()
