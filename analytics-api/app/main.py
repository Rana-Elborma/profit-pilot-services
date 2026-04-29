import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine
from app.routers.analytics import router as analytics_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("analytics-api starting up")
    yield
    logger.info("analytics-api shutting down — closing DB connections")
    engine.dispose()


app = FastAPI(title="Profit Pilot Analytics API", lifespan=lifespan)

app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "service": "analytics-api"}
