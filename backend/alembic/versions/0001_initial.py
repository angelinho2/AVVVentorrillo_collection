"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extensión trigram para autocompletado de calles
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Enums
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

    # Tabla usuarios
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre_usuario", sa.String(50), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("es_admin", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("creado_en", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )

    # Tabla equipos
    op.create_table(
        "equipos",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(50), unique=True, nullable=False),
        sa.Column("activo", sa.Boolean, nullable=False, server_default="true"),
    )

    # Tabla calles
    op.create_table(
        "calles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("nombre", sa.String(150), unique=True, nullable=False),
        sa.Column("creado_por", sa.Integer, sa.ForeignKey("usuarios.id")),
        sa.Column("creado_en", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.execute(
        "CREATE INDEX idx_calles_nombre_trgm ON calles USING gin (nombre gin_trgm_ops)"
    )

    # Tabla viviendas
    op.create_table(
        "viviendas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("calle_id", sa.Integer, sa.ForeignKey("calles.id"), nullable=False),
        sa.Column("portal", sa.String(10), nullable=False),
        sa.Column("piso", sa.String(5)),
        sa.Column("puerta", sa.String(20)),
        sa.Column("nombre", sa.String(150)),
        sa.Column("creado_en", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("calle_id", "portal", "piso", "puerta", name="uq_vivienda"),
    )
    op.create_index("idx_viviendas_calle", "viviendas", ["calle_id"])

    # Tabla visitas
    op.create_table(
        "visitas",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vivienda_id", sa.Integer, sa.ForeignKey("viviendas.id"), nullable=False),
        sa.Column("equipo_id", sa.Integer, sa.ForeignKey("equipos.id"), nullable=False),
        sa.Column("registrado_por", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("resultado", sa.Enum("aporta", "no_abre", "no_aporta", "reintentar",
                                       "pasara_por_local", name="resultado_visita"), nullable=False),
        sa.Column("observaciones", sa.Text),
        sa.Column("creado_en", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_visitas_vivienda", "visitas", ["vivienda_id"])
    op.create_index("idx_visitas_fecha", "visitas", ["fecha"])
    op.create_index("idx_visitas_equipo_fecha", "visitas", ["equipo_id", "fecha"])

    # Tabla aportaciones
    op.create_table(
        "aportaciones",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vivienda_id", sa.Integer, sa.ForeignKey("viviendas.id")),
        sa.Column("nombre_persona", sa.String(150)),
        sa.Column("visita_id", sa.Integer, sa.ForeignKey("visitas.id")),
        sa.Column("origen", sa.Enum("puerta", "local", name="origen_aportacion"), nullable=False),
        sa.Column("equipo_id", sa.Integer, sa.ForeignKey("equipos.id"), nullable=False),
        sa.Column("registrado_por", sa.Integer, sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("importe", sa.Numeric(8, 2), nullable=False),
        sa.Column("forma_pago", sa.Enum("efectivo", "bizum", name="forma_pago"), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False, server_default=sa.text("CURRENT_DATE")),
        sa.Column("anio_campania", sa.Integer, nullable=False),
        sa.Column("observaciones", sa.Text),
        sa.Column("creado_en", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.CheckConstraint(
            "vivienda_id IS NOT NULL OR nombre_persona IS NOT NULL",
            name="chk_vivienda_o_persona"
        ),
    )
    op.create_index("idx_aportaciones_vivienda_anio", "aportaciones", ["vivienda_id", "anio_campania"])
    op.create_index("idx_aportaciones_fecha", "aportaciones", ["fecha"])
    op.create_index("idx_aportaciones_equipo_fecha", "aportaciones", ["equipo_id", "fecha"])


def downgrade() -> None:
    op.drop_table("aportaciones")
    op.drop_table("visitas")
    op.drop_table("viviendas")
    op.drop_table("calles")
    op.drop_table("equipos")
    op.drop_table("usuarios")
    op.execute("DROP TYPE IF EXISTS resultado_visita")
    op.execute("DROP TYPE IF EXISTS origen_aportacion")
    op.execute("DROP TYPE IF EXISTS forma_pago")
