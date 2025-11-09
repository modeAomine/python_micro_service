# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

# ✅ Простой POST эндпоинт
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

# ✅ Еще один простой POST
@app.post("/api/auth/simple")
async def simple_auth():
    return {
        "success": True,
        "message": "Simple auth works!"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)