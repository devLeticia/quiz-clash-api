from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from quiz_clash.api.routes import quiz
from quiz_clash.core.exceptions import QuizClashError
from quiz_clash.core.rate_limiter import limiter

app = FastAPI(title="Quiz Clash API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])


@app.exception_handler(QuizClashError)
async def quiz_clash_error_handler(request: Request, exc: QuizClashError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/")
def health_check():
    return {"status": "ok"}
