from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from jose import jwt

from app.database import get_db
from app.models import Usuario, Visita, Aportacion, OrigenAportacion, Vivienda
from app.schemas import VisitaCreate, VisitaPatch, VisitaOut
from app.auth import get_current_user
from app.config import settings

router = APIRouter()

from datetime import date
from typing import Optional
from app.models import ResultadoVisita, Calle

@router.get("", response_model=list[VisitaOut])
async def buscar_visitas(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    resultado: Optional[ResultadoVisita] = None,
    equipo_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = (
        select(Visita)
        .options(
            selectinload(Visita.aportacion).selectinload(Aportacion.vivienda).selectinload(Vivienda.calle),
            selectinload(Visita.vivienda).selectinload(Vivienda.calle)
        )
    )
    if fecha_inicio:
        q = q.where(Visita.fecha >= fecha_inicio)
    if fecha_fin:
        q = q.where(Visita.fecha <= fecha_fin)
    if resultado:
        q = q.where(Visita.resultado == resultado)
    if equipo_id:
        q = q.where(Visita.equipo_id == equipo_id)
        
    q = q.order_by(Visita.fecha.desc(), Visita.id.desc()).limit(limit).offset(offset)
    
    result = await db.execute(q)
    return result.scalars().all()


def _get_equipo_id_from_token(current_user: Usuario, token_equipo_id: int) -> int:
    return token_equipo_id


@router.post("", response_model=VisitaOut, status_code=201)
async def registrar_visita(
    data: VisitaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    visita = Visita(
        vivienda_id=data.vivienda_id,
        equipo_id=data.equipo_id,
        registrado_por=current_user.id,
        fecha=data.fecha,
        resultado=data.resultado,
        observaciones=data.observaciones,
    )
    db.add(visita)
    await db.flush()  # Para obtener visita.id antes del commit

    # Si resultado=aporta y viene aportación anidada → insertar en la misma transacción
    if data.resultado.value == "aporta" and data.aportacion:
        aportacion = Aportacion(
            vivienda_id=data.vivienda_id,
            visita_id=visita.id,
            origen=OrigenAportacion.puerta,
            equipo_id=data.equipo_id,
            registrado_por=current_user.id,
            importe=data.aportacion.importe,
            forma_pago=data.aportacion.forma_pago,
            fecha=data.fecha,
            anio_campania=data.fecha.year,
            observaciones=data.aportacion.observaciones,
        )
        db.add(aportacion)

    await db.commit()
    
    # Cargar la visita junto con la relación aportacion usando selectinload
    result = await db.execute(
        select(Visita)
        .options(
            selectinload(Visita.aportacion).selectinload(Aportacion.vivienda).selectinload(Vivienda.calle)
        )
        .where(Visita.id == visita.id)
    )
    return result.scalar_one()


@router.patch("/{visita_id}", response_model=VisitaOut)
async def editar_visita(
    visita_id: int,
    data: VisitaPatch,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(
        select(Visita)
        .options(
            selectinload(Visita.aportacion).selectinload(Aportacion.vivienda).selectinload(Vivienda.calle)
        )
        .where(Visita.id == visita_id)
    )
    visita = result.scalar_one_or_none()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(visita, field, value)

    await db.commit()
    await db.refresh(visita)
    return visita


@router.delete("/{visita_id}", status_code=204)
async def borrar_visita(
    visita_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Visita).where(Visita.id == visita_id))
    visita = result.scalar_one_or_none()
    if not visita:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    await db.delete(visita)
    await db.commit()
