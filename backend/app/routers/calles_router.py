from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional

from app.database import get_db
from app.models import Usuario, Calle
from app.schemas import CalleCreate, CalleOut
from app.auth import get_current_user, get_current_admin

router = APIRouter()


@router.get("", response_model=list[CalleOut])
async def buscar_calles(
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Autocompletado de calles por trigram (mín. 2 caracteres) o listado completo."""
    if q and len(q) >= 2:
        # Búsqueda por similaridad trigram
        result = await db.execute(
            select(Calle)
            .where(Calle.nombre.ilike(f"%{q}%"))
            .order_by(Calle.nombre)
            .limit(20)
        )
    else:
        result = await db.execute(select(Calle).order_by(Calle.nombre))
    return result.scalars().all()


@router.post("", response_model=CalleOut, status_code=201)
async def crear_calle(
    data: CalleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    # Comprobar si ya existe (case-insensitive)
    existing = await db.execute(
        select(Calle).where(func.lower(Calle.nombre) == data.nombre.strip().lower())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="La calle ya existe")

    calle = Calle(nombre=data.nombre.strip(), creado_por=current_admin.id)
    db.add(calle)
    await db.commit()
    await db.refresh(calle)
    return calle
