# app/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import hashlib
import hmac
import time
import os
from datetime import datetime, timedelta
import json
from jose import jwt

from app.database import get_db
from app.repositories.user_repository import UserRepository

router = APIRouter()

# Модели
class TelegramInitData(BaseModel):
    init_data: str

class TelegramUser(BaseModel):
    id: int
    first_name: str
    last_name: str = None
    username: str = None
    language_code: str = None
    is_premium: bool = False

class AuthResponse(BaseModel):
    success: bool
    user: dict = None
    token: str = None
    message: str = None
    is_new_user: bool = False

# JWT утилиты
def create_access_token(data: dict):
    secret_key = os.getenv("SECRET_KEY")
    algorithm = os.getenv("ALGORITHM", "HS256")
    
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)

# Валидация Telegram Web App данных
def validate_telegram_init_data(init_data: str) -> bool:
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            return False
            
        parsed_data = {}
        for item in init_data.split('&'):
            key, value = item.split('=')
            parsed_data[key] = value
        
        data_hash = parsed_data.pop('hash', '')
        data_check_string = '\n'.join(
            f"{key}={value}" for key, value in sorted(parsed_data.items())
        )
        
        secret_key = hmac.new(
            b"WebAppData", bot_token.encode(), hashlib.sha256
        ).digest()
        
        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()
        
        # Проверяем время (24 часа)
        auth_date = int(parsed_data.get('auth_date', 0))
        if time.time() - auth_date > 86400:
            return False
        
        return hmac.compare_digest(computed_hash, data_hash)
        
    except Exception as e:
        print(f"Validation error: {e}")
        return False

def parse_telegram_user(init_data: str) -> dict:
    try:
        params = dict(item.split('=') for item in init_data.split('&') if '=' in item)
        user_str = params.get('user', '{}')
        return json.loads(user_str)
    except:
        return {}

@router.post("/telegram", response_model=AuthResponse)
async def telegram_auth(data: TelegramInitData, db: Session = Depends(get_db)):
    try:
        if not validate_telegram_init_data(data.init_data):
            raise HTTPException(status_code=401, detail="Invalid Telegram auth data")
        
        telegram_user = parse_telegram_user(data.init_data)
        if not telegram_user.get('id'):
            raise HTTPException(status_code=400, detail="User data not found")
        
        telegram_id = telegram_user['id']
        existing_user = await UserRepository.get_user_by_telegram_id(db, telegram_id)
        is_new_user = False
        
        if existing_user:
            await UserRepository.update_user_last_login(db, telegram_id)
            user = existing_user
        else:
            user_data = {
                "telegram_id": telegram_id,
                "first_name": telegram_user.get('first_name', ''),
                "last_name": telegram_user.get('last_name'),
                "username": telegram_user.get('username'),
                "language_code": telegram_user.get('language_code'),
                "is_premium": telegram_user.get('is_premium', False)
            }
            user = await UserRepository.create_user(db, user_data)
            is_new_user = True
        
        token = create_access_token({
            "sub": str(user.telegram_id),
            "telegram_id": user.telegram_id
        })
        
        return AuthResponse(
            success=True,
            user=user.to_dict(),
            token=token,
            is_new_user=is_new_user,
            message="User registered" if is_new_user else "Login successful"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bot-start")
async def bot_start_command(user_data: TelegramUser, db: Session = Depends(get_db)):
    """
    Эндпоинт для обработки /start команды из бота
    """
    try:
        user, is_new = await UserRepository.get_or_create_user(db, user_data.dict())
        
        return {
            "success": True,
            "user": user.to_dict(),
            "is_new_user": is_new,
            "message": "Добро пожаловать! 👋" if is_new else "С возвращением! 🎉"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me")
async def get_current_user(telegram_id: int, db: Session = Depends(get_db)):
    user = await UserRepository.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return AuthResponse(success=True, user=user.to_dict())

@router.get("/test")
async def test_route():
    return {"message": "✅ Auth router is working!"}