# FocusFlow

Aplicación web para el seguimiento de hábitos. Permite registrar hábitos, marcar
su cumplimiento diario, visualizar el progreso en un calendario y obtener
estadísticas y recomendaciones a partir del histórico del usuario.

Trabajo de Fin de Grado en Ingeniería Informática.

## Tecnologías

- **Backend:** Python, FastAPI, SQLAlchemy, MySQL, autenticación JWT (bcrypt + PyJWT).
- **Frontend:** HTML5, CSS3, JavaScript, Fetch API, jQuery.

## Estructura

```
backend/
  app/
    controllers/   # Endpoints (capa de presentación)
    services/      # Lógica de negocio
    repositories/  # Acceso a datos
    models/        # Modelos SQLAlchemy
    schemas/       # Esquemas Pydantic
    core/          # Utilidades (seguridad)
    db/            # Conexión y scripts SQL
    main.py        # Punto de entrada de la API
frontend/          # Páginas HTML, CSS y JS
```

## Requisitos previos

- Python 3.11+
- MySQL 8+

## Puesta en marcha (backend)

1. Crear y activar un entorno virtual:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   # source .venv/bin/activate   # Linux/Mac
   ```
2. Instalar dependencias:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Crear la base de datos ejecutando el script
   `backend/app/db/focusflowScripts.sql` en tu servidor MySQL.
4. Configurar las variables de entorno:
   ```bash
   copy backend\.env.example backend\.env    # Windows
   # cp backend/.env.example backend/.env     # Linux/Mac
   ```
   Edita `backend/.env` con tu clave secreta y tu cadena de conexión a MySQL.
   Genera una clave segura con:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
5. Arrancar la API (desde `backend/app`):
   ```bash
   cd backend/app
   python main.py
   ```
   API: http://127.0.0.1:8000 — Documentación: http://127.0.0.1:8000/docs

## Frontend

Abre `frontend/index.html` en el navegador (o sírvelo con una extensión tipo
Live Server). El frontend llama a la API en http://localhost:8000.

## Notas de seguridad

- `backend/.env` contiene secretos y **no se versiona** (ver `.gitignore`).
- Usa `backend/.env.example` como plantilla.
