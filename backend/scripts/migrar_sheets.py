#!/usr/bin/env python3
"""
Script de migración: CSV de Google Sheets → PostgreSQL

Uso:
    docker compose exec backend python scripts/migrar_sheets.py

El CSV debe estar en /app/old-data/
"""

import csv
import os
import sys
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Añadir el directorio raíz del backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text

from app.config import settings
from app.models import Base, Usuario, Equipo, Calle, Vivienda, Aportacion, OrigenAportacion, FormaPago
from app.auth import hash_password

# ── Configuración ────────────────────────────────────────────────────────────

CSV_PATH = Path("/app/old-data/Copia de pagos_vecinos_v2.xlsx - Data.csv")
ERRORES_PATH = Path("/app/old-data/errores_migracion.csv")

USUARIO_SISTEMA = "sistema_migracion"
EQUIPO_DUMMY = "Campaña anterior"

# ── Mapa de normalización de puertas ────────────────────────────────────────

PUERTA_MAP = {
    # Derecha
    "dcha": "Derecha",
    "dcha.": "Derecha",
    "dcha,": "Derecha",
    # Izquierda
    "izq": "Izquierda",
    "izq.": "Izquierda",
    "izda": "Izquierda",
    "izda.": "Izquierda",
    # Centro-derecha
    "ctro dcha": "Centro-derecha",
    "ctro. dcha": "Centro-derecha",
    "ctro dcha.": "Centro-derecha",
    "ctro dcho": "Centro-derecha",
    "ctro. dcho": "Centro-derecha",
    "centro dcha": "Centro-derecha",
    "centro dcho": "Centro-derecha",
    # Centro-izquierda
    "ctro izq": "Centro-izquierda",
    "ctro. izq": "Centro-izquierda",
    "ctro izq.": "Centro-izquierda",
    "centro izq": "Centro-izquierda",
    "centro izda": "Centro-izquierda",
    # Centro
    "ctro": "Centro",
    "ctro.": "Centro",
    "centro": "Centro",
}

# Letras válidas como puerta (A-K)
LETRAS_VALIDAS = set("ABCDEFGHIJK")


def normalizar_puerta(valor: str) -> str:
    """Normaliza abreviaturas de puerta al valor canónico de la app."""
    v = valor.strip()
    lookup = v.lower().strip(".")
    if lookup in PUERTA_MAP:
        return PUERTA_MAP[lookup]
    # Letra única: asegurar mayúscula
    if len(v) == 1 and v.upper() in LETRAS_VALIDAS:
        return v.upper()
    # Si no reconocemos el valor, lo devolvemos tal cual (se registrará como error si es inválido)
    return v


def parsear_importe(valor: str) -> Decimal | None:
    """
    Intenta convertir el campo Importe a Decimal.
    Devuelve None si el valor no es monetario (X, No, Lc, etc.)
    """
    v = valor.strip().strip('"')
    if not v:
        return None
    # Reemplazar coma decimal por punto
    v = v.replace(",", ".")
    try:
        d = Decimal(v)
        if d <= 0:
            return None
        return d
    except InvalidOperation:
        return None


def corregir_anio(anio_str: str, fecha: datetime) -> int:
    """
    Aplica la regla de corrección de años:
    - 2026 → 2025 (error de teclado en la hoja original)
    - 2024 → 2024 (se mantiene)
    - 2025 → 2025 (se mantiene)
    """
    try:
        anio = int(anio_str)
    except ValueError:
        return fecha.year
    if anio == 2026:
        return 2025
    return anio


