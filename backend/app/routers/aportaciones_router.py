from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Usuario, Aportacion, Vivienda, Visita
from app.schemas import AportacionCreate, AportacionPatch, AportacionOut
from app.auth import get_current_user

router = APIRouter()


@router.post("", response_model=AportacionOut, status_code=201)
async def crear_aportacion(
    data: AportacionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Validar que tiene vivienda o nombre_persona
    if not data.vivienda_id and not data.nombre_persona:
        raise HTTPException(status_code=400, detail="Debe indicar vivienda o nombre_persona")

    aportacion = Aportacion(
        **data.model_dump(),
        registrado_por=current_user.id,
    )
    db.add(aportacion)
    await db.commit()
    result = await db.execute(
        select(Aportacion)
        .options(selectinload(Aportacion.vivienda).selectinload(Vivienda.calle))
        .where(Aportacion.id == aportacion.id)
    )
    return result.scalar_one()


@router.get("", response_model=list[AportacionOut])
async def listar_aportaciones(
    fecha: Optional[date] = None,
    equipo_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = select(Aportacion).options(selectinload(Aportacion.vivienda).selectinload(Vivienda.calle))
    if fecha:
        q = q.where(Aportacion.fecha == fecha)
    if equipo_id:
        q = q.where(Aportacion.equipo_id == equipo_id)
    q = q.order_by(Aportacion.creado_en.desc())
    result = await db.execute(q)
    return result.scalars().all()


@router.patch("/{aportacion_id}", response_model=AportacionOut)
async def editar_aportacion(
    aportacion_id: int,
    data: AportacionPatch,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Aportacion).where(Aportacion.id == aportacion_id))
    aportacion = result.scalar_one_or_none()
    if not aportacion:
        raise HTTPException(status_code=404, detail="Aportación no encontrada")

    # Si se cambió la vivienda y está asociada a una visita, actualizar la visita también
    if "vivienda_id" in data.model_dump(exclude_none=True) and aportacion.visita_id:
        result_visita = await db.execute(select(Visita).where(Visita.id == aportacion.visita_id))
        visita = result_visita.scalar_one_or_none()
        if visita:
            visita.vivienda_id = data.vivienda_id

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(aportacion, field, value)

    await db.commit()
    
    result = await db.execute(
        select(Aportacion)
        .options(selectinload(Aportacion.vivienda).selectinload(Vivienda.calle))
        .where(Aportacion.id == aportacion_id)
    )
    aportacion = result.scalar_one()
    return aportacion


@router.delete("/{aportacion_id}", status_code=204)
async def borrar_aportacion(
    aportacion_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Aportacion).where(Aportacion.id == aportacion_id))
    aportacion = result.scalar_one_or_none()
    if not aportacion:
        raise HTTPException(status_code=404, detail="Aportación no encontrada")
    await db.delete(aportacion)
    await db.commit()
