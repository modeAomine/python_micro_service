from sqlalchemy.orm import Session
from sqlalchemy import and_
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
            db.refresh(user)
        return user

    @staticmethod
    async def get_user_by_id(db: Session, user_id: int):
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    async def update_user(db: Session, telegram_id: int, update_data: dict):
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            for key, value in update_data.items():
                setattr(user, key, value)
            db.commit()
            db.refresh(user)
        return user