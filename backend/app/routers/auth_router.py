from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Usuario, Equipo
from app.schemas import LoginRequest, CambiarEquipoRequest, TokenOut, UsuarioOut
from app.auth import verify_password, create_access_token, get_current_user

router = APIRouter()


@router.post("/login", response_model=TokenOut)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Usuario).where(Usuario.nombre_usuario == data.nombre_usuario)
    )
    user = result.scalar_one_or_none()
    if not user or not user.activo or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    equipo_id = data.equipo_id

    if equipo_id is not None:
        # Verificar que el equipo existe y está activo
        eq_result = await db.execute(
            select(Equipo).where(Equipo.id == equipo_id, Equipo.activo == True)
        )
        equipo = eq_result.scalar_one_or_none()
        if not equipo:
            raise HTTPException(status_code=400, detail="Equipo no válido")
    elif not user.es_admin:
        # Los cobradores no admins DEBEN seleccionar equipo
        raise HTTPException(status_code=400, detail="Debes seleccionar un equipo")

    token = create_access_token({"sub": str(user.id), "equipo_id": equipo_id})
    return TokenOut(
        access_token=token,
        usuario=UsuarioOut.model_validate(user),
        equipo_id=equipo_id,
    )


@router.post("/cambiar-equipo", response_model=TokenOut)
async def cambiar_equipo(
    data: CambiarEquipoRequest,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    eq_result = await db.execute(
        select(Equipo).where(Equipo.id == data.equipo_id, Equipo.activo == True)
    )
    equipo = eq_result.scalar_one_or_none()
    if not equipo:
        raise HTTPException(status_code=400, detail="Equipo no válido")

    token = create_access_token({"sub": str(current_user.id), "equipo_id": data.equipo_id})
    return TokenOut(
        access_token=token,
        usuario=UsuarioOut.model_validate(current_user),
        equipo_id=data.equipo_id,
    )


@router.get("/me", response_model=UsuarioOut)
async def me(current_user: Usuario = Depends(get_current_user)):
    return UsuarioOut.model_validate(current_user)
