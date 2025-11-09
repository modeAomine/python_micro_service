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

# Модели (оставляем как у тебя)
class TelegramInitData(BaseModel):
    query_id: str = None
    user: dict = None
    receiver: dict = None
    chat: dict = None
    chat_type: str = None
    chat_instance: str = None
    start_param: str = None
    can_send_after: int = None
    auth_date: int
    hash: str

class AuthResponse(BaseModel):
    success: bool
    user: dict = None
    token: str = None
    message: str = None
    is_new_user: bool = False

# JWT утилиты (оставляем как у тебя)
def create_access_token(data: dict, expires_delta: timedelta = None):
    secret_key = os.getenv("SECRET_KEY", "fallback_secret_key")
    algorithm = os.getenv("ALGORITHM", "HS256")
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
        )
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt

# Валидация Telegram Web App данных (оставляем как у тебя)
def validate_telegram_init_data(init_data: str, bot_token: str) -> bool:
    try:
        parsed_data = {}
        for item in init_data.split('&'):
            key, value = item.split('=')
            parsed_data[key] = value
        
        data_hash = parsed_data.pop('hash', '')
        
        data_check_string = '\n'.join(
            f"{key}={value}" 
            for key, value in sorted(parsed_data.items())
        )
        
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        computed_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        auth_date = int(parsed_data.get('auth_date', 0))
        current_time = int(time.time())
        if current_time - auth_date > 86400:
            return False
        
        return hmac.compare_digest(computed_hash, data_hash)
        
    except Exception as e:
        print(f"Validation error: {e}")
        return False

def parse_telegram_user(user_str: str) -> dict:
    try:
        return json.loads(user_str)
    except:
        return {}

@router.post("/telegram", response_model=AuthResponse)
async def telegram_auth(init_data: dict, db: Session = Depends(get_db)):
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not bot_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bot token not configured"
            )
        
        init_data_str = '&'.join([f"{k}={v}" for k, v in init_data.items()])
        
        if not validate_telegram_init_data(init_data_str, bot_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Telegram authentication data"
            )
        
        user_data_str = init_data.get('user', '{}')
        telegram_user = parse_telegram_user(user_data_str)
        
        if not telegram_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User data not found in initData"
            )
        
        telegram_id = telegram_user.get('id')
        if not telegram_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram ID not found"
            )
        
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
                "is_premium": telegram_user.get('is_premium', False),
                "photo_url": telegram_user.get('photo_url'),
                "is_bot": telegram_user.get('is_bot', False)
            }
            user = await UserRepository.create_user(db, user_data)
            is_new_user = True
        
        token_data = {
            "sub": str(user.telegram_id),
            "telegram_id": user.telegram_id,
            "username": user.username
        }
        access_token = create_access_token(token_data)
        
        return AuthResponse(
            success=True,
            user=user.to_dict(),
            token=access_token,
            is_new_user=is_new_user,
            message="User registered successfully" if is_new_user else "Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication failed"
        )

@router.get("/me")
async def get_current_user(telegram_id: int, db: Session = Depends(get_db)):
    user = await UserRepository.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return AuthResponse(
        success=True,
        user=user.to_dict()
    )