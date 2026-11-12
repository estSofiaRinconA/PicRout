# Manual de Errores – PicRout (RoutineAI)

**Documento vivo. Actualizado: 2026-11-11.**  
Cada error se registra aquí **antes** de aplicar la solución definitiva.

---

## Formato de cada entrada

- **ID**: ERR-XXX
- **Fecha**: YYYY-MM-DD
- **Módulo**: (Auth / Rutinas / IA / Verificación / Rachas-Puntos / Tienda / Social / Notificaciones / Backend / Setup / Cliente Android)
- **Severidad**: Crítica / Alta / Media / Baja
- **Descripción**: Qué ocurrió
- **Causa raíz**:
- **Solución aplicada**:
- **Prevención**: Qué se añadió para que no vuelva a pasar
- **Estado**: Abierto / En progreso / Resuelto / Mitigado
- **Responsable**:

---

## Errores registrados

### ERR-001
- **Fecha**: 2026-10-28
- **Módulo**: Rachas-Puntos
- **Severidad**: Alta
- **Descripción**: El cálculo de racha en `backend/functions/streak.py` no era idempotente. Al evaluar el mismo día múltiples veces (por ejemplo, al refrescar el estado o marcar varias rutinas), la racha se incrementaba más de una vez por día.
- **Causa raíz**: Falta de control de fecha de último procesamiento (`last_streak_date`). La función `evaluate_day_and_update_streak` sumaba la racha sin verificar si ese día ya había sido contabilizado.
- **Solución aplicada**: Se añadió el campo `last_streak_date` en el modelo de usuario y la verificación explícita `if user.last_streak_date == day` antes de incrementar. Solo se procesa el bonus y el incremento una vez por día calendario.
- **Prevención**: Idempotencia por fecha garantizada en la lógica de racha. Pruebas de evaluación múltiple del mismo día documentadas en la guía de verificación.
- **Estado**: Resuelto
- **Responsable**: Equipo de desarrollo

### ERR-002
- **Fecha**: 2026-11-11
- **Módulo**: Verificación / IA (fotos)
- **Severidad**: Alta
- **Descripción**: Fallos recurrentes en el flujo de verificación por fotos (`single_photo` / `before_after`): uploads multipart inestables y visión poco fiable.
- **Causa raíz**: Multipart vacío/mal tipado y pipeline de visión inmaduro.
- **Solución aplicada**: **Eliminación completa** de la verificación por fotos del proyecto.
  - Borrados: `ai/llm_vision.py`, `ai/photo_validator.py`, `functions/storage_files.py`, endpoint `/photo`.
  - Método único: **quiz**. Analyzer y servicio siempre usan quiz.
  - Columnas de rutas de foto quitadas del modelo `VerificationAttempt`.
- **Prevención**: No reintroducir fotos sin diseño de upload nativo Android + tests de contrato API.
- **Estado**: Resuelto (código de fotos retirado)
- **Responsable**: Equipo de desarrollo

*(Se irán añadiendo únicamente errores reales detectados en chats, logs o pruebas.)*


## Incidencias de migración y Google Sign-In (11 de noviembre de 2026)

### ERR-003
- **Fecha:** 2026-11-11
- **Módulo:** Setup / Python
- **Severidad:** Media
- **Descripción:** Uvicorn ejecutado desde backend con ruta backend.App.main:app produjo ModuleNotFoundError: backend.
- **Causa raíz:** Directorio de trabajo incompatible con la ruta del módulo.
- **Solución aplicada:** Desde backend ejecutar `python -m uvicorn App.main:app --reload`; desde raíz, `python -m uvicorn App.main:app --app-dir backend --reload`.
- **Prevención:** Documentar ambos comandos.
- **Estado:** Resuelto según pruebas manuales; prevención automatizada pendiente
- **Responsable:** Equipo de desarrollo

### ERR-004
- **Fecha:** 2026-11-11
- **Módulo:** Setup / Python
- **Severidad:** Media
- **Descripción:** Desde la raíz, la importación `from App.config import get_settings` provocó ModuleNotFoundError: App.
- **Causa raíz:** La carpeta backend no estaba en sys.path.
- **Solución aplicada:** Añadir `--app-dir backend` cuando se ejecuta desde raíz, o trabajar desde backend.
- **Prevención:** Unificar convenciones de importación.
- **Estado:** Resuelto según pruebas manuales; prevención automatizada pendiente
- **Responsable:** Equipo de desarrollo

