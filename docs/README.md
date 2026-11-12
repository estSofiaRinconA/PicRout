# PicRout — Documentación del proyecto

**Actualización:** 11 de noviembre de 2026 · **Stack backend:** Python, FastAPI, SQLAlchemy y PostgreSQL en Supabase.

## Estado probado
- Backend y conexión con **un proyecto Supabase compartido** entre computadores.
- Registro y login tradicional por correo o usuario; JWT propio de PicRout.
- Google Sign-In real mediante **Google Cloud → Supabase Auth → POST /auth/google → public.users → JWT PicRout**. Se comprobó creación de usuario y segundo acceso sin duplicados.
- Rutinas, ocurrencias, rachas/puntos y quiz forman parte del backend probado en etapas anteriores; consultar la guía para repetir las verificaciones.
- La validación por fotos fue **retirada** el 11/11/2026. Actualmente se utiliza **quiz**.

## Estado pendiente
Interfaz Android y botón Google final, asociación segura de Google a cuentas tradicionales, pruebas automatizadas y casos de seguridad ampliados, tienda, red social, notificaciones y distribución APK. No presentar estas características como terminadas.

## Puesta en marcha
Desde `backend/`:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn App.main:app --reload
```

Desde la raíz del repositorio:

```powershell
python -m uvicorn App.main:app --app-dir backend --reload
```

- Swagger: `http://127.0.0.1:8000/docs`
- Salud: `GET /health` (200 no garantiza por sí solo conexión a PostgreSQL).
- Configurar `backend/.env` local y seguro: `DATABASE_URL`, secretos JWT y las variables Supabase Auth esperadas por el código (en esta implementación, `SUPABASE_URL`, `SUPABASE_ANON_KEY`). **Nunca publicar `.env`**.
- Verificar conexión registrando un usuario nuevo y buscando su fila en `public.users`.

## Documentos
| Archivo | Función |
|---|---|
| [Manual_de_Usuario.md](Manual_de_Usuario.md) | Uso y estado de las funciones de PicRout. |
| [Manual_de_Errores.md](Manual_de_Errores.md) | Errores reales y soluciones documentadas (ERR-001 a ERR-010). |
| [Guia_Verificacion_Manual.txt](Guia_Verificacion_Manual.txt) | JSON, endpoints y checklist de pruebas actuales, incluida autenticación Google. |
| [Guia_Supabase.md](Guia_Supabase.md) | Configurar un equipo nuevo para usar **el mismo Supabase**; OAuth y recuperación de incidencias. |

## Flujo de Google: detalles de integración
1. Google Cloud: proveedor OAuth y callback del **mismo proyecto Supabase**.
2. Supabase Auth valida sesión e identidad Google.
3. `POST /auth/google` recibe `{"access_token":"<SUPABASE_ACCESS_TOKEN>"}`, verifica la sesión y crea/consulta cuenta de PicRout.
4. La API devuelve el JWT propio que se usa en rutas protegidas.
5. Si ya hay cuenta tradicional con el mismo correo, se devuelve 409; la vinculación está pendiente.

**Seguridad:** no publicar tokens de sesión, Google Client Secret, contraseñas ni claves. No modificar triggers de `auth.users` sin revisar qué ejecutan. La eliminación del trigger obsoleto `on_auth_user_created` en el entorno probado debe mantenerse documentada como migración de esquema revisada por el equipo.

## Trabajo en Git
- `base-de-datos`: rama de la migración a PostgreSQL.
- `feature/google-signin`: rama de integración Google, creada para aislar el trabajo. El historial/estado remoto final debe verificarse con `git status` y `git log`; el manual no presupone una fusión a `main`.

**Contacto del proyecto:** picrout@gmail.com
