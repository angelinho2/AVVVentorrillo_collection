from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models import FormaPago, OrigenAportacion, ResultadoVisita


# ── Usuarios ─────────────────────────────────────────────────────────────────

class UsuarioBase(BaseModel):
    nombre_usuario: str
    es_admin: bool = False

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioPatch(BaseModel):
    nombre_usuario: Optional[str] = None
    password: Optional[str] = None
    es_admin: Optional[bool] = None
    activo: Optional[bool] = None

class UsuarioOut(UsuarioBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    activo: bool
    creado_en: datetime


# ── Equipos ──────────────────────────────────────────────────────────────────

class EquipoBase(BaseModel):
    nombre: str

class EquipoCreate(EquipoBase):
    pass

class EquipoPatch(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None

class EquipoOut(EquipoBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    activo: bool


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    nombre_usuario: str
    password: str
    equipo_id: Optional[int] = None  # Opcional para admins sin equipo asignado

class CambiarEquipoRequest(BaseModel):
    equipo_id: int

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
    equipo_id: Optional[int] = None


# ── Calles ───────────────────────────────────────────────────────────────────

class CalleBase(BaseModel):
    nombre: str

class CalleCreate(CalleBase):
    pass

class CalleOut(CalleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ── Viviendas ─────────────────────────────────────────────────────────────────

class ViviendaBase(BaseModel):
    calle_id: int
    portal: str
    piso: Optional[str] = None
    puerta: Optional[str] = None
    nombre: Optional[str] = None

class ViviendaCreate(ViviendaBase):
    pass

class ViviendaOut(ViviendaBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    calle: CalleOut

class HistoricoAnio(BaseModel):
    anio_campania: int
    total: float
    num_aportaciones: int


# ── Aportaciones ─────────────────────────────────────────────────────────────

class AportacionBase(BaseModel):
    vivienda_id: Optional[int] = None
    nombre_persona: Optional[str] = None
    origen: OrigenAportacion
    equipo_id: int
    importe: float
    forma_pago: FormaPago
    fecha: date
    anio_campania: int
    observaciones: Optional[str] = None

class AportacionCreate(AportacionBase):
    visita_id: Optional[int] = None

class AportacionPatch(BaseModel):
    importe: Optional[float] = None
    forma_pago: Optional[FormaPago] = None
    fecha: Optional[date] = None
    anio_campania: Optional[int] = None
    observaciones: Optional[str] = None
    equipo_id: Optional[int] = None

class AportacionOut(AportacionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    visita_id: Optional[int] = None
    registrado_por: int
    creado_en: datetime
    vivienda: Optional[ViviendaOut] = None


# ── Visitas ───────────────────────────────────────────────────────────────────

class AportacionAnidada(BaseModel):
    """Aportación enviada dentro del body de una visita cuando resultado=aporta."""
    importe: float
    forma_pago: FormaPago
    observaciones: Optional[str] = None

class VisitaCreate(BaseModel):
    vivienda_id: int
    equipo_id: int
    fecha: date
    resultado: ResultadoVisita
    observaciones: Optional[str] = None
    aportacion: Optional[AportacionAnidada] = None  # Solo si resultado == aporta

class VisitaPatch(BaseModel):
    fecha: Optional[date] = None
    resultado: Optional[ResultadoVisita] = None
    observaciones: Optional[str] = None
    equipo_id: Optional[int] = None

class VisitaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vivienda_id: int
    equipo_id: int
    registrado_por: int
    fecha: date
    resultado: ResultadoVisita
    observaciones: Optional[str] = None
    creado_en: datetime
    aportacion: Optional[AportacionOut] = None
