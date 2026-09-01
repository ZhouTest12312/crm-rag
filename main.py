"""FastAPI 入口。"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import auth, chat, classes, enrollments, health, students, work_orders

FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"

app = FastAPI(title="edu-crm-langgraph", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(enrollments.router)
app.include_router(students.router)
app.include_router(classes.router)
app.include_router(work_orders.router)


@app.get("/api")
def api_root():
    return {
        "project": "edu-crm-langgraph",
        "chat": "POST /api/chat",
        "docs": "/docs",
        "crm": [
            "/api/enrollments",
            "/api/student",
            "/api/classes",
            "/api/work-orders",
        ],
    }


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "project": "edu-crm-langgraph",
            "hint": "先构建前端：cd frontend && npm install && npm run build",
            "docs": "/docs",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001, reload=False)
