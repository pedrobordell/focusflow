import uvicorn
from fastapi import FastAPI
from db.database import engine
from models.user import Base
from controllers.auth_controller import auth_controller

# Inicializar la base de datos y crear la app
Base.metadata.create_all(bind=engine)
app = FastAPI()

# Registrar controladores
app.include_router(auth_controller)

# Endpoint de prueba
@app.get("/")
def root():
    return {"mensaje": "Servidor funcionando"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)