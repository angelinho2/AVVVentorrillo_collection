# Documentación Técnica y Estructura del Proyecto: AVV Ventorrillo

Este documento centraliza todos los detalles de la infraestructura, base de datos, flujos de la aplicación y organización de los contenedores para facilitar la toma de decisiones.

## 1. Visión General del Proyecto
La aplicación es una PWA (Aplicación Web Progresiva) diseñada para gestionar la recaudación de cuotas anuales de los socios de la Asociación de Vecinos (AVV Ventorrillo). Facilita el trabajo de los **cobradores** (que van puerta a puerta o atienden en el local) y proporciona un control riguroso a los **administradores** mediante historiales diarios, reportes y exportaciones en Excel.

---

## 2. Infraestructura y Contenedores (Docker Compose)
El proyecto corre orquestado con Docker en un único servidor.
- **Dominio**: `avv.eingel.me` (servido a través de Caddy como proxy inverso en la máquina host).
- **Archivos Clave**: `/home/ubuntu/avvVento_collection/docker-compose.yml`

### Contenedores:
1. **`db` (PostgreSQL 16 Alpine)**
   - **Misión**: Almacenamiento persistente de datos.
   - **Volumen**: `avv_pgdata` (Mapeado a `/var/lib/postgresql/data` dentro del contenedor).
   - **Puertos**: Expone el puerto `5432` internamente y el `5433` al localhost del servidor (útil para que el host pueda hacer backups o depurar).
2. **`backend` (FastAPI Python)**
   - **Misión**: API RESTful asíncrona.
   - **Puertos**: Expone internamente el `8000` y está mapeado al `8002` del localhost. (Caddy intercepta las rutas `/api/*` y las envía al 8002).
3. **`frontend` (Vue 3 + Vite + Nginx)**
   - **Misión**: SPA (Single Page Application) ligera e instalable como app en móviles. Nginx sirve los estáticos.
   - **Puertos**: Expone el `80` internamente y se mapea al `3002` del localhost (Caddy intercepta el tráfico raíz `/` y lo manda aquí).

### Sistema de Backups
- **Script**: `/home/ubuntu/avvVento_collection/backup_avv.sh`
- **Funcionamiento**: Extrae un volcado comprimido (`pg_dump | gzip`) cada día a las 03:00 AM (vía `cron`).
- **Retención**: Guarda los archivos en la carpeta `backups/` y borra automáticamente los que tengan más de 30 días de antigüedad.

---

## 3. Base de Datos (Modelos y Tablas)
Esquema relacional estricto en PostgreSQL usando `SQLAlchemy` (asíncrono) y `Alembic` para migraciones de esquema. Todo está definido en `backend/app/models.py`.

### Tablas Principales
1. **`usuarios`**: Gestiona el inicio de sesión.
   - Campos: `id`, `nombre_usuario`, `password_hash`, `es_admin` (booleano), `activo` (para deshabilitarlos sin borrarlos), `creado_en`.
2. **`equipos`**: Agrupaciones de trabajo (ej. "Equipo 1", "Equipo 2"). Las aportaciones siempre van ligadas a un equipo para la contabilidad.
   - Campos: `id`, `nombre`, `activo`.
3. **`calles`**: Diccionario de vías o calles.
   - Campos: `id`, `nombre`, `creado_por`, `creado_en`.
4. **`viviendas`**: Representa un domicilio único real.
   - Campos: `id`, `calle_id`, `portal`, `piso`, `puerta`, `nombre`, `creado_en`.
   - **Restricción**: Es imposible que haya dos viviendas con la misma combinación exacta de Calle + Portal + Piso + Puerta.
5. **`visitas`**: Registro de un evento de cobro a una puerta.
   - Campos: `id`, `vivienda_id`, `equipo_id`, `registrado_por` (usuario), `fecha`, `resultado` (Enum: *aporta, no_abre, no_aporta, reintentar, pasara_por_local*), `observaciones`, `creado_en`.
6. **`aportaciones`**: El dinero recaudado. (El core de la contabilidad).
   - Campos: `id`, `vivienda_id` (opcional si es aportación libre del local), `nombre_persona` (opcional si es aportación libre del local), `visita_id` (ligada si el cobro fue en puerta), `origen` (*puerta* o *local*), `equipo_id`, `registrado_por`, `importe` (Numérico), `forma_pago` (*efectivo* o *bizum*), `fecha` (día contable), `anio_campania`, `observaciones`, `creado_en` (marca de tiempo real del registro en sistema).

---

## 4. Flujo de la App y Endpoints
### Flujo en el Frontend (`/frontend/src/`)
La app depende de `Pinia` para gestionar el estado (`auth.js` maneja el token JWT de sesión que caduca a las 6 horas).

- **`/login`**: Punto de entrada. Redirige según si es cobrador normal o admin.
- **`/` (Registro Rápido)**: 
  - La vista reina en calle. Un formulario vertical diseñado para teléfonos donde seleccionan Calle -> Vivienda -> Resultado. Si el resultado es "Aporta", despliega el campo para el importe. Automáticamente crea la `vivienda` si no existía, registra la `visita` y genera la `aportación` asociada.
- **`/mi-dia`**: 
  - Resumen rápido para que el cobrador compruebe en la calle cuánto dinero lleva en efectivo y bizum, y corrija (edite o borre) si anotó mal una casa.
- **`/local` (Aportación en el Local)**: 
  - Vista para recaudación física. Permite asociar la cuota a una `vivienda` concreta o simplemente a un `nombre de persona` libre (sin domicilio).
- **`/admin` (Dashboard del Administrador)**:
  - Sistema de pestañas: 
    - **Reportes**: Gráficos de recaudación diaria y anual. Incluye un botón para generar un archivo Excel en tiempo real.
    - **Historial**: Vista similar a "Mi Día" pero engloba las transacciones de *todos* los equipos ordenadas por días (con paginación). Permite editar y borrar cualquier registro.
    - **Equipos, Cobradores y Calles**: Interfaces CRUD (Crear, leer, actualizar, borrar) para gestionar los diccionarios base del sistema.

### Rutas del Backend (`/backend/app/routers/`)
- `/api/auth`: Provee el inicio de sesión y devuelve el JWT.
- `/api/usuarios`, `/api/equipos`, `/api/calles`, `/api/viviendas`: Rutas CRUD con validaciones estrictas.
- `/api/visitas` y `/api/aportaciones`: Rutas transaccionales donde se generan los reportes y registros de negocio. Contienen la lógica de filtros por fechas y paginación (`limit`/`offset`).
- `/api/reportes/exportar-excel`: Un endpoint especial que cruza varias tablas con JOINs (Aportacion, Vivienda, Calle, Equipo), formatea un objeto en memoria usando `openpyxl` y devuelve el Excel puro directamente al cliente.

## 5. Secretos y Variables Críticas
Configurables en el archivo `.env` del root:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Credenciales de acceso a la Base de Datos aislada.
- `SECRET_KEY`: Llave criptográfica empleada por FastAPI para firmar los tokens JWT (si se pierde, todos los usuarios son cerrados de sesión forzosamente).
- `ADMIN_DEFAULT_PASSWORD`: La clave que emplea el sistema para crear la cuenta de administrador maestro la primera vez que se inicializa la BD vacía.
