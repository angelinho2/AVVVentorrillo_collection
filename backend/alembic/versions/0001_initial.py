"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-28
"""
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute("""
        DO $$ BEGIN
            CREATE TYPE resultado_visita AS ENUM (
                'aporta', 'no_abre', 'no_aporta', 'reintentar', 'pasara_por_local'
            );
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE origen_aportacion AS ENUM ('puerta', 'local');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE forma_pago AS ENUM ('efectivo', 'bizum');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre_usuario VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            es_admin BOOLEAN NOT NULL DEFAULT FALSE,
            activo BOOLEAN NOT NULL DEFAULT TRUE,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(50) UNIQUE NOT NULL,
            activo BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS calles (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(150) UNIQUE NOT NULL,
            creado_por INTEGER REFERENCES usuarios(id),
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_calles_nombre_trgm
            ON calles USING gin (nombre gin_trgm_ops)
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS viviendas (
            id SERIAL PRIMARY KEY,
            calle_id INTEGER NOT NULL REFERENCES calles(id),
            portal VARCHAR(10) NOT NULL,
            piso VARCHAR(5),
            puerta VARCHAR(20),
            nombre VARCHAR(150),
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_vivienda UNIQUE (calle_id, portal, piso, puerta)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_viviendas_calle ON viviendas(calle_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS visitas (
            id SERIAL PRIMARY KEY,
            vivienda_id INTEGER NOT NULL REFERENCES viviendas(id),
            equipo_id INTEGER NOT NULL REFERENCES equipos(id),
            registrado_por INTEGER NOT NULL REFERENCES usuarios(id),
            fecha DATE NOT NULL DEFAULT CURRENT_DATE,
            resultado resultado_visita NOT NULL,
            observaciones TEXT,
            creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_visitas_vivienda ON visitas(vivienda_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_visitas_fecha ON visitas(fecha)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_visitas_equipo_fecha ON visitas(equipo_id, fecha)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS aportaciones (
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
            CONSTRAINT chk_vivienda_o_persona
                CHECK (vivienda_id IS NOT NULL OR nombre_persona IS NOT NULL)
        )
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_aportaciones_vivienda_anio
            ON aportaciones(vivienda_id, anio_campania)
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_aportaciones_fecha ON aportaciones(fecha)")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_aportaciones_equipo_fecha
            ON aportaciones(equipo_id, fecha)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS aportaciones")
    op.execute("DROP TABLE IF EXISTS visitas")
    op.execute("DROP TABLE IF EXISTS viviendas")
    op.execute("DROP TABLE IF EXISTS calles")
    op.execute("DROP TABLE IF EXISTS equipos")
    op.execute("DROP TABLE IF EXISTS usuarios")
    op.execute("DROP TYPE IF EXISTS resultado_visita")
    op.execute("DROP TYPE IF EXISTS origen_aportacion")
    op.execute("DROP TYPE IF EXISTS forma_pago")
