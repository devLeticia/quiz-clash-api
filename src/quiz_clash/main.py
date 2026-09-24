# src/quiz_clash/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from quiz_clash.api.routes import quiz
from quiz_clash.core.exceptions import QuizClashError

app = FastAPI(title="Quiz Clash API")

app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])


@app.exception_handler(QuizClashError)
async def quiz_clash_error_handler(request: Request, exc: QuizClashError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/")
def health_check():
    return {"status": "ok"}
