# PicRout

**Convierte tu día a día en tu mejor racha**

Aplicación de seguimiento de hábitos y rutinas con verificación por Inteligencia Artificial, sistema de rachas, puntos, tienda virtual y red social.

---

## Equipo

| Integrante                    | Rol                  |
|-------------------------------|----------------------|
| Sofía Rincón Álvarez          | Desarrollo           |
| Juan Pablo Zárate Fernández   | Desarrollo           |
| Sofía Bautista Díaz           | Desarrollo           |

**Profesor:** Freddy León Reyes  
**Universidad Militar Nueva Granada** — Ingeniería de Software  
**Entrega final:** 17 de noviembre de 2026

---

## Estructura del repositorio

```text
PicRout/
├── backend/          → API en FastAPI (Python)
├── docs/             → Documentación interna + Manual de Errores
├── landing/          → Página HTML de descarga del APK
├── .github/          → Workflows de GitHub Actions
└── README.md
```

---

## Stack tecnológico

| Capa              | Tecnología                          |
|-------------------|-------------------------------------|
| Backend           | Python + FastAPI                    |
| Base de datos     | SQLite (dev) → PostgreSQL (prod)    |
| Inteligencia Artificial | Motor propio en Python         |
| Cliente prioritario | Android                           |
| Post-universidad  | Windows (.exe) y versión HTML (solo pruebas) |

---

## Cómo levantar el backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux

uvicorn App.main:app --reload
```

- API: http://127.0.0.1:8000
- Documentación automática: http://127.0.0.1:8000/docs

---

## Regla de código

> La mayor parte del código debe estar en **Python**.  
> Solo se usa otro lenguaje cuando sea estrictamente necesario o aporte una optimización clara.

---

## Estado del proyecto

- [x] Estructura base del repositorio
- [x] Autenticación (rama `feature/auth`)
  - Registro / Login (correo o username + contraseña)
  - Recuperación de contraseña con OTP 6 dígitos (10 min, un solo uso)
  - Perfil de usuario (nombre, avatar, bio, tema, color)
  - JWT Bearer
  - Estructura lista para Google Sign-In (pendiente de CLIENT_ID)
- [x] Rutinas + Rachas (rama `feature/routines`)
  - CRUD de plantillas (nombre, días, hora, duración, puntos base)
  - Ocurrencias diarias automáticas
  - Estados: pendiente / falta_verificacion / completada / incompleta / perdida
  - Racha solo si se completan TODAS las del día + bonus de puntos
  - Idempotencia de racha (`last_streak_date`)
- [ ] Motor de IA
- [ ] Verificación
- [ ] Tienda
- [ ] Red social
- [ ] Panel de administración
- [ ] Despliegue permanente

## Endpoints de autenticación (Paso 1)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/register` | Crear cuenta |
| POST | `/auth/login` | Login (identifier = email o username) |
| POST | `/auth/google` | Google Sign-In (estructura; 501 por ahora) |
| POST | `/auth/forgot-password` | Solicitar OTP al correo |
| POST | `/auth/reset-password` | Cambiar contraseña con OTP |
| GET | `/auth/me` | Perfil del usuario autenticado |
| PUT | `/auth/me` | Actualizar perfil |

## Endpoints de rutinas (Paso 2)

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/routines` | Crear rutina |
| GET | `/routines` | Listar rutinas activas |
| GET | `/routines/today` | Ocurrencias de hoy + resumen |
| GET | `/routines/streak` | Racha y puntos |
| GET | `/routines/{id}` | Detalle de rutina |
| PUT | `/routines/{id}` | Actualizar rutina |
| DELETE | `/routines/{id}` | Soft-delete |
| PATCH | `/routines/occurrences/{id}/status` | Cambiar estado (+ puntos/racha) |
| POST | `/routines/evaluate-today` | Forzar evaluación del día |

Documentación interactiva: http://127.0.0.1:8000/docs
