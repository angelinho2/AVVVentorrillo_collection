from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Usuario, Equipo
from app.schemas import EquipoCreate, EquipoPatch, EquipoOut
from app.auth import get_current_admin, get_current_user

router = APIRouter()


@router.get("", response_model=list[EquipoOut])
async def listar_equipos(
    solo_activos: bool = False,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = select(Equipo)
    if solo_activos:
        q = q.where(Equipo.activo == True)
    result = await db.execute(q.order_by(Equipo.nombre))
    return result.scalars().all()


@router.post("", response_model=EquipoOut, status_code=201)
async def crear_equipo(
    data: EquipoCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    existing = await db.execute(select(Equipo).where(Equipo.nombre == data.nombre))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="El equipo ya existe")

    equipo = Equipo(nombre=data.nombre, activo=True)
    db.add(equipo)
    await db.commit()
    await db.refresh(equipo)
    return equipo


@router.patch("/{equipo_id}", response_model=EquipoOut)
async def editar_equipo(
    equipo_id: int,
    data: EquipoPatch,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    result = await db.execute(select(Equipo).where(Equipo.id == equipo_id))
    equipo = result.scalar_one_or_none()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(equipo, field, value)

    await db.commit()
    await db.refresh(equipo)
    return equipo


@router.delete("/{equipo_id}", status_code=204)
async def desactivar_equipo(
    equipo_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    result = await db.execute(select(Equipo).where(Equipo.id == equipo_id))
    equipo = result.scalar_one_or_none()
    if not equipo:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    # Soft delete
    equipo.activo = False
    await db.commit()
