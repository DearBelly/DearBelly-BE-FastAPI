from fastapi import FastAPI, Request
from app.core.lifespan import lifespan
from app.api.endpoints import predictions
from app.core.logging_config import setup_logging
from prometheus_fastapi_instrumentator import Instrumentator

setup_logging()
app = FastAPI(
    title="DearBelly CV API",
    description="DearBelly CV를 위한 Swagger 입니다.",
    version="1.0.0",
    lifespan=lifespan
)

instrumentator = Instrumentator().instrument(app)
instrumentator.expose(app, include_in_schema=False, endpoint="/actuator/prometheus")
app.include_router(predictions.router, prefix="/api/v1", tags=["Prediction"])

@app.get("/health")
async def health(request: Request):
    redis_client = request.app.state.redis_client
    if not redis_client or not await redis_client.ping():
        return {"status": "error", "message": "Redis connection failed"}
    return {"status": "ok"}