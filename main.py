# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
import asyncio
from threading import Thread

# ===== AIOGRAM BOT IMPORTS =====
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command

# ===== DATABASE IMPORTS =====
try:
    from app.database import get_db, engine, Base
    from app.models.user import User
    from app.repositories.user_repository import UserRepository
    
    Base.metadata.create_all(bind=engine)
    print("✅ Database connected")
except ImportError as e:
    print(f"❌ Database error: {e}")
    get_db = None
    UserRepository = None

# ===== FASTAPI APP =====
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== TELEGRAM BOT =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
router = Router()

# ===== MODELS =====
class TelegramUser(BaseModel):
    id: int
    first_name: str
    last_name: str = None
    username: str = None
    language_code: str = None
    is_premium: bool = False
    is_bot: bool = False

# ===== БОТ =====
@router.message(Command("start"))
async def start_command(message: types.Message):
    """Обработчик команды /start"""
    try:
        user = message.from_user
        
        # СОХРАНЯЕМ ПОЛЬЗОВАТЕЛЯ НАПРЯМУЮ В БД
        if UserRepository:
            user_data = {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "language_code": user.language_code,
                "is_premium": getattr(user, 'is_premium', False),
                "is_bot": user.is_bot
            }
            
            # Используем БД напрямую из бота
            from app.database import SessionLocal
            db = SessionLocal()
            try:
                existing_user = await UserRepository.get_user_by_telegram_id(db, user.id)
                if existing_user:
                    await UserRepository.update_user_last_login(db, user.id)
                else:
                    await UserRepository.create_user(db, user_data)
                db.commit()
                print(f"✅ User {user.id} saved to DB")
            except Exception as e:
                print(f"❌ DB error: {e}")
                db.rollback()
            finally:
                db.close()
        
        # Приветственное сообщение
        welcome_text = f"""
👋 Привет, {user.first_name}!

Добро пожаловать в бот для вывоза мусора! 🗑️

Используй /menu для главного меню
        """
        
        await message.answer(welcome_text)
        
    except Exception as e:
        print(f"Error in start: {e}")
        await message.answer(f"Привет, {message.from_user.first_name}! 🎉")

# ===== API =====
@app.get("/")
async def root():
    return {"message": "Bot + API working"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/auth/bot-start")
async def bot_start(user_data: TelegramUser, db: Session = Depends(get_db)):
    """API для сохранения пользователя"""
    try:
        if not UserRepository:
            return {"success": False, "message": "DB not available"}
        
        clean_data = {k: v for k, v in user_data.dict().items() if v is not None}
        
        existing_user = await UserRepository.get_user_by_telegram_id(db, clean_data['id'])
        
        if existing_user:
            await UserRepository.update_user_last_login(db, clean_data['id'])
            is_new = False
            user_obj = existing_user
        else:
            user_obj = await UserRepository.create_user(db, clean_data)
            is_new = True
        
        return {
            "success": True,
            "user": user_obj.to_dict(),
            "is_new_user": is_new
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===== ЗАПУСК БОТА =====
async def start_bot():
    try:
        dp.include_router(router)
        print("🤖 Bot starting...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Bot failed: {e}")

def run_bot():
    asyncio.run(start_bot())

@app.on_event("startup")
async def startup():
    print("🚀 Server starting...")
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)