async def main():
    if not CSV_PATH.exists():
        print(f"ERROR: No se encuentra el CSV en {CSV_PATH}")
        sys.exit(1)

    engine = create_async_engine(settings.database_url, echo=False)
    AsyncSession = async_sessionmaker(engine, expire_on_commit=False)

    stats = {
        "total": 0,
        "importadas": 0,
        "descartadas_no_monetario": 0,
        "descartadas_error": 0,
        "calles_creadas": 0,
        "viviendas_creadas": 0,
    }
    errores = []

    async with AsyncSession() as session:
        # ── 1. Crear usuario sistema ────────────────────────────────────────
        res = await session.execute(
            select(Usuario).where(Usuario.nombre_usuario == USUARIO_SISTEMA)
        )
        usuario_sistema = res.scalar_one_or_none()
        if not usuario_sistema:
            usuario_sistema = Usuario(
                nombre_usuario=USUARIO_SISTEMA,
                password_hash=hash_password("no_se_usa_" + os.urandom(8).hex()),
                es_admin=False,
                activo=False,  # Inactivo: no puede loguearse
            )
            session.add(usuario_sistema)
            await session.flush()

        # ── 2. Crear equipo dummy ───────────────────────────────────────────
        res = await session.execute(
            select(Equipo).where(Equipo.nombre == EQUIPO_DUMMY)
        )
        equipo_dummy = res.scalar_one_or_none()
        if not equipo_dummy:
            equipo_dummy = Equipo(nombre=EQUIPO_DUMMY, activo=False)
            session.add(equipo_dummy)
            await session.flush()

        # ── 3. Leer CSV ─────────────────────────────────────────────────────
        with open(CSV_PATH, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        print(f"CSV leído: {len(rows)} filas")

        # Caché local de calles y viviendas para evitar múltiples queries
        calles_cache: dict[str, int] = {}  # nombre_normalizado → id
        viviendas_cache: dict[tuple, int] = {}  # (calle_id, portal, piso, puerta) → id

        for i, row in enumerate(rows, 1):
            stats["total"] += 1

            try:
                # Limpiar BOM en primera columna si existe
                id_original = row.get("ID") or row.get("\ufeffID", "")
                calle_raw = row.get("Calle", "").strip()
                portal = row.get("Portal", "").strip()
                puerta_raw = row.get("Puerta", "").strip()
                planta = row.get("Planta", "").strip()
                anio_raw = row.get("Año", row.get("A\u00f1o", "")).strip()
                importe_raw = row.get("Importe", "").strip()
                fecha_raw = row.get("FechaPago", "").strip()
                observaciones = row.get("Observaciones", "").strip()

                # ── Filtrar registros no monetarios ────────────────────────
                importe = parsear_importe(importe_raw)
                if importe is None:
                    stats["descartadas_no_monetario"] += 1
                    continue

                # ── Parsear fecha ───────────────────────────────────────────
                try:
                    fecha = datetime.strptime(fecha_raw, "%d/%m/%Y")
                except ValueError:
                    errores.append({"fila": i, "id": id_original, "motivo": f"Fecha inválida: {fecha_raw!r}"})
                    stats["descartadas_error"] += 1
                    continue

                # ── Corregir año ────────────────────────────────────────────
                anio_campania = corregir_anio(anio_raw, fecha)

                # ── Normalizar puerta ───────────────────────────────────────
                puerta = normalizar_puerta(puerta_raw)

                # ── Normalizar piso ─────────────────────────────────────────
                piso = planta.strip() if planta else None

                # ── Calle ───────────────────────────────────────────────────
                calle_norm = calle_raw.strip()
                if calle_norm not in calles_cache:
                    res = await session.execute(
                        select(Calle).where(Calle.nombre == calle_norm)
                    )
                    calle_obj = res.scalar_one_or_none()
                    if not calle_obj:
                        calle_obj = Calle(
                            nombre=calle_norm,
                            creado_por=usuario_sistema.id,
                        )
                        session.add(calle_obj)
                        await session.flush()
                        stats["calles_creadas"] += 1
                    calles_cache[calle_norm] = calle_obj.id
                calle_id = calles_cache[calle_norm]

                # ── Vivienda ────────────────────────────────────────────────
                viv_key = (calle_id, portal, piso, puerta)
                if viv_key not in viviendas_cache:
                    res = await session.execute(
                        select(Vivienda).where(
                            Vivienda.calle_id == calle_id,
                            Vivienda.portal == portal,
                            Vivienda.piso == piso,
                            Vivienda.puerta == puerta,
                        )
                    )
                    viv_obj = res.scalar_one_or_none()
                    if not viv_obj:
                        viv_obj = Vivienda(
                            calle_id=calle_id,
                            portal=portal,
                            piso=piso,
                            puerta=puerta,
                        )
                        session.add(viv_obj)
                        await session.flush()
                        stats["viviendas_creadas"] += 1
                    viviendas_cache[viv_key] = viv_obj.id
                vivienda_id = viviendas_cache[viv_key]

                # ── Aportación ──────────────────────────────────────────────
                aportacion = Aportacion(
                    vivienda_id=vivienda_id,
                    origen=OrigenAportacion.puerta,
                    equipo_id=equipo_dummy.id,
                    registrado_por=usuario_sistema.id,
                    importe=importe,
                    forma_pago=FormaPago.efectivo,
                    fecha=fecha.date(),
                    anio_campania=anio_campania,
                    observaciones=observaciones if observaciones else None,
                )
                session.add(aportacion)
                stats["importadas"] += 1

                # Commit cada 200 filas para no acumular demasiado en memoria
                if stats["importadas"] % 200 == 0:
                    await session.commit()
                    print(f"  → {stats['importadas']} aportaciones insertadas...")

            except Exception as e:
                errores.append({"fila": i, "id": row.get("ID", "?"), "motivo": str(e)})
                stats["descartadas_error"] += 1

        # Commit final
        await session.commit()

    # ── Guardar errores ─────────────────────────────────────────────────────
    if errores:
        with open(ERRORES_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["fila", "id", "motivo"])
            writer.writeheader()
            writer.writerows(errores)
        print(f"\n⚠️  {len(errores)} errores guardados en {ERRORES_PATH}")

    # ── Resumen ──────────────────────────────────────────────────────────────
    print("\n" + "="*50)
    print("RESUMEN DE MIGRACIÓN")
    print("="*50)
    print(f"  Total filas procesadas:      {stats['total']}")
    print(f"  Aportaciones importadas:     {stats['importadas']}")
    print(f"  Descartadas (no monetario):  {stats['descartadas_no_monetario']}")
    print(f"  Descartadas (error):         {stats['descartadas_error']}")
    print(f"  Calles creadas:              {stats['calles_creadas']}")
    print(f"  Viviendas creadas:           {stats['viviendas_creadas']}")
    print("="*50)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
