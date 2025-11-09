from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import hashlib
import hmac
import time
import os
from datetime import datetime, timedelta
import json
from jose import jwt

# Убираем точки перед импортами - это неправильный синтаксис
try:
    from app.database import get_db
    from app.repositories.user_repository import UserRepository
    print("✅ Database imports successful")
except ImportError as e:
    print(f"❌ Database imports failed: {e}")
    # Заглушки если импорты не работают
    get_db = None
    UserRepository = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TelegramUser(BaseModel):
    id: int
    first_name: str
    last_name: str = None
    username: str = None

# ✅ Простые GET эндпоинты
@app.get("/")
async def root():
    return {"message": "API is working!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/test")
async def test():
    return {"message": "Test works!"}

@app.get("/api/auth/test")
async def auth_test():
    return {"message": "Auth test works!"}

# ✅ Простой POST эндпоинт (без БД)
@app.post("/api/auth/bot-start")
async def bot_start(user: TelegramUser):
    print(f"Received user: {user}")  # Для логов
    return {
        "success": True,
        "message": f"Welcome {user.first_name}!",
        "user": {
            "telegram_id": user.id,
            "first_name": user.first_name,
            "username": user.username
        },
        "is_new_user": True
    }

# ✅ Эндпоинт с БД (если импорты работают)
@app.post("/api/auth/bot-start-db")
async def bot_start_db(user_data: TelegramUser, db: Session = Depends(get_db)):
    """
    Эндпоинт для обработки /start команды из бота с БД
    """
    try:
        if UserRepository is None:
            raise HTTPException(status_code=500, detail="Database not configured")
            
        user, is_new = await UserRepository.get_or_create_user(db, user_data.dict())
        
        return {
            "success": True,
            "user": user.to_dict(),
            "is_new_user": is_new,
            "message": "Добро пожаловать! 👋" if is_new else "С возвращением! 🎉"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ✅ Простой тест БД
@app.get("/api/auth/db-test")
async def db_test(db: Session = Depends(get_db)):
    try:
        if UserRepository is None:
            return {"success": False, "message": "Database not available"}
        
        # Просто проверяем что БД работает
        user_count = db.execute("SELECT 1 as test").fetchone()
        return {
            "success": True, 
            "message": "Database is working!",
            "test_result": user_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)