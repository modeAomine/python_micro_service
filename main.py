# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Добавляем путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

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

# Импортируем и инициализируем БД
try:
    from app.database import engine, Base
    from app.models.user import User
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
except Exception as e:
    print(f"⚠️ Database setup: {e}")

# Импортируем роутеры
try:
    from app.auth.router import router as auth_router
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    print("✅ Auth router loaded")
except ImportError as e:
    print(f"❌ Auth router: {e}")

@app.get("/")
async def root():
    return {"message": "Telegram Mini App Auth API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)