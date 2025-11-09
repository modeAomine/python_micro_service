# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
import os
import sys

# Добавляем путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

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

# ПРОСТОЙ ТЕСТОВЫЙ РОУТЕР БЕЗ ИМПОРТОВ
from fastapi import APIRouter

test_router = APIRouter()

@test_router.get("/test")
async def test():
    return {"message": "✅ Server is working!"}

@test_router.post("/test-post")
async def test_post(data: dict):
    return {"message": "✅ POST is working!", "received": data}

app.include_router(test_router, prefix="/api/auth", tags=["auth"])

# Основные роуты
@app.get("/")
async def root():
    return {"message": "Telegram Mini App Auth API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# УБИРАЕМ MANGUM ДЛЯ ТЕСТА
# from mangum import Mangum
# handler = Mangum(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=8000,
        reload=True if os.getenv("ENV") == "development" else False
    )