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
- [ ] Autenticación
- [ ] Rutinas + Rachas
- [ ] Motor de IA
- [ ] Verificación
- [ ] Puntos + Tienda
- [ ] Red social
- [ ] Panel de administración
- [ ] Despliegue permanente
