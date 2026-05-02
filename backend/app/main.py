import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.database import engine, AsyncSessionLocal
from app.routes.auth import router as auth_router
from app.routes.channels import router as channels_router
from app.routes.messages import router as messages_router
from app.routes.ws import router as ws_router
from app.routes.analysis import router as analysis_router
from app.routes.scores import router as scores_router
# Chat Core Platform 拡張ルート (優先度B)
from app.routes.decisions import router as decisions_router
from app.routes.human_actions import router as human_actions_router
from app.routes.executions import router as executions_router
from app.routes.evidence import router as evidence_router
from app.routes.signals import router as signals_router
from app.services.redis_client import close as redis_close
from app.services.redis_subscriber import redis_subscriber_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    subscriber_task = asyncio.create_task(redis_subscriber_loop())
    yield
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass
    await redis_close()
    await engine.dispose()


app = FastAPI(title="Chat AI Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(channels_router)
app.include_router(messages_router)
app.include_router(ws_router)
app.include_router(analysis_router)
app.include_router(scores_router)
app.include_router(decisions_router)
app.include_router(human_actions_router)
app.include_router(executions_router)
app.include_router(evidence_router)
app.include_router(signals_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
async def health_db():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return {"database": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="database unavailable")