### ERR-005
- **Fecha:** 2026-11-11
- **Módulo:** Base de datos / Setup
- **Severidad:** Alta
- **Descripción:** Registro y login respondían bien en PC 2, pero el usuario no aparecía en Supabase.
- **Causa raíz:** Configuración local faltante (`.env` ausente); no se había acreditado la conexión compartida.
- **Solución aplicada:** Se creó y configuró `.env`; cinco pruebas posteriores confirmaron registro, login, persistencia y login tras reiniciar.
- **Prevención:** Añadir checklist de instalación para cada equipo.
- **Estado:** Resuelto según pruebas manuales; prevención automatizada pendiente
- **Responsable:** Equipo de desarrollo

### ERR-006
- **Fecha:** 2026-11-11
- **Módulo:** Auth / Python
- **Severidad:** Alta
- **Descripción:** ImportError: no se pudo importar `LoginRequest` de `App.schemas.auth`.
- **Causa raíz:** La clase faltaba después de editar el esquema para Google.
- **Solución aplicada:** Se restauró el esquema tradicional y se conservó `GoogleLoginRequest` con `access_token`.
- **Prevención:** Probar imports y Swagger antes de ejecutar OAuth.
- **Estado:** Resuelto según pruebas manuales; prevención automatizada pendiente
- **Responsable:** Equipo de desarrollo

### ERR-007
- **Fecha:** 2026-11-11
- **Módulo:** Base de datos / Configuración
- **Severidad:** Alta
- **Descripción:** PostgreSQL indicó que la base `postgres Alternativa conexión directa:` no existía.
- **Causa raíz:** Texto explicativo incorporado accidentalmente a `DATABASE_URL`.
- **Solución aplicada:** Se corrigió la URI para apuntar a la base `postgres`; el backend inició.
- **Prevención:** Verificar con `sqlalchemy.engine.make_url` sin imprimir contraseñas.
- **Estado:** Resuelto según pruebas manuales; prevención automatizada pendiente
- **Responsable:** Equipo de desarrollo

### ERR-008
- **Fecha:** 2026-11-11
- **Módulo:** Auth / Python
- **Severidad:** Media
- **Descripción:** ModuleNotFoundError: backend en `functions/supabase_auth.py`.
- **Causa raíz:** Importación `from backend.App.schemas import user` incompatible con la ejecución desde backend.
- **Solución aplicada:** Se retiró la importación innecesaria; el backend inició.
- **Prevención:** No mezclar imports `backend.App` y `App` indiscriminadamente.
- **Estado:** Resuelto según pruebas manuales; prevención automatizada pendiente
- **Responsable:** Equipo de desarrollo

### ERR-009
- **Fecha:** 2026-11-11
- **Módulo:** Supabase Auth / PostgreSQL
- **Severidad:** Alta
- **Descripción:** OAuth retornaba `Database error saving new user`; log: `relation public.profiles does not exist`.
- **Causa raíz:** El trigger `on_auth_user_created` llamaba a `public.handle_new_auth_user()`, que escribía en una tabla `public.profiles` inexistente.
- **Solución aplicada:** Después de inspeccionar la función, se retiró el trigger obsoleto y el flujo real de Google pudo avanzar.
- **Prevención:** Documentar la modificación de esquema en migración versionada y comprobar triggers antes de cambiarlos.
- **Estado:** Resuelto según pruebas manuales; prevención automatizada pendiente
- **Responsable:** Equipo de desarrollo

### ERR-010
- **Fecha:** 2026-11-11
- **Módulo:** Google Sign-In / Validación
- **Severidad:** Alta
- **Descripción:** `POST /auth/google` rechazaba una sesión real con `Identidad de Google incompleta o correo no confirmado`.
- **Causa raíz:** Validación rígida de `provider_id` y `email_confirmed_at`, sin contemplar los campos alternativos de la respuesta de Supabase.
- **Solución aplicada:** Se ajustó la lectura de identificador (`provider_id` o `identity_data.sub`) y confirmación (`email_confirmed_at` o `confirmed_at`), manteniendo validación de correo Google. Pruebas posteriores: 200, persistencia y segundo login sin duplicados.
- **Prevención:** Añadir tests con respuestas representativas de Supabase y casos de rechazo.
- **Estado:** Resuelto según pruebas manuales; prevención automatizada pendiente
- **Responsable:** Equipo de desarrollo


> **Seguridad:** nunca pegar tokens, contraseñas, `DATABASE_URL` real ni `.env` en issues o capturas; si hubo exposición pública, rotar las credenciales.
