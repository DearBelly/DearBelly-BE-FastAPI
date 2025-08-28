from fastapi import FastAPI, Request
from app.core.lifespan import lifespan
from app.api.endpoints import predictions

app = FastAPI(
    title="DearBelly CV API",
    description="DearBelly CV를 위한 Swagger 입니다.",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(predictions.router, prefix="/api/v1", tags=["Prediction"])

@app.get("/health")
async def health(request: Request):
    redis_client = request.app.state.redis_client
    if not redis_client or not await redis_client.ping():
        return {"status": "error", "message": "Redis connection failed"}
    return {"status": "ok"}