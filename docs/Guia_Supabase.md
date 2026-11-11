# Guía: migrar la base de datos a Supabase (PostgreSQL)

**Fecha:** 2026-11-11  
**Objetivo:** dejar de usar SQLite local y apuntar el backend FastAPI a un PostgreSQL gestionado en Supabase, sin cambiar el código de modelos.

---

## 1. Crear el proyecto en Supabase

1. Entra en [https://supabase.com](https://supabase.com) y crea un proyecto (región cercana, p. ej. `sa-east-1` o `us-east-1`).
2. Anota la **contraseña de la base de datos** que elijas al crear el proyecto (solo se muestra una vez).
3. En el dashboard: **Project Settings → Database**.

### Cadena de conexión recomendada

Supabase ofrece dos modos:

| Modo | Uso | Puerto típico |
|------|-----|----------------|
| **Session pooler** (Transaction/Session) | API / serverless | `6543` |
| **Direct** | migraciones, scripts, `create_all` | `5432` |

Para PicRout (FastAPI con SQLAlchemy síncrono) usa preferiblemente:

```text
postgresql+psycopg2://postgres.[PROJECT_REF]:[TU_PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

O la URI **Direct**:

```text
postgresql+psycopg2://postgres:[TU_PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
```

El prefijo `postgresql+psycopg2://` es obligatorio para SQLAlchemy + el driver `psycopg2-binary`.

---

## 2. Configurar el backend

```bash
cd backend
cp .env.example .env   # si aún no tienes .env
```

Edita `.env`:

```env
# Comenta o elimina la línea de SQLite y pon la de Supabase:
DATABASE_URL=postgresql+psycopg2://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres

DEBUG=False
SECRET_KEY=una_clave_larga_y_aleatoria
```

Instala dependencias (incluye el driver de Postgres):

```bash
pip install -r requirements.txt
```

---

## 3. Crear las tablas

Al arrancar la API, `init_db()` ejecuta `Base.metadata.create_all` y crea:

- `users`
- `password_otps`
- `routines`
- `routine_occurrences`
- `verification_attempts`

```bash
uvicorn App.main:app --reload --host 0.0.0.0 --port 8000
```

Comprueba en Supabase → **Table Editor** que aparecen las tablas.

Si prefieres no arrancar el servidor solo para crear tablas:

```bash
cd backend
python -c "from storage.database import init_db; init_db(); print('OK tablas creadas')"
```

---

## 4. Datos existentes en SQLite (opcional)

Si ya tienes usuarios/rutinas en `app_routines.db` y quieres **traspasarlos**:

1. Exporta desde SQLite (ejemplo con `sqlite3`):

   ```bash
   sqlite3 app_routines.db ".mode insert" ".output dump.sql" ".dump" ".exit"
   ```

2. Adapta el dump a PostgreSQL (tipos, `AUTOINCREMENT` → `SERIAL`/identity, comillas).  
   Para un proyecto en etapa temprana suele ser más simple **recrear usuarios** en el entorno Supabase y no migrar filas de prueba.

3. Alternativa: script Python con dos engines (origen SQLite + destino Postgres) y copia fila a fila de los modelos SQLAlchemy. Pedir al equipo si hace falta automatizarlo.

---

## 5. Seguridad

- **Nunca** subas `.env` al repositorio (ya está en `.gitignore`).
- En producción restringe CORS y rota `SECRET_KEY`.
- En Supabase puedes activar **Network restrictions** y usar solo el pooler con SSL (psycopg2 lo usa por defecto en URIs de Supabase).

---

## 6. Verificación rápida

```bash
curl http://127.0.0.1:8000/health
# → {"status":"ok"}

curl http://127.0.0.1:8000/
# → app online
```

Registro de prueba vía `/docs` → `POST /auth/register`. Si el usuario aparece en **Table Editor → users**, la migración está operativa.

---

## Resumen de cambios de código (ya aplicados en el repo)

- `requirements.txt`: `psycopg2-binary==2.9.9`
- `storage/database.py`: pool y `pool_pre_ping` para Postgres; SQLite sin cambios
- `.env.example`: plantilla `DATABASE_URL` para Supabase + flag de fotos

No hace falta cambiar los modelos (`entities/*`): SQLAlchemy es agnóstico al motor.
