# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import hashlib
import hmac
import time
import os
import json
from datetime import datetime, timedelta
from jose import jwt

# ===== CONFIG =====
app = FastAPI(
    title="Telegram Mini App Auth API",
    description="API для авторизации в Telegram Mini App",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== DATABASE =====
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель User
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=True)
    username = Column(String(255), nullable=True)
    language_code = Column(String(10), nullable=True)
    is_premium = Column(Boolean, default=False)
    photo_url = Column(Text, nullable=True)
    is_bot = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, server_default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
            "language_code": self.language_code,
            "is_premium": self.is_premium,
            "photo_url": self.photo_url,
            "is_bot": self.is_bot,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }

# Создаем таблицы
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== MODELS =====
class TelegramInitData(BaseModel):
    init_data: str

class TelegramUser(BaseModel):
    id: int
    first_name: str
    last_name: str = None
    username: str = None
    language_code: str = None
    is_premium: bool = False
    photo_url: str = None
    is_bot: bool = False

class AuthResponse(BaseModel):
    success: bool
    user: dict = None
    token: str = None
    message: str = None
    is_new_user: bool = False

# ===== UTILS =====
def create_access_token(data: dict):
    secret_key = os.getenv("SECRET_KEY", "fallback_secret_key")
    algorithm = os.getenv("ALGORITHM", "HS256")
    
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)

def validate_telegram_init_data(init_data: str) -> bool:
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            return False
            
        parsed_data = {}
        for item in init_data.split('&'):
            if '=' in item:
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

# ===== USER REPOSITORY =====
class UserRepository:
    @staticmethod
    async def get_user_by_telegram_id(db, telegram_id: int):
        return db.query(User).filter(User.telegram_id == telegram_id).first()
    
    @staticmethod
    async def create_user(db, user_data: dict):
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    async def update_user_last_login(db, telegram_id: int):
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.last_login = datetime.utcnow()
            db.commit()
        return user
    
    @staticmethod
    async def get_or_create_user(db, telegram_user: dict):
        telegram_id = telegram_user.get('id')
        existing_user = await UserRepository.get_user_by_telegram_id(db, telegram_id)
        
        if existing_user:
            await UserRepository.update_user_last_login(db, telegram_id)
            return existing_user, False
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
            return user, True

# ===== ROUTES =====
@app.get("/")
async def root():
    return {"message": "Telegram Mini App Auth API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/test")
async def test():
    return {"message": "✅ Test endpoint works!"}

@app.get("/api/auth/test")
async def auth_test():
    return {"message": "✅ Auth router is working!"}

# 🔐 Аутентификация через Telegram Mini App
@app.post("/api/auth/telegram", response_model=AuthResponse)
async def telegram_auth(request: TelegramInitData, db = Depends(get_db)):
    try:
        if not validate_telegram_init_data(request.init_data):
            raise HTTPException(status_code=401, detail="Invalid Telegram auth data")
        
        telegram_user = parse_telegram_user(request.init_data)
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

# 🤖 Эндпоинт для /start команды бота
@app.post("/api/auth/bot-start")
async def bot_start(user: TelegramUser, db = Depends(get_db)):
    try:
        user_obj, is_new = await UserRepository.get_or_create_user(db, user.dict())
        
        return {
            "success": True,
            "user": user_obj.to_dict(),
            "is_new_user": is_new,
            "message": "Добро пожаловать! 👋" if is_new else "С возвращением! 🎉"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 👤 Получение данных пользователя
@app.get("/api/auth/me")
async def get_current_user(telegram_id: int, db = Depends(get_db)):
    user = await UserRepository.get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return AuthResponse(success=True, user=user.to_dict())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)