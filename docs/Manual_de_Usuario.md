# Manual de Usuario – PicRout (RoutineAI)

**Versión:** 1.2 — documentación del backend validado y funciones previstas  
**Fecha:** 11 de noviembre de 2026  
**Equipo:** Sofía Rincón Álvarez · Juan Pablo Zárate Fernández · Sofía Bautista Díaz  
**Profesor:** Freddy León Reyes  
**Universidad Militar Nueva Granada – Ingeniería de Software**

**Slogan:** *Convierte tu día a día en tu mejor racha*

---

## 1. Introducción

PicRout (RoutineAI) es una aplicación móvil Android de seguimiento de hábitos y rutinas respaldada por Inteligencia Artificial. Permite:

- Crear rutinas personalizadas con días, hora y duración.
- Verificar el cumplimiento mediante **quiz generado por IA**.
- Mantener **rachas** diarias (solo si se completan **todas** las rutinas del día).
- Ganar **puntos** según la dificultad estimada por la IA.
- Canjear puntos en una **tienda virtual**.
- Compartir rachas, evidencias y chats en una **red social** interna.
- Recibir notificaciones de recordatorio e interacciones.

Este manual describe el uso previsto de PicRout y distingue lo **probado en backend** de lo **pendiente en Android**. Las pantallas, tienda, red social, notificaciones y APK se describen como funciones planificadas mientras no haya una prueba específica de su implementación.

---

## 2. Requisitos del dispositivo

| Requisito                    | Detalle                          |
|-----------------------------|----------------------------------|
| Sistema operativo           | Android 8.0 (API 26) o superior  |
| Cámara                      | No requerida (verificación solo por quiz) |
| Conexión a Internet         | Requerida (sincronización + IA)  |
| Almacenamiento libre        | ≥ 100 MB recomendado             |
| Permisos                    | Notificaciones (y almacenamiento si aplica) |

---

## 3. Instalación (flujo previsto de Android)

1. Abre en el navegador del teléfono la página de descarga de PicRout (landing HTML).
2. Descarga el archivo **APK**.
3. Cuando exista un APK oficial, sigue las instrucciones de instalación publicadas por el equipo y verifica la procedencia del archivo.
4. Abre el APK e instala.
5. Al abrir la app, configura los permisos de **notificaciones** que solicite; la verificación actual es solo por quiz y no requiere cámara.

> **Nota para desarrolladores:** el backend se levanta con FastAPI. Ver `README.md` del repositorio.

---

## 4. Primer acceso e inicio de sesión

### 4.1 Pantalla de bienvenida

Al abrir la app aparece la pantalla de bienvenida con tres opciones principales:

- **Registrarse**
- **Iniciar sesión**
- **Continuar con Google**

### 4.2 Registro con correo / usuario y contraseña

1. Pulsa **Registrarse**.
2. Completa:
   - Correo electrónico (válido)
   - Nombre de usuario (único)
   - Contraseña (mínimo 8 caracteres recomendado)
3. Confirma la contraseña.
4. Acepta términos si se muestran.
5. Pulsa **Crear cuenta**.

### 4.3 Inicio de sesión

1. Pulsa **Iniciar sesión**.
2. Ingresa **correo o nombre de usuario** + **contraseña**.
3. Pulsa **Entrar**.

### 4.4 Inicio de sesión con Google

**Estado:** flujo backend validado el 11/11/2026 con Google Cloud + Supabase Auth + FastAPI + PostgreSQL; botón Android pendiente.

**Flujo previsto en la aplicación:**

1. Pulsa **Continuar con Google** cuando esté disponible en Android.
2. Selecciona y autentica tu cuenta de Google.
3. Supabase Auth valida la sesión; el backend de PicRout crea o recupera el usuario y emite su token propio.

**Limitación actual:** si ya existe una cuenta tradicional con el mismo correo, el backend devuelve **409** para evitar vincular cuentas sin autorización. La vinculación segura de cuentas todavía está pendiente. No se requiere establecer una contraseña de PicRout para una cuenta Google nueva.

### 4.5 Recuperación de contraseña (OTP)

1. En la pantalla de login pulsa **¿Olvidaste tu contraseña?**.
2. Ingresa el correo asociado a la cuenta.
3. El sistema genera un **código de 6 dígitos**. El envío real por correo depende de la configuración SMTP del entorno; en desarrollo puede mostrarse en los logs del servidor.
4. El código:
   - Es de **un solo uso**.
   - Tiene validez de **10 minutos**.
