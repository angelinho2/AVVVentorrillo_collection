# 🏘️ App de Contribuciones Vecinales — AVV Ventorrillo

Aplicación web para gestionar las aportaciones económicas de la campaña de fiestas del barrio. Permite a los cobradores registrar visitas puerta a puerta y aportaciones en el local, y al administrador ver reportes, exportar a Excel y gestionar equipos y usuarios.

---

## Contenido

- [Requisitos previos](#requisitos-previos)
- [Inicio rápido](#inicio-rápido)
- [Configuración de Caddy](#configuración-de-caddy)
- [Migración de datos históricos](#migración-de-datos-históricos)
- [Gestión de usuarios y equipos](#gestión-de-usuarios-y-equipos)
- [Backups](#backups)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Desarrollo local](#desarrollo-local)
- [Puertos utilizados](#puertos-utilizados)
- [⚠️ Cambio de dominio](#️-cambio-de-dominio)
- [Troubleshooting](#troubleshooting)

---

## Requisitos previos

- Docker Engine ≥ 24.x
- Docker Compose v2 (plugin `docker compose`)
- Caddy ≥ 2.x ejecutándose como servicio systemd en el host (`systemctl status caddy`)
- Registro DNS tipo A para `avv.eingel.me` apuntando a la IP del servidor (`51.83.6.229`)

---

## Inicio rápido

```bash
git clone https://github.com/angelinho2/AVVVentorrillo_collection.git avvVento_collection
cd avvVento_collection

# Copiar plantilla de variables de entorno y rellenar con valores reales
cp .env.example .env
nano .env

# Construir y levantar los 3 contenedores (db, backend, frontend)
docker compose up -d --build

# Verificar que los 3 están corriendo
docker compose ps
```

Una vez arrancado, el backend crea automáticamente el usuario **admin** con la contraseña de `ADMIN_DEFAULT_PASSWORD` en `.env`. **Cambia esta contraseña desde el panel de admin tras el primer login.**

---

## Configuración de Caddy

Añadir el siguiente bloque al final de `/etc/caddy/Caddyfile` en el host, **sin tocar nada de lo existente**:

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

Luego recargar Caddy sin downtime:

```bash
sudo systemctl reload caddy
```

> **Nota**: Caddy gestionará el certificado TLS automáticamente una vez que el DNS haya propagado.

---

## Migración de datos históricos

El CSV con datos del año anterior está en `old-data/`. Para importarlos a la base de datos:

```bash
# Ejecutar el script de migración dentro del contenedor backend
docker compose exec backend python scripts/migrar_sheets.py
```

El script:
- Descarta filas con importe no monetario (`X`, `No`, `Lc`, `C`, etc.)
- Corrige años: `2026` → `2025` (error de teclado en la hoja original); `2024` y `2025` se mantienen
- Normaliza abreviaturas de puertas (`Dcha` → `Derecha`, `Izda` → `Izquierda`, etc.)
- Genera un informe en pantalla y un `old-data/errores_migracion.csv` con las filas problemáticas

**Verificar los datos importados:**

```bash
# Totales por año
docker compose exec db psql -U avv_user -d avv_ventorrillo -c \
  "SELECT anio_campania, COUNT(*), SUM(importe) FROM aportaciones GROUP BY anio_campania ORDER BY anio_campania;"

# Calles importadas
docker compose exec db psql -U avv_user -d avv_ventorrillo -c \
  "SELECT nombre FROM calles ORDER BY nombre;"

# Número de viviendas
docker compose exec db psql -U avv_user -d avv_ventorrillo -c \
  "SELECT COUNT(*) FROM viviendas;"
```

---

## Gestión de usuarios y equipos

1. Entra en `https://avv.eingel.me/login` con usuario `admin` y la contraseña de `.env`
2. Navega a **Admin → Equipos**: crea los equipos de cobro (ej: "Equipo A", "Equipo B")
3. Navega a **Admin → Cobradores**: da de alta cada cobrador con nombre de usuario y contraseña
4. Entrega las credenciales a cada cobrador para que haga login seleccionando su equipo

> Los equipos y usuarios desactivados no aparecen en los selectores pero se preservan sus datos históricos.

---

## Backups

### Configuración inicial

```bash
# Hacer ejecutable el script
chmod +x backup_avv.sh

# Añadir al cron del host (backup diario a las 03:00)
crontab -e
```

Añadir esta línea al crontab:
```
0 3 * * * /home/ubuntu/avvVento_collection/backup_avv.sh >> /var/log/avv_backup.log 2>&1
```

### Restaurar un backup

```bash
gunzip -c backups/avv_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose exec -T db psql -U avv_user -d avv_ventorrillo
```

Los backups se guardan en `backups/` y se eliminan automáticamente después de 30 días.

---

## Estructura del proyecto

```
avvVento_collection/
├── README.md
├── docker-compose.yml
├── .env.example                       ← plantilla de variables (copiar a .env)
├── .gitignore
├── backup_avv.sh                      ← script de backup con cron
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/versions/0001_initial.py
│   └── app/
│       ├── main.py                    ← FastAPI, CORS, lifespan
│       ├── config.py                  ← settings desde .env
│       ├── database.py                ← engine async, session
│       ├── models.py                  ← SQLAlchemy models
│       ├── schemas.py                 ← Pydantic schemas
│       ├── auth.py                    ← JWT + bcrypt
│       ├── routers/                   ← endpoints por recurso
│       └── utils/excel_export.py
│   └── scripts/migrar_sheets.py
│
├── frontend/
│   ├── Dockerfile                     ← multi-stage: node build → nginx
│   ├── nginx.conf
│   └── src/
│       ├── views/                     ← Login, RegistroRapido, Local, Dia, Dashboard
│       ├── components/                ← BuscadorCalle, SelectorVivienda, Historico, NavBar
│       ├── stores/auth.js             ← Pinia: JWT + equipo activo
│       └── api/client.js              ← Axios con interceptor JWT
│
├── old-data/                          ← CSV de datos históricos
└── backups/                           ← backups automáticos (en .gitignore)
```

---

## Desarrollo local

```bash
# Levantar todos los servicios
docker compose up -d --build

# Ver API docs interactiva
http://localhost:8002/docs

# Ver el frontend
http://localhost:3002

# Conectar a la BD directamente
psql -h localhost -p 5433 -U avv_user -d avv_ventorrillo

# Ver logs en tiempo real
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild solo el backend tras cambios de código
docker compose build --no-cache backend && docker compose up -d backend
```

---

## Puertos utilizados

| Componente | Puerto HOST | Notas |
|------------|-------------|-------|
| Backend (FastAPI) | **8002** | Solo `127.0.0.1` — Caddy proxifica |
| Frontend (Nginx) | **3002** | Solo `127.0.0.1` — Caddy proxifica |
| PostgreSQL | **5433** | Solo `127.0.0.1` — acceso local/debug |

> Estos puertos se eligieron para no conflictar con los servicios existentes en el servidor (8000, 8001, 3000, 3001, 5432).

---

## ⚠️ Cambio de dominio

Si en el futuro se cambia el dominio de `avv.eingel.me` a otro, hay que modificar **exactamente** estos puntos:

1. **DNS**: Crear registro A del nuevo dominio apuntando a `51.83.6.229` en el panel DNS
2. **Caddyfile** (`/etc/caddy/Caddyfile`): Cambiar `avv.eingel.me` por el nuevo dominio → `sudo systemctl reload caddy`
3. **Backend CORS** (`backend/app/main.py`): Actualizar la lista `allow_origins` con el nuevo dominio → rebuild del backend
4. **Rebuild del frontend** si procede:
   ```bash
   docker compose build --no-cache frontend && docker compose up -d frontend
   ```
5. **Certificado TLS**: Caddy lo gestiona automáticamente — no requiere intervención

**Resumen mínimo**: Cambiar la línea del Caddyfile + el registro DNS + la lista CORS en `main.py`.

---

## Troubleshooting

| Síntoma | Solución |
|---------|----------|
| `502 Bad Gateway` en Caddy | `docker compose ps` — verificar que los contenedores están `Up` |
| Backend en `Restarting` | `docker compose logs backend` para ver el error exacto |
| "No puedo conectar a la BD" | `psql -h localhost -p 5433 -U avv_user -d avv_ventorrillo` |
| Error de certificado TLS | Verificar que el DNS ya propagó: `dig avv.eingel.me` |
| "Login no funciona" | El admin se crea al arrancar — revisar `docker compose logs backend` |
| El CSV no importa | El fichero debe estar en `old-data/` con el nombre exacto |
| `alembic` no encuentra la BD | Verificar que el contenedor `db` está `healthy` antes del `backend` |