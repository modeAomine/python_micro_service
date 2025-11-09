from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
import os

# ИСПРАВЛЕННЫЕ ИМПОРТЫ
from app.auth.router import router as auth_router

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
    allow_origins=["http://localhost:5173", "https://v40dwu-46-159-247-240.ru.tuna.am"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

security = HTTPBearer()

@app.get("/")
async def root():
    return {"message": "Telegram Mini App Auth API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENV") == "development" else False
    )