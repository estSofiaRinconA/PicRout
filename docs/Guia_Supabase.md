# Guía de Supabase — configuración compartida de PicRout

**Actualización:** 11 de noviembre de 2026  
**Alcance:** incorporación de equipos, recuperación de conexión y Google OAuth. **No crear un proyecto nuevo por computador.**

## ¿Conservar este documento?
**Sí, en versión breve.** El equipo utiliza **un único proyecto Supabase**, pero cada PC necesita su propio `.env`, y hay configuración de OAuth y de esquema que no se reconstruye solo con `git pull`. La guía antigua de migración SQLite → PostgreSQL queda como antecedente histórico, no como procedimiento cotidiano.

## 1. Preparar un PC nuevo
1. Obtener permiso para acceder al proyecto Supabase compartido y al repositorio.
2. Actualizar la rama adecuada (`git fetch origin`, `git switch <rama>`, `git pull --ff-only`), sin sobrescribir cambios locales.
3. Instalar dependencias con `python -m pip install -r requirements.txt` desde `backend/`.
4. Crear `backend/.env` localmente copiando **de manera segura** los nombres/valores autorizados del equipo; **jamás** añadirlo a Git.
5. Confirmar que `DATABASE_URL` apunta al PostgreSQL **del mismo proyecto**, y que `SUPABASE_URL` y `SUPABASE_ANON_KEY` (si el backend los utiliza con esos nombres) corresponden al mismo proyecto. Conservar la clave JWT requerida por el backend.
6. Ejecutar desde `backend/`:

```powershell
python -m uvicorn App.main:app --reload
```

Desde la raíz de PicRout, alternativa:

```powershell
python -m uvicorn App.main:app --app-dir backend --reload
```

> No utilizar `backend.App.main:app` desde `backend/`. No cambiar el código para compensar una ruta de ejecución incorrecta.

## 2. Validación de conexión
- `GET /health` devuelve 200: confirma disponibilidad de la API, **no** por sí solo la base.
- Registrar usuario de prueba único en `POST /auth/register` (`email`, `username`, `display_name`, `password`).
- Iniciar sesión en `POST /auth/login` (`identifier`, `password`).
- Buscar exactamente ese usuario en `public.users` desde SQL Editor.
- Reiniciar FastAPI y repetir el login; no duplicar la cuenta de prueba.
- Limpiar cuentas de prueba solo mediante procedimiento autorizado por el equipo y considerando claves foráneas.

Consulta segura de ejemplo (reemplaza solo el identificador ficticio):

```sql
SELECT id, email, username, display_name
FROM public.users
WHERE username = 'usuario_de_prueba';
```

## 3. Google OAuth — configuración compartida
- En Google Cloud, configurar **Google Auth Platform**, la pantalla de consentimiento y un cliente OAuth de tipo web para Supabase. `picrout@gmail.com` es correo oficial de soporte/contacto, **no** un token ni una contraseña de OAuth.
- En Google Cloud registrar como redirect autorizado la **callback exacta** indicada en Supabase Authentication → Providers → Google: `https://<project-ref>.supabase.co/auth/v1/callback`.
- En el proyecto Supabase compartido habilitar Google e introducir allí Client ID y Client Secret. **No** poner Client Secret en APK ni frontend.
- Para pruebas web locales, permitir explícitamente `http://127.0.0.1:5500/google-test.html` en Authentication → URL Configuration → Redirect URLs.
- Supabase Auth gestiona `auth.users` (UUID), mientras PicRout gestiona `public.users` (IDs propios). No son tablas intercambiables.
- La página de prueba obtiene un **access_token de Supabase**; `POST /auth/google` lo valida y emite un **JWT propio de PicRout**. No publicar ninguno de esos tokens.
- Cuenta tradicional con correo coincidente: la implementación actual devuelve **409** hasta desarrollar vinculación segura; no asociar cuentas solo por correo.

## 4. Incidencia resuelta: trigger obsoleto
En el entorno probado, `on_auth_user_created` en `auth.users` llamaba a `public.handle_new_auth_user()` y trataba de insertar en la inexistente `public.profiles`. Se inspeccionó la función y se retiró **únicamente ese trigger**. No recrearlo indiscriminadamente ni eliminar otros triggers sin auditoría. Esta corrección requiere quedar reflejada en una migración SQL versionada y revisada por el equipo.

Consulta **solo lectura** para comprobar si reapareció:

```sql
SELECT t.tgname, p.oid::regprocedure AS function_name
FROM pg_trigger AS t
JOIN pg_proc AS p ON p.oid = t.tgfoid
WHERE t.tgrelid = 'auth.users'::regclass
  AND NOT t.tgisinternal;
```

## 5. Seguridad y mantenimiento
- `backend/.env` debe estar ignorado y **no rastreado** por Git (`git ls-files -- .env` desde `backend/`).
- No enviar credenciales por chat, capturas, issues ni documentación.
- No ejecutar `DROP`, migraciones, `create_all` o scripts destructivos en la base compartida sin coordinación; `create_all` **no sustituye** migraciones.
- Revisar RLS, backups y permisos de PostgreSQL antes de despliegue. La conexión backend con credenciales de DB puede saltarse políticas que sí afectan al cliente.
- En producción: URLs OAuth verificadas, separación de entornos y gestión de secretos.

## 6. Estado comprobado el 11/11/2026
En el segundo PC: `/health`, registro, login, presencia en `public.users` y login después de reiniciar funcionaron. Google Sign-In real: API 200, nuevo usuario en `public.users` y segundo login sin duplicado. **No se ha confirmado integración Android ni pruebas completas de seguridad/producción.**
