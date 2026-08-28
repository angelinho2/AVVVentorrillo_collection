import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, Enum, ForeignKey,
    Integer, Numeric, String, Text, TIMESTAMP, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class ResultadoVisita(str, enum.Enum):
    aporta = "aporta"
    no_abre = "no_abre"
    no_aporta = "no_aporta"
    reintentar = "reintentar"
    pasara_por_local = "pasara_por_local"


class OrigenAportacion(str, enum.Enum):
    puerta = "puerta"
    local = "local"


class FormaPago(str, enum.Enum):
    efectivo = "efectivo"
    bizum = "bizum"


# ── Modelos ──────────────────────────────────────────────────────────────────

class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre_usuario: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    es_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())


class Equipo(Base):
    __tablename__ = "equipos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Calle(Base):
    __tablename__ = "calles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    creado_por: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    viviendas: Mapped[list["Vivienda"]] = relationship("Vivienda", back_populates="calle")


class Vivienda(Base):
    __tablename__ = "viviendas"
    __table_args__ = (
        UniqueConstraint("calle_id", "portal", "piso", "puerta", name="uq_vivienda"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    calle_id: Mapped[int] = mapped_column(Integer, ForeignKey("calles.id"), nullable=False)
    portal: Mapped[str] = mapped_column(String(10), nullable=False)
    piso: Mapped[Optional[str]] = mapped_column(String(5))
    puerta: Mapped[Optional[str]] = mapped_column(String(20))
    nombre: Mapped[Optional[str]] = mapped_column(String(150))
    creado_en: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    calle: Mapped["Calle"] = relationship("Calle", back_populates="viviendas")
    visitas: Mapped[list["Visita"]] = relationship("Visita", back_populates="vivienda")
    aportaciones: Mapped[list["Aportacion"]] = relationship("Aportacion", back_populates="vivienda")


class Visita(Base):
    __tablename__ = "visitas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vivienda_id: Mapped[int] = mapped_column(Integer, ForeignKey("viviendas.id"), nullable=False)
    equipo_id: Mapped[int] = mapped_column(Integer, ForeignKey("equipos.id"), nullable=False)
    registrado_por: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    resultado: Mapped[ResultadoVisita] = mapped_column(Enum(ResultadoVisita), nullable=False)
    observaciones: Mapped[Optional[str]] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    vivienda: Mapped["Vivienda"] = relationship("Vivienda", back_populates="visitas")
    equipo: Mapped["Equipo"] = relationship("Equipo")
    registrado_por_usuario: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[registrado_por])
    aportacion: Mapped[Optional["Aportacion"]] = relationship("Aportacion", back_populates="visita", uselist=False)


class Aportacion(Base):
    __tablename__ = "aportaciones"
    __table_args__ = (
        CheckConstraint(
            "vivienda_id IS NOT NULL OR nombre_persona IS NOT NULL",
            name="chk_vivienda_o_persona"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vivienda_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("viviendas.id"))
    nombre_persona: Mapped[Optional[str]] = mapped_column(String(150))
    visita_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("visitas.id"))
    origen: Mapped[OrigenAportacion] = mapped_column(Enum(OrigenAportacion), nullable=False)
    equipo_id: Mapped[int] = mapped_column(Integer, ForeignKey("equipos.id"), nullable=False)
    registrado_por: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False)
    importe: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    forma_pago: Mapped[FormaPago] = mapped_column(Enum(FormaPago), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    anio_campania: Mapped[int] = mapped_column(Integer, nullable=False)
    observaciones: Mapped[Optional[str]] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    vivienda: Mapped[Optional["Vivienda"]] = relationship("Vivienda", back_populates="aportaciones")
    visita: Mapped[Optional["Visita"]] = relationship("Visita", back_populates="aportacion")
    equipo: Mapped["Equipo"] = relationship("Equipo")
    registrado_por_usuario: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[registrado_por])
