# Plan de Implementación — App de Contribuciones Vecinales (AVV Ventorrillo)

**Basado en:** documento_requisitos_app_contribuciones_avv.md (v1.0)
**Fecha límite:** 01/09/2026
**Desarrollador:** Ángel Souto Martell

---

## 0. Decisiones de arquitectura (antes de escribir código)

Dado el plazo (días, no semanas) y tu stack habitual, la recomendación es optimizar para velocidad de desarrollo y robustez conocida, no para novedad tecnológica.

| Capa | Elección recomendada | Motivo |
|---|---|---|
| Backend | Python + FastAPI | Tipado, validación automática con Pydantic, rápido de escribir, encaja con tu experiencia en Python/APIs |
| Base de datos | PostgreSQL | Concurrencia de escritura robusta out-of-the-box, tipos `ENUM`/`NUMERIC` adecuados para importes, ya usas Docker |
| ORM | SQLAlchemy + Alembic | Migraciones versionadas, evita SQL manual repetitivo |
| Frontend | Vue 3 + Vite (o React si te sientes más cómodo) SPA responsive | Un único formulario reactivo con autocompletados, consumo de API REST |
| Autenticación | JWT en cookie httpOnly o localStorage + bcrypt para contraseñas | Simple, sin estado en servidor, encaja con API REST |
| Despliegue | Docker Compose (app + Postgres + Nginx/Caddy como proxy inverso con TLS) | Ya lo dominas, reproducible, fácil rollback |
| Backups | `pg_dump` programado vía cron dentro de un contenedor auxiliar, subido a almacenamiento externo | Datos de dinero real: backups automáticos no son opcionales |

Si prefieres reducir aún más la superficie para cumplir el plazo, una alternativa válida es Django + Django Admin (te da CRUD y gestión de calles "gratis" para el admin), pero FastAPI + SPA te da una experiencia móvil más pulida para los cobradores, que es la parte crítica de UX aquí.

---

## 1. Esquema de base de datos (PostgreSQL)

```sql
CREATE TYPE resultado_visita AS ENUM ('aporta', 'no_abre', 'no_aporta', 'reintentar', 'pasara_por_local');
CREATE TYPE origen_aportacion AS ENUM ('puerta', 'local');
CREATE TYPE forma_pago AS ENUM ('efectivo', 'bizum');

CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre_usuario VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    es_admin BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE equipos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE calles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE NOT NULL,
    creado_por INTEGER REFERENCES usuarios(id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_calles_nombre_trgm ON calles USING gin (nombre gin_trgm_ops);

CREATE TABLE viviendas (
    id SERIAL PRIMARY KEY,
    calle_id INTEGER NOT NULL REFERENCES calles(id),
    portal VARCHAR(10) NOT NULL,
    piso VARCHAR(5),
    puerta VARCHAR(20),
    nombre VARCHAR(150),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (calle_id, portal, piso, puerta)
);
CREATE INDEX idx_viviendas_calle ON viviendas(calle_id);

CREATE TABLE visitas (
    id SERIAL PRIMARY KEY,
    vivienda_id INTEGER NOT NULL REFERENCES viviendas(id),
    equipo_id INTEGER NOT NULL REFERENCES equipos(id),
    registrado_por INTEGER NOT NULL REFERENCES usuarios(id),
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    resultado resultado_visita NOT NULL,
    observaciones TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_visitas_vivienda ON visitas(vivienda_id);
CREATE INDEX idx_visitas_fecha ON visitas(fecha);
CREATE INDEX idx_visitas_equipo_fecha ON visitas(equipo_id, fecha);

CREATE TABLE aportaciones (
    id SERIAL PRIMARY KEY,
    vivienda_id INTEGER REFERENCES viviendas(id),
    nombre_persona VARCHAR(150),
    visita_id INTEGER REFERENCES visitas(id),
    origen origen_aportacion NOT NULL,
    equipo_id INTEGER NOT NULL REFERENCES equipos(id),
    registrado_por INTEGER NOT NULL REFERENCES usuarios(id),
    importe NUMERIC(8,2) NOT NULL CHECK (importe > 0),
    forma_pago forma_pago NOT NULL,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    anio_campania INTEGER NOT NULL,
    observaciones TEXT,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (vivienda_id IS NOT NULL OR nombre_persona IS NOT NULL)
);
CREATE INDEX idx_aportaciones_vivienda_anio ON aportaciones(vivienda_id, anio_campania);
CREATE INDEX idx_aportaciones_fecha ON aportaciones(fecha);
CREATE INDEX idx_aportaciones_equipo_fecha ON aportaciones(equipo_id, fecha);
```

