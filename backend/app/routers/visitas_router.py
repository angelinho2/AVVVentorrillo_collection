from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt

from app.database import get_db
from app.models import Usuario, Visita, Aportacion, OrigenAportacion
from app.schemas import VisitaCreate, VisitaPatch, VisitaOut
from app.auth import get_current_user
from app.config import settings

router = APIRouter()


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
    await db.refresh(visita)
    # Cargar relación aportacion si existe
    if visita.aportacion:
        await db.refresh(visita, ["aportacion"])
    return visita


@router.patch("/{visita_id}", response_model=VisitaOut)
async def editar_visita(
    visita_id: int,
    data: VisitaPatch,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    result = await db.execute(select(Visita).where(Visita.id == visita_id))
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
