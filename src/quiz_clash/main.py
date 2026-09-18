from fastapi import FastAPI

from quiz_clash.api.routes import quiz

app = FastAPI(title="Quiz Clash API")

app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])


@app.get("/")
def health_check():
    return {"status": "ok"}