**Notas de diseño:**
- `gin_trgm_ops` (extensión `pg_trgm`) permite el autocompletado de calles por coincidencia parcial de texto, no solo prefijo. Activar con `CREATE EXTENSION pg_trgm;`.
- `anio_campania` se guarda de forma explícita (no solo derivado de `fecha`) para que las agregaciones anuales sean triviales y rápidas incluso si algún día se registra una aportación con fecha fuera de temporada.
- `piso` y `puerta` son `VARCHAR` y no `ENUM`/`INTEGER` para admitir tus valores especiales (piso "0", puertas "centro-izquierda", letras hasta la K) sin rigidez, validando el conjunto permitido en la capa de aplicación (más flexible que forzarlo en el tipo de columna).
- El `UNIQUE (calle_id, portal, piso, puerta)` en viviendas evita duplicar la misma vivienda por error de tecleo del admin.

---

## 2. Valores fijos de formulario (frontend)

Basado en tus anotaciones finales:

```
PISOS = ["0","1","2","3","4","5","6","7","8","9","10","11","12"]
PUERTAS = ["Izquierda","Centro-izquierda","Centro","Centro-derecha","Derecha",
           "A","B","C","D","E","F","G","H","I","J","K"]
```

Ambos como listas desplegables (`<select>`), no campos de texto libre, para evitar variantes ortográficas del mismo valor (p. ej. "Dcha" vs "Derecha") que romperían agregaciones futuras.

---

## 3. API REST — endpoints principales

| Método | Ruta | Descripción | Rol |
|---|---|---|---|
| POST | `/auth/login` | Devuelve JWT + fuerza selección de equipo | Todos |
| POST | `/auth/seleccionar-equipo` | Fija equipo activo en la sesión/token | Todos |
| GET | `/calles?buscar=texto` | Autocompletado de calles (trigram) | Todos |
| POST | `/calles` | Crear calle nueva | Admin |
| GET | `/viviendas?calle_id=&portal=` | Buscar vivienda existente | Todos |
| POST | `/viviendas` | Crear vivienda si no existe aún | Todos |
| GET | `/viviendas/{id}/historico` | Aportaciones agregadas por año de esa vivienda | Todos |
| POST | `/visitas` | Registrar visita (con o sin aportación anidada) | Todos |
| POST | `/aportaciones` | Registrar aportación directa (caso local / sin domicilio) | Todos |
| PATCH/DELETE | `/visitas/{id}`, `/aportaciones/{id}` | Editar/borrar registro | Todos (según regla de negocio) |
| GET | `/reportes/diario?fecha=` | Total por equipo y total general de un día | Admin |
| GET | `/reportes/dashboard?anio=&calle_id=&equipo_id=` | Estadísticas agregadas filtrables | Admin |
| GET | `/reportes/exportar-excel?anio=` | Descarga `.xlsx` | Admin |

El endpoint `POST /visitas` acepta opcionalmente un bloque `aportacion` anidado para que, cuando el resultado sea `aporta`, se cree visita + aportación en una sola transacción atómica (evita estados inconsistentes si la conexión se cae a mitad de guardado).

---

## 4. Pantallas (frontend)

1. **Login** → selección de equipo (si el usuario tiene más de un equipo posible).
2. **Registro rápido** (pantalla principal, la que más se usa): buscador de calle con autocompletado → selección/creación de portal-piso-puerta → línea de histórico ("año anterior: X €" + botón "ver más años") → selector de resultado → si `aporta`, campos de importe/forma de pago/observaciones → guardar.
3. **Aportación en el local**: formulario simplificado (vivienda opcional o nombre de persona, importe, forma de pago, observaciones).
4. **Listado del día**: registros creados por el equipo actual en la sesión, con opción de editar/borrar.
5. **Dashboard admin**: filtros por año/calle/equipo, totales, gráfico de evolución multianual, gestión de calles, gestión de usuarios/equipos, exportar a Excel.