5. Ingresa el código y la nueva contraseña.
6. Confirma. Si el código expira o se reutiliza, se mostrará error y deberás solicitar uno nuevo.

---

## 5. Perfil de usuario

El perfil se usa tanto en la app como en la red social.

Campos disponibles:

| Campo       | Descripción                              |
|-------------|------------------------------------------|
| Nombre      | Nombre visible                           |
| Avatar      | Imagen de perfil (propia o de tienda)    |
| Tema / Color| Personalización visual de la interfaz    |
| Biografía   | Texto corto sobre ti                     |

**Cómo editarlo:**

1. Ve a **Perfil** (icono de usuario).
2. Pulsa **Editar perfil**.
3. Modifica los campos deseados.
4. Guarda. Los cambios de avatar/marco de la tienda se aplican de inmediato.

---

## 6. Gestión de rutinas

### 6.1 Crear una rutina

1. Desde el **Home** o el menú **Rutinas** pulsa **+ Nueva rutina**.
2. Completa los datos:

| Campo          | Ejemplo / Notas                                      |
|----------------|------------------------------------------------------|
| Nombre         | “Estudiar algoritmos”                                |
| Descripción    | “Repasar grafos y árboles de decisión 1 hora”        |
| Días           | Lunes, Miércoles, Viernes (selección múltiple)       |
| Hora           | 09:00 a.m.                                           |
| Duración       | 1 h (opcional; depende del tipo de actividad)        |

3. Pulsa **Guardar**.
4. La **IA analiza** nombre + descripción y automáticamente:
   - Usa **quiz** como método de verificación.
   - Asigna un **puntaje base** según dificultad (entre 5 y 30 puntos aprox.).

### 6.2 Método de verificación

| Método (en la app) | Código interno | Descripción |
|--------------------|----------------|-------------|
| **Quiz**           | `quiz`         | La IA genera preguntas sobre la actividad; hay que aprobar ≥ 60 % |

### 6.3 Estados de una ocurrencia del día

Cada rutina genera una **ocurrencia** por día en el que aplica. Estados:

| Estado en pantalla     | Código                  | Significado                                      |
|------------------------|-------------------------|--------------------------------------------------|
| Pendiente              | `pendiente`             | Aún no se ha intentado verificar                 |
| Falta verificación     | `falta_verificacion`    | Se inició el proceso; falta responder el quiz    |
| Completada             | `completada`            | Verificación aprobada → suma puntos              |
| Incompleta             | `incompleta`            | Verificación fallida o abandonada                |
| Perdida                | `perdida`               | No se realizó a tiempo (afecta la racha)         |

### 6.4 Editar o eliminar una rutina

- Desde el listado de rutinas → menú de la rutina → **Editar** o **Eliminar** (desactivar).
- Si cambias mucho el nombre o la descripción, conviene volver a crear o dejar que el sistema reasigne método al verificar.

---

## 7. Completar una rutina (flujo de verificación)

### 7.1 Desde el día de hoy

1. Entra a **Hoy** / **Mis rutinas de hoy**.
2. Verás cada ocurrencia con su estado.
3. Pulsa **Verificar** en la que quieras completar.
4. La app inicia un **intento de verificación** y te guía según el método.

### 7.2 Flujo de quiz

1. Al iniciar la verificación, la IA genera **3 preguntas** relacionadas con la actividad.
2. Responde todas (una opción por pregunta).
3. Si aciertas al menos el **60 %** → **Completada** + puntos.
4. Si no alcanzas el umbral → **Incompleta**; puedes volver a intentar (nuevo intento).

> **Importante:** Los puntos solo se otorgan cuando el intento queda **aprobado**.

### 7.3 Cómo trabaja la IA por detrás (resumen para el usuario)

- **Sin conexión a un proveedor cloud:** reglas en español para puntos/dificultad y plantillas de quiz.
- **Con proveedor gratis opcional (p. ej. Groq o Gemini):** análisis de texto y generación de quizzes con modelo de lenguaje.
- Tú solo ves las preguntas y el resultado (aprobado / no aprobado).

---

## 8. Rachas y puntos

### 8.1 Cómo funciona la racha

- La racha **solo se mantiene o aumenta** si completas **todas** las ocurrencias del día (todas en estado **Completada**).
- Si alguna queda incompleta o perdida al cerrar el día → la racha se **rompe**.
- El sistema evita contar dos veces el mismo día (idempotencia por fecha).
- A mayor racha, mayor **bonificación** de puntos del día.

