# Manual de Errores – PicRout (RoutineAI)

**Documento vivo.**  
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
