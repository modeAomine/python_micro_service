import sys
import os

# Добавляем корневую папку проекта в Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "run:app",
        host="0.0.0.0", 
        port=8000,
        reload=True
    )