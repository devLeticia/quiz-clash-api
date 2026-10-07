import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from quiz_clash.api.routes import quiz, rooms
from quiz_clash.core.exceptions import register_exception_handlers
from quiz_clash.core.rate_limiter import limiter

DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", ",".join(DEV_ORIGINS)).split(",")

logger = logging.getLogger("quiz_clash")
app = FastAPI(title="Quiz Clash API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
app.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

register_exception_handlers(app)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


@app.get("/")
def health_check():
    return {"status": "ok"}
