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
    from app.models import Vivienda, Calle, Visita, Equipo, Aportacion
    from sqlalchemy import extract
    
    # 1. Aportaciones
    qa = (
        select(Aportacion, Vivienda, Calle, Equipo, Visita.resultado)
        .outerjoin(Vivienda, Aportacion.vivienda_id == Vivienda.id)
        .outerjoin(Calle, Vivienda.calle_id == Calle.id)
        .join(Equipo, Aportacion.equipo_id == Equipo.id)
        .outerjoin(Visita, Aportacion.visita_id == Visita.id)
    )
    if anio:
        qa = qa.where(Aportacion.anio_campania == anio)
        
    # 2. Visitas sin aportación
    qv = (
        select(Visita, Vivienda, Calle, Equipo)
        .outerjoin(Vivienda, Visita.vivienda_id == Vivienda.id)
        .outerjoin(Calle, Vivienda.calle_id == Calle.id)
        .join(Equipo, Visita.equipo_id == Equipo.id)
        .where(Visita.resultado != "aporta")
    )
    if anio:
        qv = qv.where(extract('year', Visita.fecha) == anio)
        
    res_a = await db.execute(qa.order_by(Aportacion.creado_en.asc()))
    res_v = await db.execute(qv.order_by(Visita.creado_en.asc()))
    
    rows_a = res_a.all()
    rows_v = res_v.all()
    
    unified_rows = []
    for aportacion, vivienda, calle, equipo, res_visita in rows_a:
        unified_rows.append({
            "id": f"A-{aportacion.id}",
            "fecha": str(aportacion.fecha),
            "creado_en": aportacion.creado_en,
            "anio_campania": aportacion.anio_campania,
            "calle_nombre": calle.nombre if calle else "",
            "portal": vivienda.portal if vivienda else "",
            "piso": vivienda.piso if vivienda else "",
            "puerta": vivienda.puerta if vivienda else "",
            "nombre_persona": aportacion.nombre_persona or "",
            "origen": aportacion.origen.value,
            "equipo_nombre": equipo.nombre,
            "importe": float(aportacion.importe),
            "forma_pago": aportacion.forma_pago.value,
            "observaciones": aportacion.observaciones or "",
            "resultado_visita": res_visita.value if res_visita else ("local" if aportacion.origen.value == "local" else "aporta")
        })
        
    for visita, vivienda, calle, equipo in rows_v:
        unified_rows.append({
            "id": f"V-{visita.id}",
            "fecha": str(visita.fecha),
            "creado_en": visita.creado_en,
            "anio_campania": visita.fecha.year,
            "calle_nombre": calle.nombre if calle else "",
            "portal": vivienda.portal if vivienda else "",
            "piso": vivienda.piso if vivienda else "",
            "puerta": vivienda.puerta if vivienda else "",
            "nombre_persona": "",
            "origen": "puerta",
            "equipo_nombre": equipo.nombre,
            "importe": None,
            "forma_pago": "",
            "observaciones": visita.observaciones or "",
            "resultado_visita": visita.resultado.value
        })
        
    # Ordenar cronológicamente
    unified_rows.sort(key=lambda x: x["creado_en"] if x["creado_en"] else x["fecha"])

    excel_bytes = generar_excel(unified_rows, anio)
    nombre_archivo = f"aportaciones_{anio or 'todos'}.xlsx"
    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"},
    )
