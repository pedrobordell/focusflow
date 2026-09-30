# FocusFlow

Aplicación web para el seguimiento de hábitos. Permite registrar hábitos, marcar
su cumplimiento diario, visualizar el progreso en un calendario y obtener
estadísticas y recomendaciones a partir del histórico del usuario.

Trabajo de Fin de Grado en Ingeniería Informática.

## Tecnologías

- **Backend:** Python, FastAPI, SQLAlchemy, MySQL, autenticación JWT (bcrypt + PyJWT).
- **Estadísticas y recomendaciones:** Pandas, Matplotlib (gráficas PNG) y scikit-learn
  (árbol de decisión y regresión lineal).
- **Calendario:** icalendar (exportación de las sesiones a `.ics`).
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

1. Entrar en `backend/` y crear y activar un entorno virtual (el resto de comandos
   de esta sección se ejecutan desde esa carpeta):
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   # source .venv/bin/activate   # Linux/Mac
   ```
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Crear la base de datos ejecutando el script
   `backend/app/db/focusflowScripts.sql` en tu servidor MySQL.
   Para cargar los datos de prueba (opcional, ver [Datos de prueba](#datos-de-prueba)),
   ejecuta a continuación `backend/app/db/focusflowDemo.sql` sobre la base
   `focusflow`: el volcado solo contiene datos y no la selecciona por sí mismo.
   ```bash
   mysql -u root -p -e "source app/db/focusflowScripts.sql"
   mysql -u root -p focusflow -e "source app/db/focusflowDemo.sql"
   ```
   Desde MySQL Workbench: ejecuta el primer script y carga el segundo en
   *Server → Data Import → Import from Self-Contained File*, con `focusflow`
   como *Default Target Schema*.
4. Configurar las variables de entorno:
   ```bash
   copy .env.example .env    # Windows
   # cp .env.example .env     # Linux/Mac
   ```
   Edita `backend/.env` con tu clave secreta y tu cadena de conexión a MySQL.
   Genera una clave segura con:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
5. Arrancar la API (desde `backend/app`):
   ```bash
   cd app
   python main.py
   ```
   API: http://127.0.0.1:8000 - Documentación: http://127.0.0.1:8000/docs

## Frontend

Abre `frontend/index.html` en el navegador (o sírvelo con una extensión tipo
Live Server). El frontend llama a la API en http://localhost:8000.

## Datos de prueba

Ejecutando `backend/app/db/focusflowDemo.sql` sobre la base `focusflow` (tras
crear el esquema con `focusflowScripts.sql`) se carga un usuario con cuatro
hábitos, sus sesiones de julio a septiembre de 2026 y los mensajes generados en
ese periodo, para poder probar la aplicación sin necesidad de registrarse ni
generar datos manualmente:

- **Email:** `user@example.com`
- **Contraseña:** `123456`

La aplicación toma siempre como referencia la fecha de hoy. Si se prueba después
de septiembre de 2026, el horario de hoy y la semana actual aparecerán vacíos y,
a partir de los 14 días sin sesiones cumplidas, las recomendaciones avisarán de
que los hábitos están olvidados: es el comportamiento esperado, no un fallo. Para
ver los datos de la demo, retrocede en el calendario hasta esos meses o elige
*All time* en Habit Stats.

## Pruebas automáticas

Las pruebas usan una base de datos SQLite en memoria, así que no necesitan MySQL
ni el fichero `.env`. Desde `backend/`, con el entorno virtual activado:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Notas de seguridad

- `backend/.env` contiene secretos y **no se versiona** (ver `.gitignore`).
- Usa `backend/.env.example` como plantilla.
