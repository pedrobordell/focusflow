import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import engine
from models import Base
from controllers.auth_controller import auth_controller
from controllers.habit_controller import habit_controller
from controllers.session_controller import session_controller

# Crea las tablas que falten
Base.metadata.create_all(bind=engine)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,      # Usa Bearer token en cabecera, no cookies.
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar controladores
app.include_router(auth_controller)
app.include_router(habit_controller)
app.include_router(session_controller)

# Endpoint de prueba
@app.get("/")
def root():
    return {"Server running successfully"}

# Inicializa FastAPI en el servidor uvicorn
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

