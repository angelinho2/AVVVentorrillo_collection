from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Usuario, Aportacion, Equipo, Visita
from app.auth import get_current_admin
from app.utils.excel_export import generar_excel

router = APIRouter()


@router.get("/diario")
async def reporte_diario(
    fecha: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    if fecha is None:
        fecha = date.today()

    # Total por equipo
    por_equipo = await db.execute(
        select(
            Equipo.nombre,
            func.count(Aportacion.id).label("num"),
            func.sum(Aportacion.importe).label("total"),
        )
        .join(Aportacion, Aportacion.equipo_id == Equipo.id)
        .where(Aportacion.fecha == fecha)
        .group_by(Equipo.id, Equipo.nombre)
        .order_by(Equipo.nombre)
    )

    # Total general
    total_gen = await db.execute(
        select(
            func.count(Aportacion.id).label("num"),
            func.sum(Aportacion.importe).label("total"),
        ).where(Aportacion.fecha == fecha)
    )
    totales = total_gen.one()

    return {
        "fecha": str(fecha),
        "por_equipo": [
            {"equipo": r.nombre, "num_aportaciones": r.num, "total": float(r.total or 0)}
            for r in por_equipo.all()
        ],
        "total_general": {
            "num_aportaciones": totales.num or 0,
            "total": float(totales.total or 0),
        },
    }


@router.get("/dashboard")
async def reporte_dashboard(
    anio: Optional[int] = None,
    calle_id: Optional[int] = None,
    equipo_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    q = select(
        Aportacion.anio_campania,
        func.count(Aportacion.id).label("num"),
        func.sum(Aportacion.importe).label("total"),
    )
    if anio:
        q = q.where(Aportacion.anio_campania == anio)
    if equipo_id:
        q = q.where(Aportacion.equipo_id == equipo_id)
    if calle_id:
        from app.models import Vivienda
        q = q.join(Vivienda, Aportacion.vivienda_id == Vivienda.id).where(Vivienda.calle_id == calle_id)

    q = q.group_by(Aportacion.anio_campania).order_by(Aportacion.anio_campania.desc())
    result = await db.execute(q)
    rows = result.all()

    return {
        "filtros": {"anio": anio, "calle_id": calle_id, "equipo_id": equipo_id},
        "por_anio": [
            {"anio": r.anio_campania, "num_aportaciones": r.num, "total": float(r.total or 0)}
            for r in rows
        ],
        "total": float(sum(r.total or 0 for r in rows)),
    }


@router.get("/exportar-excel")
async def exportar_excel(
    anio: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: Usuario = Depends(get_current_admin),
):
    from app.models import Vivienda, Calle
    q = (
        select(Aportacion, Vivienda, Calle, Equipo)
        .outerjoin(Vivienda, Aportacion.vivienda_id == Vivienda.id)
        .outerjoin(Calle, Vivienda.calle_id == Calle.id)
        .join(Equipo, Aportacion.equipo_id == Equipo.id)
    )
    if anio:
        q = q.where(Aportacion.anio_campania == anio)
    q = q.order_by(Aportacion.fecha, Aportacion.id)

    result = await db.execute(q)
    rows = result.all()

    excel_bytes = generar_excel(rows, anio)
    nombre_archivo = f"aportaciones_{anio or 'todos'}.xlsx"
    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )
