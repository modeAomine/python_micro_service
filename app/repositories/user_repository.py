# app/repositories/user_repository.py
from sqlalchemy.orm import Session
from app.models.user import User
import datetime

class UserRepository:
    
    @staticmethod
    async def get_user_by_telegram_id(db: Session, telegram_id: int):
        return db.query(User).filter(User.telegram_id == telegram_id).first()
    
    @staticmethod
    async def create_user(db: Session, user_data: dict):
        user = User(**user_data)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    async def update_user_last_login(db: Session, telegram_id: int):
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.last_login = datetime.datetime.utcnow()
            db.commit()
        return user
    
    @staticmethod
    async def get_or_create_user(db: Session, telegram_user: dict):
        """Получить или создать пользователя (для /start команды)"""
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