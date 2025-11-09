# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
import os
import sys

# Добавляем текущую директорию в путь для импортов
sys.path.append(os.path.dirname(__file__))

# Загрузка переменных окружения
load_dotenv()

app = FastAPI(
    title="Telegram Mini App Auth API",
    description="API для авторизации в Telegram Mini App",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Импортируем роутеры после инициализации app
try:
    from app.auth.router import router as auth_router
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
except ImportError as e:
    print(f"Warning: Could not import routers: {e}")

security = HTTPBearer()

@app.get("/")
async def root():
    return {"message": "Telegram Mini App Auth API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Handler для Vercel
from mangum import Mangum
handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENV") == "development" else False
    )