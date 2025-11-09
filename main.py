# main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
import os
import sys

# Добавляем путь для импортов - ФИКС
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Импортируем роутеры - ФИКС ИМПОРТОВ
try:
    # Пробуем разные пути импорта
    try:
        from app.auth.router import router as auth_router
        print("✅ Import from app.auth.router successful")
    except ImportError:
        from auth.router import router as auth_router  
        print("✅ Import from auth.router successful")
    
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
    print("✅ Auth router included")
    
except ImportError as e:
    print(f"❌ Could not import routers: {e}")
    # Создаем базовый роутер если импорт не удался
    from fastapi import APIRouter
    auth_router = APIRouter()
    
    @auth_router.get("/test")
    async def test():
        return {"message": "Test route working"}
    
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

security = HTTPBearer()

@app.get("/")
async def root():
    return {"message": "Telegram Mini App Auth API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/test-imports")
async def test_imports():
    """Тестовый эндпоинт для проверки импортов"""
    try:
        from app.auth.router import router
        return {"import_status": "success", "message": "All imports working"}
    except ImportError as e:
        return {"import_status": "failed", "error": str(e)}

# Handler для Vercel
try:
    from mangum import Mangum
    handler = Mangum(app)
    print("✅ Mangum handler created")
except ImportError as e:
    print(f"❌ Mangum import failed: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,  # ФИКС: передаем app напрямую
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENV") == "development" else False
    )