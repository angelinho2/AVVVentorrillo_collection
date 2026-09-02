from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional

from app.database import get_db
from app.models import Usuario, Vivienda, Aportacion
from app.schemas import ViviendaCreate, ViviendaOut, HistoricoAnio
from app.auth import get_current_user

router = APIRouter()


@router.get("", response_model=list[ViviendaOut])
async def buscar_viviendas(
    calle_id: Optional[int] = None,
    portal: Optional[str] = None,
    piso: Optional[str] = None,
    puerta: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = select(Vivienda).options(selectinload(Vivienda.calle))
    if calle_id:
        q = q.where(Vivienda.calle_id == calle_id)
    if portal:
        q = q.where(Vivienda.portal == portal)
    if piso is not None:
        q = q.where(Vivienda.piso == piso)
    if puerta:
        q = q.where(Vivienda.puerta == puerta)
    result = await db.execute(q.limit(50))
    return result.scalars().all()


@router.post("", response_model=ViviendaOut, status_code=201)
async def crear_vivienda(
    data: ViviendaCreate,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    # Comprobar si ya existe
    existing = await db.execute(
        select(Vivienda)
        .options(selectinload(Vivienda.calle))
        .where(
            Vivienda.calle_id == data.calle_id,
            Vivienda.portal == data.portal,
            Vivienda.piso == data.piso,
            Vivienda.puerta == data.puerta,
        )
    )
    found = existing.scalar_one_or_none()
    if found:
        return found

    vivienda = Vivienda(**data.model_dump())
    db.add(vivienda)
    await db.commit()
    await db.refresh(vivienda)
    # Cargar relación calle
    await db.refresh(vivienda, ["calle"])
    return vivienda


@router.get("/{vivienda_id}/historico", response_model=list[HistoricoAnio])
async def historico_vivienda(
    vivienda_id: int,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    from app.models import Visita
    
    res_ap = await db.execute(
        select(Aportacion)
        .where(Aportacion.vivienda_id == vivienda_id)
        .order_by(Aportacion.anio_campania.desc(), Aportacion.fecha.desc())
    )
    aportaciones = res_ap.scalars().all()
    
    res_vis = await db.execute(
        select(Visita)
        .where(Visita.vivienda_id == vivienda_id, Visita.resultado != "aporta")
        .order_by(Visita.fecha.desc())
    )
    visitas = res_vis.scalars().all()
    
    agrupado = {}
    
    def init_anio(anio):
        if anio not in agrupado:
            agrupado[anio] = {
                "anio_campania": anio,
                "total": 0.0,
                "num_aportaciones": 0,
                "observaciones": []
            }

    for ap in aportaciones:
        anio = ap.anio_campania
        init_anio(anio)
        agrupado[anio]["total"] += float(ap.importe)
        agrupado[anio]["num_aportaciones"] += 1
        
        if ap.observaciones and str(ap.observaciones).strip():
            agrupado[anio]["observaciones"].append({
                "fecha": ap.fecha,
                "texto": ap.observaciones.strip()
            })
            
    for vis in visitas:
        anio = vis.fecha.year
        init_anio(anio)
        
        texto_obs = f"[{vis.resultado.value.replace('_', ' ').capitalize()}]"
        if vis.observaciones and str(vis.observaciones).strip():
            texto_obs += f" - {str(vis.observaciones).strip()}"
            
        agrupado[anio]["observaciones"].append({
            "fecha": vis.fecha,
            "texto": texto_obs
        })
            
    for val in agrupado.values():
        val["observaciones"].sort(key=lambda x: x["fecha"], reverse=True)
            
    return sorted(list(agrupado.values()), key=lambda x: x["anio_campania"], reverse=True)