---

## 5. Migración de datos (script único, antes de abrir la app a cobradores)

1. Exportar la hoja de Google Sheets a CSV.
2. Script Python (pandas) que:
   - Normaliza texto de `calle` (trim, capitalización) y hace `INSERT ... ON CONFLICT DO NOTHING` en `calles`.
   - Inserta `viviendas` únicas por `(calle, portal, planta, puerta)`.
   - Inserta cada fila como `aportaciones` con `origen='puerta'`, `equipo_id` a un equipo genérico "Campaña anterior" (crear ese equipo dummy) y `registrado_por` a un usuario "sistema/migración".
   - Valida que `año` coincida con `EXTRACT(YEAR FROM fecha)`; loggea discrepancias en un CSV de errores para revisión manual antes de confirmar el import.
3. Ejecutar en una base de datos de staging primero, validar totales por año contra los totales que recuerde tu padre, y solo entonces aplicar en producción.

---

## 6. Cronograma detallado (hasta el 01/09/2026)

Dado que hoy es 28/08 y el plazo es 01/09, el margen real es muy ajustado (unos 4 días). Prioriza lo imprescindible para operar el día 1 y deja el resto para iteración en caliente durante la campaña.

**Día 1 (28/08) — Infraestructura y modelo de datos**
- Levantar Docker Compose: Postgres + backend + Nginx/Caddy con TLS.
- Crear esquema SQL (sección 1), aplicar migraciones con Alembic.
- Script de migración de la hoja de Google Sheets, ejecutado en staging.
- Endpoints de auth (login, selección de equipo) y CRUD básico de usuarios/equipos.

**Día 2 (29/08) — Núcleo funcional: visitas y aportaciones**
- Endpoints `POST /visitas`, `POST /aportaciones`, `GET /calles` (autocompletado), `GET/POST /viviendas`.
- Endpoint de histórico por vivienda (`GET /viviendas/{id}/historico`).
- Pantalla de registro rápido (la más crítica) en frontend, con los desplegables fijos de piso/puerta.

**Día 3 (30/08) — Reportes, edición y aportación en local**
- Pantalla de aportación en el local.
- Listado del día con edición/borrado.
- Reporte diario por equipo y total (`GET /reportes/diario`).
- Exportación a Excel básica.

**Día 4 (31/08) — Endurecimiento, pruebas y despliegue final**
- Pruebas manuales de los 5 flujos completos (aporta, no_abre, no_aporta, reintentar, pasara_por_local) más caso "sin domicilio".
- Pruebas de concurrencia real: dos usuarios distintos creando registros simultáneamente desde dos móviles.
- Backups automáticos (`pg_dump` programado) y verificación de que restaura correctamente.
- Crear usuarios y equipos reales para los cobradores, entregar credenciales.
- Migración definitiva de datos a producción (no staging).

**01/09 — Lanzamiento**
- Acompañamiento el primer día de campaña por si surge algún bug de uso real; el dashboard completo con gráficos avanzados puede llegar como iteración durante la primera semana, ya que no bloquea el registro de campo.

---

## 7. Qué queda fuera del MVP y se añade después del lanzamiento

- Gráficos de evolución multianual más elaborados en el dashboard (de momento basta una tabla agregada por año).
- Pop-up detallado de histórico multianual (el MVP puede mostrar solo "año anterior" en texto y añadir el pop-up en la iteración 2 si el tiempo no llega).
- PWA instalable con icono en pantalla de inicio (la versión web responsive ya es funcional sin esto).
- Filtros avanzados de dashboard por rango de fechas personalizado.

Esta priorización asegura que el 1 de septiembre la app cubra el 100% del flujo operativo real (lo que necesitan los cobradores en la calle), aunque el panel de análisis del administrador llegue algo más pulido en los días siguientes.