### 8.2 Puntos

- Cada rutina tiene un **puntaje base** (5–30) estimado por la IA según dificultad:
  - Bajo: levantarse, beber agua, hacer la cama → ~5–8.
  - Medio: ejercicio, limpieza, lectura corta → ~10–15.
  - Alto: estudio intenso, proyectos, varias horas → ~18–30.
- Los puntos se suman a tu saldo **solo al aprobar** la verificación.
- El saldo se consulta en **Perfil**, **Racha** o la futura **Tienda**.

---

## 9. Tienda virtual (planificada)

1. Entra a **Tienda** desde el menú principal.
2. Explora las categorías:
   - Cupones de empresas
   - Imprimibles
   - Decoración de perfil (marcos, avatares, temas, colores)
3. Selecciona el ítem deseado.
4. Confirma el canje (se descuentan los puntos).
5. Las recompensas de perfil se aplican **inmediatamente**.

> Si no tienes puntos suficientes, el sistema muestra un mensaje claro y no realiza el canje.

---

## 10. Red social (planificada)

Funciones disponibles:

- Publicar **rachas** y **evidencias** (según configuración de privacidad).
- Dar **likes**.
- **Chats** privados o de grupo (adaptado al estilo Instagram pero centrado en hábitos).
- Ver el feed de actividad de amigos / comunidad.

**Notificaciones sociales:** likes, comentarios, mensajes nuevos y menciones.

---

## 11. Notificaciones (planificadas)

La app genera notificaciones para:

- Recordatorio de rutinas programadas.
- Resultado de verificación (éxito o fallo).
- Rotura o aumento de racha.
- Interacciones sociales (likes, chats).
- Ofertas o novedades de la tienda (opcional).

Puedes gestionar los permisos desde los ajustes del sistema Android o desde **Ajustes** dentro de la app.

---

## 12. Ajustes y cierre de sesión

Desde el menú **Ajustes** puedes:

- Cerrar sesión.
- Gestionar cuenta (cambiar correo, eliminar cuenta – según disponibilidad).
- Revisar permisos.
- Contactar soporte / ver versión de la app.

La recuperación de contraseña siempre está disponible desde la pantalla de login.

---

## 13. Solución rápida de problemas comunes

| Problema                              | Qué hacer                                                                 |
|---------------------------------------|---------------------------------------------------------------------------|
| No puedo instalar el APK              | Habilitar “orígenes desconocidos”                                         |
| No llegan notificaciones              | Revisar permisos de notificaciones + batería optimizada                   |
| Código OTP no llega o expiró          | Revisar spam; solicitar un nuevo código (máx. 10 min de validez)          |
| No apruebo el quiz                    | Repasa la actividad y vuelve a intentar; el umbral es 60 % de aciertos    |
| No me suma la racha                   | Verifica que **todas** las rutinas del día estén en estado Completada     |
| Error de conexión                     | Comprueba Internet; el backend debe estar online                          |

Para errores técnicos consulta `Manual_de_Errores.md`; para preparar el entorno y probar el backend, `Guia_Supabase.md` y `Guia_Verificacion_Manual.txt`.

---

## 14. Contacto y soporte

- Correo oficial: **picrout@gmail.com** (soporte y correo previsto para notificaciones/OTP, sujeto a configuración de envío).

- Equipo de desarrollo: Sofía Rincón · Juan Pablo Zárate · Sofía Bautista
- Profesor: Freddy León Reyes
- Repositorio y documentación interna: carpeta `docs/` del proyecto PicRout

---

*Documento vivo. Se actualizará con cada sprint y según feedback de pruebas de usuario.*


## 15. Estado funcional confirmado (11/11/2026)

- **Backend probado:** salud, registro/login por correo o usuario, perfil en pruebas anteriores, recuperación OTP en pruebas anteriores, operaciones de rutinas y persistencia PostgreSQL; la guía de pruebas permite repetirlos.
- **Google probado:** `POST /auth/google` validó una sesión real de Supabase, devolvió 200, creó una fila en `public.users` y un segundo login no duplicó la cuenta.
- **Verificación:** solo `quiz`. Se eliminó la verificación por fotografías.
- **Pendiente:** integración Android del botón Google, vinculación de cuentas tradicionales, pruebas de seguridad completas y funcionalidades sociales/comerciales anunciadas.

> Este estado refleja las pruebas manuales reportadas, no una certificación de producción.
