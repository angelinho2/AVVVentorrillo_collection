from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Usuario
from app.auth import hash_password
from app.config import settings

from app.routers.auth_router import router as auth_router
from app.routers.calles_router import router as calles_router
from app.routers.viviendas_router import router as viviendas_router
from app.routers.visitas_router import router as visitas_router
from app.routers.aportaciones_router import router as aportaciones_router
from app.routers.reportes_router import router as reportes_router
from app.routers.usuarios_router import router as usuarios_router
from app.routers.equipos_router import router as equipos_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear usuario admin por defecto si no existe
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Usuario).where(Usuario.nombre_usuario == "admin")
        )
        if not result.scalar_one_or_none():
            admin = Usuario(
                nombre_usuario="admin",
                password_hash=hash_password(settings.admin_default_password),
                es_admin=True,
                activo=True,
            )
            session.add(admin)
            await session.commit()
    yield


app = FastAPI(
    title="API Contribuciones AVV Ventorrillo",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://avv.eingel.me", "http://localhost:3002", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(calles_router, prefix="/calles", tags=["calles"])
app.include_router(viviendas_router, prefix="/viviendas", tags=["viviendas"])
app.include_router(visitas_router, prefix="/visitas", tags=["visitas"])
app.include_router(aportaciones_router, prefix="/aportaciones", tags=["aportaciones"])
app.include_router(reportes_router, prefix="/reportes", tags=["reportes"])
app.include_router(usuarios_router, prefix="/usuarios", tags=["usuarios"])
app.include_router(equipos_router, prefix="/equipos", tags=["equipos"])


@app.get("/health")
async def health():
    return {"status": "ok"}
