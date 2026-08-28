# Plan de Implementación v2 — App de Contribuciones Vecinales (AVV Ventorrillo)

**Basado en:** [documento_requisitos_app_contribuciones_avv.md](file:///home/ubuntu/avvVento_collection/notas/documento_requisitos_app_contribuciones_avv.md) (v1.0)  
**Plan original:** [plan_implementacion_app_avv.md](file:///home/ubuntu/avvVento_collection/docs/plan_implementacion_app_avv.md)  
**Fecha límite:** 01/09/2026  
**Desarrollador:** Ángel Souto Martell  

---

## Cambios respecto al plan v1

> [!IMPORTANT]
> Este plan sustituye completamente al v1. Todas las preguntas abiertas del plan anterior están resueltas. El plan está listo para ejecución directa sin decisiones pendientes.

1. **Subdominio confirmado**: `avv.eingel.me`. README incluirá sección de cambio de dominio futuro.
2. **Migración adaptada al CSV real** (`old-data/Copia de pagos_vecinos_v2.xlsx - Data.csv`):
   - Solo se importan filas con importe numérico (se descartan `X`, `No`, `Lc`, `LC`, `C`, etc.)
   - Año `2026` → se convierte a `2025`. Año `2024` → se mantiene como `2024`.
   - Comas decimales entrecomilladas (`"2,30"`) y puntos decimales (`10.20`) manejados.
   - Normalización de puertas abreviadas (`Dcha` → `Derecha`, etc.)
3. **Gestión de equipos/cobradores enteramente desde el panel admin** (no pre-creados).
4. **DNS resuelta**: el usuario creará el registro A para `avv.eingel.me`.
5. **Puertos sin conflicto** verificados contra la auditoría del servidor.

---

## 0. Auditoría de infraestructura actual

### Puertos ocupados en el servidor

| Puerto | Servicio | Bind |
|--------|----------|------|
| 80, 443 | **Caddy** (proxy inverso global, systemd) | `*` |
| 2019 | Caddy admin API | `127.0.0.1` |
| 8000 | blog-api (FastAPI) | `0.0.0.0` |
| 8001 | padel-service backend | `127.0.0.1` |
| 8090 | Apache (blog estático) | `*` |
| 3000 | Grafana | `0.0.0.0` |
| 3001 | padel-service frontend | `127.0.0.1` |
| 3100 | Loki | `0.0.0.0` |
| 8080 | cAdvisor | `0.0.0.0` |
| 9090 | Prometheus | `0.0.0.0` |
| 9100 | Node Exporter | `0.0.0.0` |
| 9150 | Minecraft Exporter | `0.0.0.0` |
| 25565, 19565 | Minecraft | `0.0.0.0` |
| 22 | SSH | `0.0.0.0` |

### Puertos asignados a la app AVV (todos libres ✅)

| Componente | Puerto HOST | Puerto CONTENEDOR | Bind |
|------------|-------------|--------------------|----- |
| Backend (FastAPI) | **8002** | 8000 | `127.0.0.1` |
| Frontend (Nginx sirviendo SPA) | **3002** | 80 | `127.0.0.1` |
| PostgreSQL | **5433** | 5432 | `127.0.0.1` |

### Patrón de despliegue (idéntico a padel-service)

```
Internet → Caddy (HOST, systemd, 80/443 con TLS automático)
  └── avv.eingel.me
        ├── /api/* → strip_prefix /api → reverse_proxy 127.0.0.1:8002
        └── /*     → reverse_proxy 127.0.0.1:3002
```

---

## 1. Decisiones de arquitectura

| Capa | Elección | Motivo |
|------|----------|--------|
| **Backend** | Python 3.12 + FastAPI | Tipado, validación con Pydantic, rápido de escribir |
| **Base de datos** | PostgreSQL 16 (Alpine) | Concurrencia, `NUMERIC` para importes, `pg_trgm` para autocompletado |
| **ORM** | SQLAlchemy 2.0 (async) + Alembic | Migraciones versionadas, modelos tipados |
| **Frontend** | Vue 3 + Vite (SPA) | Reactivo, autocompletados, experiencia móvil fluida |
| **Autenticación** | JWT en `localStorage` + bcrypt | Sin estado en servidor, simple para API REST |
| **Proxy inverso** | Caddy del HOST (ya en ejecución) | TLS automático, consistente con el resto de servicios |
| **Contenedorización** | Docker Compose v2 | 3 servicios: backend, frontend (nginx), postgres |
| **Backups** | `pg_dump` por cron del host | Datos de dinero real, backup diario obligatorio |

---

## 2. Estructura de carpetas del proyecto

```
avvVento_collection/
├── README.md                          ← completo con instrucciones de despliegue
├── docker-compose.yml
├── .env.example                       ← plantilla de variables de entorno
├── .env                               ← variables reales (en .gitignore)
├── .gitignore
├── backup_avv.sh                      ← script de backup automático
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    ← FastAPI app, CORS, lifespan
│   │   ├── config.py                  ← Settings desde variables de entorno
│   │   ├── database.py                ← engine, session, Base
│   │   ├── models.py                  ← SQLAlchemy models
│   │   ├── schemas.py                 ← Pydantic schemas
│   │   ├── auth.py                    ← JWT, bcrypt, dependencia current_user
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth_router.py
│   │   │   ├── calles_router.py
│   │   │   ├── viviendas_router.py
│   │   │   ├── visitas_router.py
│   │   │   ├── aportaciones_router.py
│   │   │   ├── reportes_router.py
│   │   │   ├── usuarios_router.py     ← CRUD admin de usuarios/cobradores
│   │   │   └── equipos_router.py      ← CRUD admin de equipos
│   │   └── utils/
│   │       └── excel_export.py        ← Generación de .xlsx con openpyxl
│   └── scripts/
│       └── migrar_sheets.py           ← Script de migración desde CSV
│
├── frontend/
│   ├── Dockerfile                     ← Multi-stage: build con node → serve con nginx
│   ├── nginx.conf                     ← SPA fallback, cache de estáticos
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── router/
│       │   └── index.js
│       ├── stores/
│       │   └── auth.js                ← Pinia store para JWT + equipo activo
│       ├── api/
│       │   └── client.js              ← Axios instance con interceptor JWT
│       ├── views/
│       │   ├── LoginView.vue
│       │   ├── RegistroRapidoView.vue ← pantalla principal cobradores
│       │   ├── AportacionLocalView.vue
│       │   ├── ListadoDiaView.vue
│       │   └── DashboardView.vue      ← solo admin
│       └── components/
│           ├── BuscadorCalle.vue       ← autocompletado con debounce
│           ├── SelectorVivienda.vue    ← portal + piso + puerta
│           ├── HistoricoVivienda.vue   ← línea compacta + popup
│           ├── FormularioVisita.vue
│           ├── FormularioAportacion.vue
│           ├── GestionEquipos.vue      ← CRUD de equipos (admin)
│           ├── GestionUsuarios.vue     ← CRUD de usuarios/cobradores (admin)
│           ├── GestionCalles.vue       ← crear calles (admin)
│           └── NavBar.vue
│
├── old-data/                          ← datos del año anterior
│   └── Copia de pagos_vecinos_v2.xlsx - Data.csv
│
├── backups/                           ← volumen de backups (en .gitignore)
│
├── docs/
│   └── plan_implementacion_app_avv.md
│
└── notas/                             ← (en .gitignore)
```

---

## 3. Esquema de base de datos (PostgreSQL 16)

```sql
-- Activar extensión para autocompletado fuzzy de calles
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Tipos enumerados
CREATE TYPE resultado_visita AS ENUM (
    'aporta', 'no_abre', 'no_aporta', 'reintentar', 'pasara_por_local'
);
CREATE TYPE origen_aportacion AS ENUM ('puerta', 'local');
CREATE TYPE forma_pago AS ENUM ('efectivo', 'bizum');

-- Usuarios del sistema (gestionados por admin desde la app)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    nombre_usuario VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    es_admin BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Equipos de cobro (gestionados por admin desde la app)
CREATE TABLE equipos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

-- Calles del barrio (solo admin puede crear)
CREATE TABLE calles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) UNIQUE NOT NULL,
    creado_por INTEGER REFERENCES usuarios(id),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_calles_nombre_trgm ON calles USING gin (nombre gin_trgm_ops);

-- Viviendas (combinación única calle+portal+piso+puerta)
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

-- Visitas puerta a puerta
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

-- Aportaciones económicas
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
    -- Debe tener vivienda O nombre_persona (o ambos)
    CHECK (vivienda_id IS NOT NULL OR nombre_persona IS NOT NULL)
);
CREATE INDEX idx_aportaciones_vivienda_anio ON aportaciones(vivienda_id, anio_campania);
CREATE INDEX idx_aportaciones_fecha ON aportaciones(fecha);
CREATE INDEX idx_aportaciones_equipo_fecha ON aportaciones(equipo_id, fecha);
```

**Notas de diseño:**
- `gin_trgm_ops` permite autocompletado de calles por coincidencia parcial (no solo prefijo).
- `anio_campania` se guarda explícitamente (no derivado de `fecha`) para agregaciones anuales rápidas.
- `piso` y `puerta` son `VARCHAR` para admitir valores especiales ("0", "centro-izquierda", letras hasta "K"); la validación se hace en la capa de aplicación.
- `UNIQUE (calle_id, portal, piso, puerta)` evita duplicar la misma vivienda.

---

## 4. Valores fijos de formulario (frontend)

```javascript
const PISOS = ["0","1","2","3","4","5","6","7","8","9","10","11","12"];

const PUERTAS = [
    "Izquierda", "Centro-izquierda", "Centro", "Centro-derecha", "Derecha",
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"
];

const RESULTADOS_VISITA = [
    { value: "aporta",            label: "Aporta" },
    { value: "no_abre",           label: "No abre" },
    { value: "no_aporta",         label: "No aporta" },
    { value: "reintentar",        label: "Reintentar" },
    { value: "pasara_por_local",  label: "Pasará por el local" },
];

const FORMAS_PAGO = [
    { value: "efectivo", label: "Efectivo" },
    { value: "bizum",    label: "Bizum" },
];
```

Ambos como `<select>` desplegables, nunca texto libre, para evitar variantes ortográficas.

---

## 5. API REST — Endpoints

### Autenticación

| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| `POST` | `/auth/login` | Login con usuario/contraseña, devuelve JWT. El body incluye `equipo_id` | Todos |
| `POST` | `/auth/cambiar-equipo` | Cambia equipo activo durante la sesión (nuevo JWT) | Todos |
| `GET` | `/auth/me` | Devuelve datos del usuario autenticado | Todos |

### Calles

| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| `GET` | `/calles?q=texto` | Autocompletado por trigram (min 2 chars) | Todos |
| `POST` | `/calles` | Crear calle nueva | Admin |
| `GET` | `/calles` | Listar todas las calles (sin filtro, para gestión) | Admin |

### Viviendas

| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| `GET` | `/viviendas?calle_id=&portal=&piso=&puerta=` | Buscar vivienda existente | Todos |
| `POST` | `/viviendas` | Crear vivienda si no existe | Todos |
| `GET` | `/viviendas/{id}/historico` | Aportaciones agregadas por año | Todos |

### Visitas

| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| `POST` | `/visitas` | Registrar visita (opcionalmente con aportación anidada si resultado=aporta) | Todos |
| `PATCH` | `/visitas/{id}` | Editar visita | Todos |
| `DELETE` | `/visitas/{id}` | Borrar visita | Todos |

### Aportaciones

| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| `POST` | `/aportaciones` | Aportación directa (local / sin domicilio) | Todos |
| `PATCH` | `/aportaciones/{id}` | Editar aportación | Todos |
| `DELETE` | `/aportaciones/{id}` | Borrar aportación | Todos |
| `GET` | `/aportaciones?fecha=&equipo_id=` | Listado del día (filtrable) | Todos |

### Reportes (solo admin)

| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| `GET` | `/reportes/diario?fecha=` | Total por equipo y total general | Admin |
| `GET` | `/reportes/dashboard?anio=&calle_id=&equipo_id=` | Estadísticas agregadas | Admin |
| `GET` | `/reportes/exportar-excel?anio=` | Descarga `.xlsx` | Admin |

### Gestión de equipos (solo admin)

| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| `GET` | `/equipos` | Listar equipos (todos, incluso inactivos) | Admin |
| `POST` | `/equipos` | Crear equipo nuevo | Admin |
| `PATCH` | `/equipos/{id}` | Editar equipo (renombrar, activar/desactivar) | Admin |
| `DELETE` | `/equipos/{id}` | Desactivar equipo (soft delete: `activo=false`) | Admin |

### Gestión de usuarios/cobradores (solo admin)

| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| `GET` | `/usuarios` | Listar usuarios (todos, incluso inactivos) | Admin |
| `POST` | `/usuarios` | Crear usuario/cobrador (nombre_usuario + contraseña) | Admin |
| `PATCH` | `/usuarios/{id}` | Editar usuario (cambiar contraseña, activar/desactivar, cambiar rol) | Admin |
| `DELETE` | `/usuarios/{id}` | Dar de baja cobrador (soft delete: `activo=false`) | Admin |

> [!NOTE]
> - `POST /visitas` acepta un bloque `aportacion` anidado para crear visita + aportación en **una sola transacción atómica** cuando el resultado es `aporta`.
> - Los DELETE de equipos y usuarios son **soft deletes** (ponen `activo=false`), nunca borrado físico, para preservar la integridad referencial de los registros históricos.
> - Los equipos y usuarios inactivos no aparecen en los desplegables de selección pero sí en el panel de gestión admin.

---

## 6. Pantallas (frontend Vue 3)

### 6.1 Login
- Usuario + contraseña + selector de equipo (desplegable con equipos activos)
- Al autenticar, guarda JWT en localStorage y redirige a Registro Rápido

### 6.2 Registro Rápido (pantalla principal — cobradores)
1. **Buscador de calle** con autocompletado (debounce 300ms, min 2 chars, consulta `/calles?q=`)
2. **Selector de vivienda**: Portal (texto libre) + Piso (select fijo) + Puerta (select fijo)
3. **Histórico compacto**: línea "Año anterior: X €" + botón "Ver más años" → popup modal con tabla multianual
4. **Selector de resultado** (botones grandes para móvil, táctiles)
5. Si resultado = `aporta`: campos Importe + Forma de pago + Observaciones
6. Botón **Guardar** → `POST /visitas` (con aportación anidada si aplica)
7. Toast de confirmación + limpiar formulario para siguiente visita

### 6.3 Aportación en el Local
- Formulario simplificado: vivienda (opcional, mismo buscador) O nombre de persona
- Importe + forma de pago + observaciones
- `POST /aportaciones` con `origen = local`

### 6.4 Listado del Día
- Registros del equipo actual en la fecha actual
- Cada fila: calle, portal/piso/puerta, resultado, importe, hora
- Botones de editar/borrar en cada fila
- Total del día del equipo al final

### 6.5 Dashboard Admin
- **Filtros**: año campaña, calle, equipo
- **Tarjetas resumen**: total recaudado, nº aportaciones, nº visitas, media por vivienda
- **Tabla desglosada** por equipo
- **Botón "Exportar a Excel"**
- **Pestaña/sección "Gestión"** con 3 subsecciones:
  - **Equipos**: crear nuevo, ver lista con toggle activar/desactivar, renombrar
  - **Cobradores**: dar de alta (nombre_usuario + contraseña), ver lista con toggle activar/desactivar, resetear contraseña
  - **Calles**: crear nueva calle

### 6.6 Navegación
- **NavBar inferior** (estilo app móvil): Registro | Local | Mi día | (Dashboard si admin)
- Indicador de equipo activo + botón para cambiar equipo
- Botón de cerrar sesión

---

## 7. Docker Compose definitivo

```yaml
# docker-compose.yml
services:

  # ── PostgreSQL 16 ──────────────────────────────────────────────
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "127.0.0.1:5433:5432"    # Solo localhost, para depuración/backups
    volumes:
      - avv_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 3s
      retries: 5

  # ── Backend FastAPI ────────────────────────────────────────────
  backend:
    build: ./backend
    restart: unless-stopped
    ports:
      - "127.0.0.1:8002:8000"   # Solo localhost (Caddy del host hace proxy)
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      SECRET_KEY: ${SECRET_KEY}
      ADMIN_DEFAULT_PASSWORD: ${ADMIN_DEFAULT_PASSWORD}
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./old-data:/app/old-data    # Para script de migración

  # ── Frontend (Vue 3 SPA servida por Nginx) ─────────────────────
  frontend:
    build: ./frontend
    restart: unless-stopped
    ports:
      - "127.0.0.1:3002:80"     # Solo localhost (Caddy del host hace proxy)

volumes:
  avv_pgdata:
    name: avv_pgdata
```

### Variables de entorno (.env.example)

```bash
# ══════════════════════════════════════════════════════════════
# App Contribuciones AVV Ventorrillo — Variables de entorno
# Copiar a .env y rellenar con valores reales de producción
# ══════════════════════════════════════════════════════════════

# Base de datos PostgreSQL
POSTGRES_DB=avv_ventorrillo
POSTGRES_USER=avv_user
POSTGRES_PASSWORD=CAMBIAR_EN_PRODUCCION

# Backend FastAPI
SECRET_KEY=CAMBIAR_POR_CLAVE_ALEATORIA_LARGA
ADMIN_DEFAULT_PASSWORD=CAMBIAR_EN_PRODUCCION

# El backend usa DATABASE_URL construida automáticamente en docker-compose.yml
```

---

## 8. Configuración de Caddy (añadir al Caddyfile del HOST)

Se añade un bloque nuevo a `/etc/caddy/Caddyfile` **sin tocar nada existente**:

```caddyfile
avv.eingel.me {
    handle /api/* {
        uri strip_prefix /api
        reverse_proxy localhost:8002
    }

    handle {
        reverse_proxy localhost:3002
    }

    log {
        output file /var/log/caddy/avv.log
    }
}
```

Tras añadir el bloque, recargar Caddy sin downtime:
```bash
sudo systemctl reload caddy
```

> [!NOTE]
> **Requisito previo**: crear registro DNS tipo A para `avv.eingel.me` → `51.83.6.229` en el panel DNS de `eingel.me`. Caddy gestionará el certificado TLS automáticamente.

---

## 9. Migración de datos (Google Sheets → PostgreSQL)

### 9.1 Análisis del CSV real

**Archivo**: `old-data/Copia de pagos_vecinos_v2.xlsx - Data.csv`  
**Formato**: CSV con separador `,`, encoding UTF-8, fin de línea `\r\n`

```
ID,Calle,Portal,Puerta,Planta,Año,Importe,FechaPago,Observaciones
```

> [!WARNING]
> El orden de columnas del CSV real es **Puerta antes de Planta** (al revés de lo que asumía el documento de requisitos).

**Estadísticas del dataset** (1258 filas de datos):
- **9 calles únicas**: Alcalde Jaime Hervada, Alcalde Salorio Suárez, Francisco Miguel, Jose Eduardo Seijas, Luis Huici, Monasterio de Caaveiro, Peñamaría de Llano, Rodrigo A. De Santiago, Teixeira de Pascoaei
- **Años**: mayoritariamente `2025`, algunos `2026` (realmente 2025), 1 fila con `2024`
- **Valores de Importe no monetarios** (se DESCARTAN):
  - `X` → significaba "no abre" en la hoja original
  - `No` → significaba "no aporta"
  - `Lc` / `LC` → significaba "pasará por el local"
  - `C` → significado ambiguo, se descarta
- **Importes con formato especial** (se IMPORTAN):
  - `"2,30"` → coma decimal entrecomillada → interpretar como `2.30`
  - `10.20` → punto decimal → interpretar directamente

### 9.2 Normalización de puertas

El CSV usa abreviaturas inconsistentes en mayúsculas/minúsculas. Mapa de normalización:

| Valor en CSV (case-insensitive) | Valor normalizado en la app |
|---|---|
| `Dcha`, `DCHA` | `Derecha` |
| `Izq`, `Izda`, `IZDA` | `Izquierda` |
| `Ctro Dcha`, `Ctro dcha`, `Ctro dcho` | `Centro-derecha` |
| `Ctro Izq`, `Ctro izq` | `Centro-izquierda` |
| `A`, `B`, `C`, `D`, `E`, `F`, `G` (ya en uso) | Sin cambio (mantener mayúscula) |

### 9.3 Reglas de transformación del año

| Año en CSV | `anio_campania` en BD |
|---|---|
| `2024` | `2024` (se mantiene) |
| `2025` | `2025` (se mantiene) |
| `2026` | `2025` (se corrige, realmente son de 2025) |

### 9.4 Script de migración (`backend/scripts/migrar_sheets.py`)

El script:

1. **Lee** el CSV con `pandas`, manejando encoding UTF-8 y `\r\n`
2. **Filtra**: descarta filas donde `Importe` no es convertible a número (`X`, `No`, `Lc`, `LC`, `C`, vacío, etc.)
3. **Parsea importes**:
   - Si contiene coma y está entrecomillado: reemplaza `,` por `.` y convierte a `float`
   - Si ya tiene punto decimal: convierte directamente
   - Si es entero: convierte directamente
4. **Normaliza puertas** según el mapa de la sección 9.2
5. **Corrige años**: `2026` → `2025`, mantiene `2024` y `2025`
6. **Normaliza calles**: `str.strip()`, capitalización consistente con `str.title()` o mantener original si ya es correcto
7. **Inserta calles** únicas (`INSERT ... ON CONFLICT DO NOTHING`)
8. **Inserta viviendas** únicas por `(calle_id, portal, piso, puerta)` con `ON CONFLICT DO NOTHING`
9. **Crea entidades auxiliares**:
   - Equipo dummy: `"Campaña anterior"` (con `activo=false` para que no aparezca en los selectores)
   - Usuario sistema: `"sistema_migracion"` (con `activo=false`)
10. **Inserta cada fila válida** como aportación con:
    - `origen = 'puerta'`
    - `forma_pago = 'efectivo'` (asumido, la hoja no lo distinguía)
    - `equipo_id` → equipo "Campaña anterior"
    - `registrado_por` → usuario "sistema_migracion"
    - `fecha` → parseada desde `FechaPago` (formato `dd/mm/yyyy`)
    - `anio_campania` → según regla de la sección 9.3
11. **Genera informe de migración**: total procesadas, importadas, descartadas, calles, viviendas, errores
12. **Loguea discrepancias** en `old-data/errores_migracion.csv`

### 9.5 Ejecución

```bash
# Ejecutar contra la base de datos del contenedor
docker compose exec backend python scripts/migrar_sheets.py

# Verificar totales
docker compose exec db psql -U avv_user -d avv_ventorrillo -c \
  "SELECT anio_campania, COUNT(*), SUM(importe) FROM aportaciones GROUP BY anio_campania ORDER BY anio_campania;"

# Verificar calles importadas
docker compose exec db psql -U avv_user -d avv_ventorrillo -c \
  "SELECT nombre FROM calles ORDER BY nombre;"

# Verificar viviendas
docker compose exec db psql -U avv_user -d avv_ventorrillo -c \
  "SELECT COUNT(*) FROM viviendas;"
```

---

## 10. Backups automáticos

### Script de backup (`backup_avv.sh` en la raíz del proyecto)

```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/avvVento_collection/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=30

mkdir -p "$BACKUP_DIR"

docker compose -f /home/ubuntu/avvVento_collection/docker-compose.yml \
  exec -T db pg_dump -U avv_user -d avv_ventorrillo \
  | gzip > "$BACKUP_DIR/avv_backup_${TIMESTAMP}.sql.gz"

# Borrar backups de más de 30 días
find "$BACKUP_DIR" -name "avv_backup_*.sql.gz" -mtime +${KEEP_DAYS} -delete
```

### Cron del host (diario a las 03:00)
```bash
# Añadir con: crontab -e
0 3 * * * /home/ubuntu/avvVento_collection/backup_avv.sh >> /var/log/avv_backup.log 2>&1
```

### Restauración
```bash
gunzip -c backups/avv_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose exec -T db psql -U avv_user -d avv_ventorrillo
```

---

## 11. Dockerfiles

### Backend Dockerfile (`backend/Dockerfile`)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema para asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Alembic migrations al arrancar + uvicorn
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

### Frontend Dockerfile (`frontend/Dockerfile`)

```dockerfile
# Etapa 1: Build
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Etapa 2: Servir con Nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### Frontend nginx.conf (`frontend/nginx.conf`)

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback: todas las rutas van a index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache agresivo para estáticos con hash en nombre
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 12. Contenido del README.md

El README.md debe contener las siguientes secciones:

### 12.1 Cabecera
- Título: "App de Contribuciones Vecinales — AVV Ventorrillo"
- Descripción breve del propósito
- Badge de estado (si aplica)

### 12.2 Requisitos previos
- Docker Engine ≥ 24.x
- Docker Compose v2 (plugin `docker compose`)
- Caddy ≥ 2.x ejecutándose como servicio systemd en el host
- Dominio con registro DNS tipo A apuntando al servidor

### 12.3 Inicio rápido
```bash
git clone <repo-url>
cd avvVento_collection
cp .env.example .env
# Editar .env con valores reales de producción
nano .env
docker compose up -d --build
```

### 12.4 Configuración de Caddy
- Bloque exacto a copiar en `/etc/caddy/Caddyfile`
- Comando `sudo systemctl reload caddy`

### 12.5 Migración de datos históricos
- Cómo colocar el CSV en `old-data/`
- Comando para ejecutar el script de migración
- Comandos de verificación

### 12.6 Gestión de usuarios y equipos
- El primer usuario admin se crea automáticamente al arrancar (credenciales en `.env`)
- Desde la app: Dashboard → Gestión → crear equipos, crear cobradores, asignar contraseñas
- Nota: cambiar la contraseña por defecto del admin

### 12.7 Backups
- Hacer ejecutable el script: `chmod +x backup_avv.sh`
- Configurar cron: `crontab -e` → añadir línea
- Cómo restaurar un backup
- Dónde se guardan los backups

### 12.8 Estructura del proyecto
- Diagrama de carpetas (copia de la sección 2)

### 12.9 Desarrollo local
- `docker compose up -d --build` para rebuild
- Acceder a la API docs: `http://localhost:8002/docs`
- Acceder al frontend: `http://localhost:3002`
- Acceder a la BD: `psql -h localhost -p 5433 -U avv_user -d avv_ventorrillo`

### 12.10 Puertos utilizados

| Componente | Puerto | Notas |
|------------|--------|-------|
| Backend (FastAPI) | 8002 | Solo 127.0.0.1, Caddy proxifica |
| Frontend (Nginx) | 3002 | Solo 127.0.0.1, Caddy proxifica |
| PostgreSQL | 5433 | Solo 127.0.0.1, para depuración |

### 12.11 ⚠️ Cambio de dominio

> [!IMPORTANT]
> Si en el futuro se cambia el dominio de `avv.eingel.me` a otro, hay que modificar **exactamente** estos puntos:

1. **DNS**: Crear registro A del nuevo dominio apuntando a la IP del servidor
2. **Caddyfile** (`/etc/caddy/Caddyfile`): Cambiar `avv.eingel.me` por el nuevo dominio en el bloque de la app. Ejecutar `sudo systemctl reload caddy`.
3. **Frontend CORS** (si se configura explícitamente): Actualizar `VITE_API_BASE_URL` en el build del frontend si usa URL absoluta. **Actualmente no es necesario** porque el frontend usa rutas relativas (`/api/...`).
4. **Backend CORS** (`app/main.py`): Si `CORS_ORIGINS` incluye el dominio de forma explícita, actualizar la variable de entorno o el código.
5. **Rebuild del frontend** (solo si se cambió alguna variable de build):
   ```bash
   docker compose up -d --build frontend
   ```
6. **Certificado TLS**: Caddy lo gestiona automáticamente para el nuevo dominio; no requiere intervención.

**Resumen**: En el caso más simple (sin URLs absolutas en el frontend), solo hay que cambiar la línea del Caddyfile y el registro DNS.

### 12.12 Troubleshooting
- "No puedo conectar a la BD desde el host" → `psql -h localhost -p 5433 ...`
- "Caddy da error 502" → verificar que los contenedores están corriendo con `docker compose ps`
- "Error de certificado TLS" → verificar que el DNS ya ha propagado con `dig avv.eingel.me`
- "Login no funciona" → verificar que el admin por defecto se creó: mirar logs con `docker compose logs backend`

### 12.13 Licencia
- Definir según preferencia (o "Uso interno AVV Ventorrillo")

---

## 13. Cronograma detallado (28/08 → 01/09/2026)

> [!WARNING]
> El margen es de ~4 días. El cronograma prioriza lo imprescindible para operar el día 1. El dashboard elaborado se itera después del lanzamiento.

### Día 1 (28/08) — Infraestructura + modelo de datos + auth

- [ ] Crear estructura de carpetas completa del proyecto
- [ ] Crear `docker-compose.yml`, `.env`, `.env.example`, `.gitignore` actualizado
- [ ] Crear `backend/Dockerfile`, `requirements.txt`
- [ ] Configurar FastAPI con CORS, lifespan, config desde env
- [ ] Crear modelos SQLAlchemy (`models.py`) y configurar Alembic
- [ ] Generar migración inicial y verificar que el esquema se crea correctamente
- [ ] Crear `frontend/Dockerfile`, `nginx.conf`, scaffolding Vue 3 + Vite + Pinia + Vue Router
- [ ] Levantar `docker compose up -d` y verificar los 3 contenedores corriendo
- [ ] Implementar módulo de autenticación (`auth.py`): JWT + bcrypt
- [ ] Endpoints de auth: `POST /auth/login`, `POST /auth/cambiar-equipo`, `GET /auth/me`
- [ ] Crear usuario admin por defecto al arrancar (si no existe, contraseña desde env)
- [ ] Endpoints CRUD de equipos (`equipos_router.py`): GET, POST, PATCH, DELETE (soft)
- [ ] Endpoints CRUD de usuarios (`usuarios_router.py`): GET, POST, PATCH, DELETE (soft)
- [ ] Script de migración de datos (`migrar_sheets.py`) con toda la lógica de la sección 9
- [ ] Ejecutar migración y verificar datos en la BD
- [ ] Añadir bloque `avv.eingel.me` al Caddyfile del host → `sudo systemctl reload caddy`
- [ ] *(El usuario crea el registro DNS A para avv.eingel.me)*

### Día 2 (29/08) — Núcleo funcional: visitas y aportaciones

- [ ] Endpoint `GET /calles?q=` con búsqueda trigram
- [ ] Endpoint `POST /calles` (admin only)
- [ ] Endpoints `GET /viviendas?calle_id=&portal=&piso=&puerta=` y `POST /viviendas`
- [ ] Endpoint `GET /viviendas/{id}/historico`
- [ ] Endpoint `POST /visitas` (con aportación anidada atómica)
- [ ] Endpoint `POST /aportaciones` (aportación directa en local)
- [ ] Endpoints `PATCH/DELETE` para visitas y aportaciones
- [ ] Endpoint `GET /aportaciones?fecha=&equipo_id=` (listado del día)
- [ ] Frontend: pantalla de Login funcional (con selector de equipo)
- [ ] Frontend: componente BuscadorCalle (autocompletado con debounce)
- [ ] Frontend: componente SelectorVivienda (portal + piso + puerta)
- [ ] Frontend: componente HistoricoVivienda (línea compacta + popup)
- [ ] Frontend: pantalla Registro Rápido completa
- [ ] Frontend: navegación inferior (NavBar)
- [ ] Frontend: configurar API client (Axios + interceptor JWT)

### Día 3 (30/08) — Pantallas restantes + reportes + gestión admin

- [ ] Frontend: pantalla Aportación en el Local
- [ ] Frontend: pantalla Listado del Día (con edición/borrado inline)
- [ ] Endpoint `GET /reportes/diario?fecha=`
- [ ] Endpoint `GET /reportes/dashboard?anio=&calle_id=&equipo_id=`
- [ ] Endpoint `GET /reportes/exportar-excel?anio=`
- [ ] Frontend: pantalla Dashboard Admin (filtros + tarjetas resumen + tabla + exportar Excel)
- [ ] Frontend: componente GestionEquipos (crear, activar/desactivar, renombrar)
- [ ] Frontend: componente GestionUsuarios (alta, baja, reset contraseña)
- [ ] Frontend: componente GestionCalles (crear calle nueva)

### Día 4 (31/08) — Endurecimiento, pruebas y despliegue

- [ ] Pruebas manuales de los 5 flujos: aporta, no_abre, no_aporta, reintentar, pasará_por_local
- [ ] Prueba del flujo "aportación sin domicilio" (nombre_persona)
- [ ] Prueba del flujo "aportación en local" con y sin vivienda
- [ ] Prueba de la gestión admin: crear equipo, crear cobrador, desactivar, reactivar
- [ ] Prueba de concurrencia: 2 usuarios simultáneos desde 2 móviles
- [ ] Configurar backup automático (`chmod +x backup_avv.sh` + cron)
- [ ] Verificar que backup se genera y se puede restaurar
- [ ] Crear usuarios y equipos reales para los cobradores (desde la app, panel admin)
- [ ] Entregar credenciales a los cobradores
- [ ] Completar README.md con todas las secciones de la sección 12
- [ ] Prueba final end-to-end en producción (`https://avv.eingel.me`)

### 01/09 — Lanzamiento

- Acompañamiento primer día de campaña
- Soporte reactivo a bugs de uso real
- El dashboard con gráficos avanzados y el popup multianual elaborado se iteran esta primera semana

---

## 14. Fuera del MVP (se añade después del lanzamiento)

- Gráficos de evolución multianual más elaborados en el dashboard
- Pop-up detallado de histórico multianual (MVP muestra línea compacta + tabla simple en modal)
- PWA instalable con service worker + icono de pantalla de inicio
- Filtros avanzados de dashboard por rango de fechas personalizado
- Notificaciones de resumen al final del día por equipo

---

## Verification Plan

### Automated Tests
```bash
# Verificar que los 3 contenedores están corriendo
docker compose ps

# Verificar que la BD tiene el esquema correcto
docker compose exec db psql -U avv_user -d avv_ventorrillo -c "\dt"

# Verificar datos migrados
docker compose exec db psql -U avv_user -d avv_ventorrillo -c \
  "SELECT anio_campania, COUNT(*), SUM(importe) FROM aportaciones GROUP BY anio_campania;"

# Verificar que el backend responde
curl -s http://localhost:8002/docs | head -5

# Verificar que el frontend sirve la SPA
curl -s http://localhost:3002/ | head -5

# Verificar que Caddy proxifica correctamente (tras DNS)
curl -s https://avv.eingel.me/ | head -5
curl -s https://avv.eingel.me/api/calles | head -5
```

### Manual Verification
- Login desde un móvil (Android + iOS) via `https://avv.eingel.me`
- Flujo completo de registro rápido (calle → vivienda → visita → aportación)
- Crear equipo y cobrador desde panel admin
- Verificar exportación a Excel
- Verificar backup y restauración
