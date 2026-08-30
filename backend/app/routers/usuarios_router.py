from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioPatch, UsuarioOut
from app.auth import get_current_admin, hash_password

router = APIRouter()


@router.get("", response_model=list[UsuarioOut])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    result = await db.execute(select(Usuario).order_by(Usuario.nombre_usuario))
    return result.scalars().all()


@router.post("", response_model=UsuarioOut, status_code=201)
async def crear_usuario(
    data: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    existing = await db.execute(
        select(Usuario).where(Usuario.nombre_usuario == data.nombre_usuario)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="El nombre de usuario ya existe")

    usuario = Usuario(
        nombre_usuario=data.nombre_usuario,
        password_hash=hash_password(data.password),
        es_admin=data.es_admin,
        activo=True,
    )
    db.add(usuario)
    await db.commit()
    await db.refresh(usuario)
    return usuario


@router.patch("/{usuario_id}", response_model=UsuarioOut)
async def editar_usuario(
    usuario_id: int,
    data: UsuarioPatch,
    db: AsyncSession = Depends(get_db),
    current_admin: Usuario = Depends(get_current_admin),
):
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Protección: un admin no puede desactivarse a sí mismo
    if usuario_id == current_admin.id and data.activo is False:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta")

    update_data = data.model_dump(exclude_none=True)
    if "password" in update_data:
        usuario.password_hash = hash_password(update_data.pop("password"))
    for field, value in update_data.items():
        setattr(usuario, field, value)

    await db.commit()
    await db.refresh(usuario)
    return usuario


@router.delete("/{usuario_id}", status_code=204)
async def dar_de_baja_usuario(
    usuario_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    result = await db.execute(select(Usuario).where(Usuario.id == usuario_id))
    usuario = result.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # Soft delete
    usuario.activo = False
    await db.commit()
