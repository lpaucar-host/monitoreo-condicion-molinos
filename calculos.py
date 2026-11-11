from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np
import math

from config import (
    EXCEL_PATH, SHEETS_MEDICION, SHEET_EQUIPOS, SHEET_PUNTOS,
    EQUIPO_CORTO, ORDEN_EQUIPO, LIMITES
)


def _normalizar_codigo_punto(codigo) -> str:
    """Normaliza códigos de columnas sin perder la etiqueta visible original."""
    s = str(codigo).strip().replace(" ", "")
    return s.upper()


def _ajustar_diccionario_puntos(puntos: pd.DataFrame) -> pd.DataFrame:
    """
    Corrige el mapeo físico vigente y añade alias para la nueva nomenclatura
    de aceleración del Excel (nG = aceleración RMS en g, nGE = envolvente en gE).
    """
    puntos = puntos.copy()

    # Mapeo físico vigente informado por mantenimiento.
    punto_num = pd.to_numeric(puntos["Punto"], errors="coerce")
    puntos.loc[punto_num.eq(5), "Componente"] = "TRUNNION CARGA"
    puntos.loc[punto_num.eq(6), "Componente"] = "TRUNNION DESCARGA"

    # Tomar el componente base de cada punto a partir del propio diccionario.
    componentes = {}
    for n in sorted({int(x) for x in punto_num.dropna().tolist() if float(x).is_integer()}):
        q = puntos[pd.to_numeric(puntos["Punto"], errors="coerce").eq(n)]
        if not q.empty:
            componentes[n] = str(q["Componente"].dropna().iloc[0]) if q["Componente"].notna().any() else ""

    aliases = []
    for n, componente in componentes.items():
        aliases.append({
            "CodPunto": f"{n}g",
            "Componente": componente,
            "Punto": str(n),
            "Direccion": "Aceleracion RMS",
            "TipoVariable": "Vibracion-Aceleracion-RMS",
            "Unidad": "g",
            "Descripcion": "Aceleracion RMS global",
        })
        aliases.append({
            "CodPunto": f"{n}gE",
            "Componente": componente,
            "Punto": str(n),
            "Direccion": "Envolvente",
            "TipoVariable": "Vibracion-Aceleracion",
            "Unidad": "gE",
            "Descripcion": "Envolvente de aceleracion",
        })

    if aliases:
        base_cols = [c for c in puntos.columns if c in aliases[0]]
        alias_df = pd.DataFrame(aliases)
        for c in puntos.columns:
            if c not in alias_df.columns:
                alias_df[c] = np.nan
        alias_df = alias_df[puntos.columns]
        puntos = pd.concat([puntos, alias_df], ignore_index=True)

    puntos["CodPunto"] = puntos["CodPunto"].astype(str).str.strip()
    puntos["_CodigoNorm"] = puntos["CodPunto"].map(_normalizar_codigo_punto)

    # Si hubiera duplicados, priorizar la nomenclatura nueva g/gE.
    puntos["_PrioridadAlias"] = puntos["CodPunto"].astype(str).str.contains(r"gE?$", regex=True).astype(int)
    puntos = (
        puntos.sort_values(["_CodigoNorm", "_PrioridadAlias"], ascending=[True, False])
        .drop_duplicates("_CodigoNorm", keep="first")
        .drop(columns=["_PrioridadAlias"])
        .reset_index(drop=True)
    )
    return puntos

def _archivo_excel() -> Path:
    """Devuelve el Excel estándar; si fue renombrado, toma el primer xlsx de /data."""
    if EXCEL_PATH.exists():
        return EXCEL_PATH
    candidatos = sorted(EXCEL_PATH.parent.glob("*.xlsx"))
    if not candidatos:
        raise FileNotFoundError(
            f"No se encontró {EXCEL_PATH.name} dentro de {EXCEL_PATH.parent}"
        )
    return candidatos[0]

def clasificar_valor(tipo_variable: str, valor) -> str:
    """Clasifica un único valor usando los límites oficiales."""
    if pd.isna(valor):
        return "SIN DATO"
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "SIN DATO"

    regla = LIMITES.get(str(tipo_variable))
    if not regla:
        return "SIN DATO"

    cortes = regla["cortes"]
    estados = regla["estados"]

    if tipo_variable == "Temperatura":
        # ACEPTADO < 45; MODERADO 45–60; CRITICO > 60
        if v < cortes[0]:
            return estados[0]
        if v <= cortes[1]:
            return estados[1]
        return estados[2]

    # Vibración: el valor exacto del límite pertenece al nivel inferior.
    if v <= cortes[0]:
        return estados[0]
    if v <= cortes[1]:
        return estados[1]
    if v <= cortes[2]:
        return estados[2]
    return estados[3]

def cargar_dimensiones(excel_path: Path | None = None):
    archivo = excel_path or _archivo_excel()

    equipos = pd.read_excel(archivo, sheet_name=SHEET_EQUIPOS, engine="openpyxl")
    equipos = equipos[equipos["TAG"].astype(str).str.match(r"^MOL-", na=False)].copy()
    equipos["EquipoCorto"] = equipos["TAG"].map(EQUIPO_CORTO).fillna(equipos["Equipo"])
    equipos["OrdenEquipo"] = equipos["TAG"].map(ORDEN_EQUIPO).fillna(99).astype(int)

    puntos = pd.read_excel(archivo, sheet_name=SHEET_PUNTOS, engine="openpyxl")
    puntos = puntos[puntos["CodPunto"].notna()].copy()
    puntos["CodPunto"] = puntos["CodPunto"].astype(str).str.strip()
    puntos = _ajustar_diccionario_puntos(puntos)

    return equipos, puntos

def cargar_mediciones(excel_path: Path | None = None) -> pd.DataFrame:
    """Convierte las cinco hojas anchas en una única tabla larga y limpia."""
    archivo = excel_path or _archivo_excel()
    equipos, puntos = cargar_dimensiones(archivo)

    tag_por_hoja = dict(zip(equipos["Hoja"], equipos["TAG"]))
    codigos_validos = set(puntos["_CodigoNorm"].astype(str))

    partes = []
    for hoja in SHEETS_MEDICION:
        df = pd.read_excel(archivo, sheet_name=hoja, header=4, engine="openpyxl")
        if "Fecha" not in df.columns:
            continue

        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        df = df[df["Fecha"].notna()].copy()

        if df.empty:
            continue

        columnas_punto = [
            c for c in df.columns
            if _normalizar_codigo_punto(c) in codigos_validos
        ]
        base_cols = [c for c in ["Tecnico", "Fecha", "Observacion"] if c in df.columns]

        long = df[base_cols + columnas_punto].melt(
            id_vars=base_cols,
            value_vars=columnas_punto,
            var_name="ColumnaOrigen",
            value_name="Valor",
        )

        long["Valor"] = pd.to_numeric(long["Valor"], errors="coerce")
        long = long[long["Valor"].notna()].copy()
        long["_CodigoNorm"] = long["ColumnaOrigen"].map(_normalizar_codigo_punto)
        long["Hoja"] = hoja
        long["TAG"] = tag_por_hoja.get(hoja)

        partes.append(long)

    if not partes:
        return pd.DataFrame()

    mediciones = pd.concat(partes, ignore_index=True)
    mediciones = mediciones.merge(
        puntos[[
            "_CodigoNorm", "CodPunto", "Componente", "Punto", "Direccion",
            "TipoVariable", "Unidad", "Descripcion"
        ]],
        on="_CodigoNorm",
        how="left",
    )
    mediciones = mediciones.drop(columns=["_CodigoNorm"], errors="ignore")

    mediciones = mediciones.merge(
        equipos[[
            "TAG", "EquipoCorto", "Equipo", "Criticidad", "IC", "RPN",
            "N_Puntos", "OrdenEquipo"
        ]],
        on="TAG",
        how="left",
    )

    mediciones["Estado"] = [
        clasificar_valor(t, v)
        for t, v in zip(mediciones["TipoVariable"], mediciones["Valor"])
    ]

    mediciones["Fecha"] = pd.to_datetime(mediciones["Fecha"], errors="coerce")
    mediciones = mediciones.sort_values(
        ["OrdenEquipo", "Fecha", "CodPunto"],
        ascending=[True, False, True],
    ).reset_index(drop=True)

    return mediciones

def resumen_fuente(mediciones: pd.DataFrame) -> dict:
    if mediciones.empty:
        return {
            "fecha_min": None, "fecha_max": None, "equipos": 0,
            "rondas": 0, "valores": 0, "puntos_unicos": 0,
        }

    return {
        "fecha_min": mediciones["Fecha"].min(),
        "fecha_max": mediciones["Fecha"].max(),
        "equipos": int(mediciones["TAG"].nunique()),
        "rondas": int(mediciones[["TAG", "Fecha"]].drop_duplicates().shape[0]),
        "valores": int(len(mediciones)),
        "puntos_unicos": int(mediciones[["TAG", "CodPunto"]].drop_duplicates().shape[0]),
    }

def ultima_medicion_por_equipo(mediciones: pd.DataFrame) -> pd.DataFrame:
    if mediciones.empty:
        return pd.DataFrame()
    out = (
        mediciones.groupby(["OrdenEquipo", "EquipoCorto", "TAG"], as_index=False)["Fecha"]
        .max()
        .rename(columns={"Fecha": "UltimaMedicion"})
        .sort_values("OrdenEquipo")
    )
    return out

def tabla_prueba_limites() -> pd.DataFrame:
    """Casos de borde para validar manualmente que las reglas son correctas."""
    casos = [
        ("Vibracion-Velocidad", 0.00),
        ("Vibracion-Velocidad", 3.00),
        ("Vibracion-Velocidad", 3.01),
        ("Vibracion-Velocidad", 5.00),
        ("Vibracion-Velocidad", 5.01),
        ("Vibracion-Velocidad", 7.00),
        ("Vibracion-Velocidad", 7.01),
        ("Vibracion-Aceleracion", 0.75),
        ("Vibracion-Aceleracion", 0.76),
        ("Vibracion-Aceleracion", 1.00),
        ("Vibracion-Aceleracion", 1.01),
        ("Vibracion-Aceleracion", 3.00),
        ("Vibracion-Aceleracion", 3.01),
        ("Temperatura", 44.9),
        ("Temperatura", 45.0),
        ("Temperatura", 60.0),
        ("Temperatura", 60.1),
    ]
    filas = []
    for tipo, valor in casos:
        filas.append({
            "Variable": tipo,
            "Valor prueba": valor,
            "Unidad": LIMITES[tipo]["unidad"],
            "Estado esperado": clasificar_valor(tipo, valor),
        })
    return pd.DataFrame(filas)

SEVERIDAD = {
    "SIN DATO": -1,
    "NORMAL": 0, "ACEPTADO": 0,
    "TOLERABLE": 1, "MODERADO": 1,
    "ALERTA": 2,
    "PELIGRO": 3, "CRITICO": 3,
}

def estado_actual_por_punto(mediciones: pd.DataFrame) -> pd.DataFrame:
    """Última lectura válida de cada Equipo + Punto."""
    if mediciones.empty:
        return pd.DataFrame()
    df = mediciones.sort_values("Fecha").copy()
    ult = df.groupby(["TAG", "CodPunto"], as_index=False).tail(1).copy()
    ult["Severidad"] = ult["Estado"].map(SEVERIDAD).fillna(-1).astype(int)
    return ult.sort_values(
        ["OrdenEquipo", "Severidad", "CodPunto"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def _indice_condicion(tipo_variable: str, valor) -> float:
    """
    Índice auxiliar solo para desempatar puntos con la misma severidad.
    No reemplaza el Estado. Escala cada variable según sus propios límites,
    evitando comparar directamente °C con mm/s o gE.
    """
    if pd.isna(valor):
        return -1.0
    v = float(valor)
    if tipo_variable == "Vibracion-Velocidad":
        if v <= 3: return v / 3.0
        if v <= 5: return 1.0 + (v - 3.0) / 2.0
        if v <= 7: return 2.0 + (v - 5.0) / 2.0
        return 3.0 + min((v - 7.0) / 7.0, 1.0)
    if tipo_variable == "Vibracion-Aceleracion":
        if v <= 0.75: return v / 0.75
        if v <= 1.0: return 1.0 + (v - 0.75) / 0.25
        if v <= 3.0: return 2.0 + (v - 1.0) / 2.0
        return 3.0 + min((v - 3.0) / 3.0, 1.0)
    if tipo_variable == "Temperatura":
        if v < 45: return max(v, 0.0) / 45.0
        if v <= 60: return 1.0 + (v - 45.0) / 15.0
        return 3.0 + min((v - 60.0) / 30.0, 1.0)
    return float(v)


def estado_actual_por_equipo(mediciones: pd.DataFrame) -> pd.DataFrame:
    """
    Resume cada molino por su peor punto actual.
    Primero manda la severidad; si varios puntos comparten severidad,
    se elige el más comprometido respecto de los límites de SU variable.
    """
    ult = estado_actual_por_punto(mediciones)
    if ult.empty:
        return pd.DataFrame()

    ult = ult.copy()
    ult["IndiceCondicion"] = [
        _indice_condicion(t, v) for t, v in zip(ult["TipoVariable"], ult["Valor"])
    ]

    filas = []
    for tag, g in ult.groupby("TAG", sort=False):
        g = g.sort_values(
            ["Severidad", "IndiceCondicion", "Fecha"],
            ascending=[False, False, False]
        )
        dominante = g.iloc[0]
        fecha_equipo = g["Fecha"].max()
        puntos_atencion = int((g["Severidad"] >= 2).sum())
        filas.append({
            "TAG": tag,
            "EquipoCorto": dominante["EquipoCorto"],
            "OrdenEquipo": int(dominante["OrdenEquipo"]),
            "EstadoGeneral": dominante["Estado"],
            "Severidad": int(dominante["Severidad"]),
            "CodPuntoDominante": dominante["CodPunto"],
            "ComponenteDominante": dominante.get("Componente"),
            "TipoVariableDominante": dominante.get("TipoVariable"),
            "ValorDominante": dominante["Valor"],
            "UnidadDominante": dominante.get("Unidad"),
            "UltimaMedicion": fecha_equipo,
            "PuntosAtencion": puntos_atencion,
        })
    return pd.DataFrame(filas).sort_values("OrdenEquipo").reset_index(drop=True)


def tendencia_ultimas_6_velocidad(mediciones: pd.DataFrame) -> pd.DataFrame:
    """
    Tendencia adaptativa por Equipo + Punto de velocidad.

    El nombre de la función se conserva por compatibilidad con la interfaz,
    pero YA NO usa una ventana fija de 6 lecturas.

    Método:
    - Si existe un mantenimiento/reemplazo explícito del punto/componente,
      se limita al ciclo vigente posterior a ese evento.
    - Evalúa ventanas recientes de 6, 8, 10, 12, 15, 20, 25 y todo el ciclo.
    - Selecciona la ventana con mejor combinación de R², RMSE, backtest,
      estabilidad de pendiente, cantidad de datos y cobertura temporal.
    - Requiere al menos 6 lecturas para una tendencia validable.

    La salida mantiene Pendiente_mm_s_mes, R2 y N para no romper app.py.
    """
    vel = mediciones[mediciones["TipoVariable"].eq("Vibracion-Velocidad")].copy()
    if vel.empty:
        return pd.DataFrame()

    resultados = []
    for (tag, punto), g in vel.groupby(["TAG", "CodPunto"]):
        g = (
            g.sort_values("Fecha")
             .drop_duplicates(subset=["Fecha"], keep="last")
             .copy()
        )
        if len(g) < 6:
            continue

        ult_global = g.iloc[-1]
        equipo = ult_global["EquipoCorto"]
        fecha_mantenimiento = None
        ciclo_estructurado = False

        try:
            evento = evento_mantenimiento_relevante(mediciones, equipo, punto)
        except Exception:
            evento = None

        q = g.copy()
        if evento is not None:
            fecha_mantenimiento = pd.to_datetime(evento["fecha"])
            qciclo = q[pd.to_datetime(q["Fecha"]).ge(fecha_mantenimiento)].copy()
            # No mezclar ciclos. Si el ciclo nuevo aún es corto, se omite la
            # tendencia en vez de recurrir a datos anteriores al mantenimiento.
            if len(qciclo) < 6:
                continue
            q = qciclo
            ciclo_estructurado = True

        modelo = _seleccionar_modelo_adaptativo(q)
        if modelo is None:
            continue

        qm = modelo["q"]
        ult = q.iloc[-1]
        resultados.append({
            "TAG": tag,
            "EquipoCorto": ult["EquipoCorto"],
            "OrdenEquipo": int(ult["OrdenEquipo"]),
            "CodPunto": punto,
            "Componente": ult.get("Componente"),
            "UltimoValor": float(ult["Valor"]),
            "UltimaFecha": ult["Fecha"],
            "Pendiente_mm_s_mes": float(modelo["slope"] * 30.0),
            "R2": float(modelo["r2"]),
            "N": int(len(qm)),
            "N_Ciclo": int(len(q)),
            "RMSE": float(modelo["rmse"]),
            "MAE": float(modelo["mae"]),
            "Backtest_MAE": (
                float(modelo["back_mae"])
                if np.isfinite(modelo["back_mae"]) else np.nan
            ),
            "Estabilidad": float(modelo["estabilidad"]),
            "ScoreModelo": float(modelo["score"]),
            "CicloEstructurado": bool(ciclo_estructurado),
            "FechaMantenimiento": fecha_mantenimiento,
        })

    if not resultados:
        return pd.DataFrame()

    return (
        pd.DataFrame(resultados)
        .sort_values(
            ["Pendiente_mm_s_mes", "ScoreModelo", "R2"],
            ascending=[False, False, False],
        )
        .reset_index(drop=True)
    )

def tendencia_global_velocidad(mediciones: pd.DataFrame, fecha_ini=None, fecha_fin=None) -> pd.DataFrame:
    """Máximo valor de velocidad RMS registrado por molino y fecha."""
    df = mediciones[mediciones["TipoVariable"].eq("Vibracion-Velocidad")].copy()
    if fecha_ini is not None:
        df = df[df["Fecha"].dt.date >= fecha_ini]
    if fecha_fin is not None:
        df = df[df["Fecha"].dt.date <= fecha_fin]
    if df.empty:
        return pd.DataFrame()

    return (
        df.groupby(["Fecha", "OrdenEquipo", "EquipoCorto"], as_index=False)["Valor"]
          .max()
          .rename(columns={"Valor": "MaxVelocidad"})
          .sort_values(["Fecha", "OrdenEquipo"])
    )


def observaciones_recientes(mediciones: pd.DataFrame, limite=8) -> pd.DataFrame:
    if mediciones.empty or "Observacion" not in mediciones.columns:
        return pd.DataFrame()
    df = mediciones.copy()
    obs = df["Observacion"].astype(str).str.strip()
    mascara = df["Observacion"].notna() & ~obs.str.lower().isin(["", "none", "nan"])
    df = df[mascara].copy()
    if df.empty:
        return pd.DataFrame()
    df = (
        df.sort_values("Fecha", ascending=False)
          .drop_duplicates(subset=["TAG", "CodPunto", "Fecha", "Observacion"])
          .head(limite)
    )
    return df[["Fecha", "EquipoCorto", "CodPunto", "Observacion"]]


PRIORIDAD_ORDEN = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}

def prioridad_actual(
    mediciones: pd.DataFrame,
    dias_vigencia: int = 30,
    tendencias: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Priorización interna y transparente.
    P1: Peligro/Crítico actual.
    P2: Alerta, dato desactualizado, o Tolerable con crecimiento consistente.
    P3: Tolerable/Moderado o Normal con crecimiento consistente.
    P4: condición normal/aceptada sin señales relevantes.

    La tendencia solo aporta si R² >= 0.60 y la pendiente es positiva.
    El RPN se usa únicamente para desempatar el orden, no para cambiar el estado.
    """
    actuales = estado_actual_por_punto(mediciones).copy()
    if tendencias is None:
        tendencias = tendencia_ultimas_6_velocidad(mediciones)

    if actuales.empty:
        return pd.DataFrame()

    if tendencias.empty:
        actuales["Pendiente_mm_s_mes"] = np.nan
        actuales["R2"] = np.nan
        actuales["UltimaFechaTendencia"] = pd.NaT
    else:
        actuales = actuales.merge(
            tendencias[
                ["TAG", "CodPunto", "Pendiente_mm_s_mes", "R2", "UltimaFecha"]
            ].rename(columns={"UltimaFecha": "UltimaFechaTendencia"}),
            on=["TAG", "CodPunto"],
            how="left",
        )

    fecha_global = pd.to_datetime(mediciones["Fecha"].max())
    actuales["DiasDesfase"] = (
        fecha_global.normalize() - pd.to_datetime(actuales["Fecha"]).dt.normalize()
    ).dt.days.astype(int)

    actuales["TendenciaClara"] = (
        actuales["R2"].fillna(-1).ge(0.60)
        & actuales["Pendiente_mm_s_mes"].fillna(0).gt(0)
    )

    prioridades = []
    motivos = []
    acciones = []

    for _, r in actuales.iterrows():
        sev = int(r["Severidad"])
        desactualizado = int(r["DiasDesfase"]) > int(dias_vigencia)
        crecimiento = (
            bool(r["TendenciaClara"])
            and float(r["Pendiente_mm_s_mes"]) >= 0.50
        )

        if sev >= 3:
            p = "P1"
            motivo = "Condición Peligro / Crítico"
            accion = "Revisar / intervenir y confirmar causa"
        elif sev >= 2:
            p = "P2"
            motivo = "Condición Alerta"
            accion = "Inspección dirigida y análisis ≤ 7 días"
        elif desactualizado:
            p = "P2"
            motivo = "Medición desactualizada"
            accion = "Actualizar medición antes de decidir"
        elif sev >= 1 and crecimiento:
            p = "P2"
            motivo = "Tolerable con crecimiento consistente"
            accion = "Repetir medición y revisar punto"
        elif sev >= 1:
            p = "P3"
            motivo = "Condición Tolerable / Moderada"
            accion = "Seguimiento en próxima ruta"
        elif crecimiento:
            p = "P3"
            motivo = "Normal con crecimiento consistente"
            accion = "Seguimiento en próxima ruta"
        else:
            p = "P4"
            motivo = "Condición estable"
            accion = "Monitoreo rutinario"

        prioridades.append(p)
        motivos.append(motivo)
        acciones.append(accion)

    actuales["Prioridad"] = prioridades
    actuales["Motivo"] = motivos
    actuales["Accion"] = acciones
    actuales["OrdenPrioridad"] = actuales["Prioridad"].map(PRIORIDAD_ORDEN)

    return actuales.sort_values(
        ["OrdenPrioridad", "Severidad", "Pendiente_mm_s_mes", "RPN", "OrdenEquipo"],
        ascending=[True, False, False, False, True],
        na_position="last",
    ).reset_index(drop=True)


def jackknife_velocidad(
    mediciones: pd.DataFrame,
    tendencias: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Base Jack-knife: valor actual de velocidad vs pendiente reciente.
    Solo calcula pendiente cuando hay al menos 4 mediciones; el R² permite
    decidir si la tendencia es suficientemente consistente.
    """
    actuales = estado_actual_por_punto(mediciones)
    actuales = actuales[
        actuales["TipoVariable"].eq("Vibracion-Velocidad")
    ].copy()

    if tendencias is None:
        tendencias = tendencia_ultimas_6_velocidad(mediciones)
    if actuales.empty:
        return pd.DataFrame()

    if tendencias.empty:
        actuales["Pendiente_mm_s_mes"] = np.nan
        actuales["R2"] = np.nan
    else:
        actuales = actuales.merge(
            tendencias[
                ["TAG", "CodPunto", "Pendiente_mm_s_mes", "R2", "N"]
            ],
            on=["TAG", "CodPunto"],
            how="left",
        )

    actuales["TendenciaClara"] = actuales["R2"].fillna(-1).ge(0.60)
    actuales["RiesgoVisual"] = (
        actuales["Severidad"].clip(lower=0) * 10
        + actuales["Valor"].astype(float) / 7.0
        + actuales["Pendiente_mm_s_mes"].fillna(0).clip(lower=0)
    )
    return actuales.sort_values(
        ["RiesgoVisual", "Valor"], ascending=[False, False]
    ).reset_index(drop=True)


def rachas_condicion(mediciones: pd.DataFrame, equipo: str, cod_punto: str) -> pd.DataFrame:
    """
    Rachas OBSERVADAS del punto: SANO = Normal/Aceptado.
    Degradado = Tolerable/Moderado/Alerta/Peligro/Crítico.

    No representa vida real del rodamiento salvo que exista una fecha
    de reemplazo/mantenimiento estructurada.
    """
    q = mediciones[
        (mediciones["EquipoCorto"].eq(equipo))
        & (mediciones["CodPunto"].eq(cod_punto))
    ].copy()

    if q.empty:
        return pd.DataFrame()

    q = (
        q.sort_values("Fecha")
        .drop_duplicates(subset=["Fecha"], keep="last")
        .copy()
    )
    q["CondicionBinaria"] = np.where(
        q["Estado"].isin(["NORMAL", "ACEPTADO"]),
        "SANO",
        "DEGRADADO",
    )
    q["Grupo"] = q["CondicionBinaria"].ne(q["CondicionBinaria"].shift()).cumsum()

    out = (
        q.groupby(["Grupo", "CondicionBinaria"], as_index=False)
        .agg(
            Inicio=("Fecha", "min"),
            Fin=("Fecha", "max"),
            Mediciones=("Fecha", "count"),
        )
    )
    out["Dias"] = (
        pd.to_datetime(out["Fin"]) - pd.to_datetime(out["Inicio"])
    ).dt.days.astype(int)
    return out


def resumen_rachas(mediciones: pd.DataFrame, equipo: str, cod_punto: str) -> dict:
    r = rachas_condicion(mediciones, equipo, cod_punto)
    q = mediciones[
        (mediciones["EquipoCorto"].eq(equipo))
        & (mediciones["CodPunto"].eq(cod_punto))
    ].copy()

    if q.empty:
        return {
            "primera": None, "ultima": None, "mediciones": 0,
            "sano_max": None, "sano_prom": None,
            "degradado_max": None, "degradado_prom": None,
            "transiciones": 0, "estado_actual": "SIN DATO",
        }

    q = q.sort_values("Fecha")
    sano = r[r["CondicionBinaria"].eq("SANO")]
    deg = r[r["CondicionBinaria"].eq("DEGRADADO")]

    return {
        "primera": q["Fecha"].min(),
        "ultima": q["Fecha"].max(),
        "mediciones": int(q["Fecha"].nunique()),
        "sano_max": int(sano["Dias"].max()) if not sano.empty else None,
        "sano_prom": float(sano["Dias"].mean()) if not sano.empty else None,
        "degradado_max": int(deg["Dias"].max()) if not deg.empty else None,
        "degradado_prom": float(deg["Dias"].mean()) if not deg.empty else None,
        "transiciones": max(int(len(r) - 1), 0),
        "estado_actual": str(q.iloc[-1]["Estado"]),
    }


def eventos_mantenimiento_observados(
    mediciones: pd.DataFrame, equipo: str
) -> pd.DataFrame:
    """
    Detecta SOLO menciones explícitas en Observacion.
    Se muestran como eventos registrados; no se asumen como cambio de rodamiento.
    """
    q = mediciones[
        mediciones["EquipoCorto"].eq(equipo)
        & mediciones["Observacion"].notna()
    ].copy()

    if q.empty:
        return pd.DataFrame()

    texto = q["Observacion"].astype(str).str.upper()
    patron = (
        r"OVH|OVERHAUL|MANTEN|CAMBIO.*RODAM|RODAM.*CAMBIO|"
        r"CAMBIO DE RODAM|ALINEA|REPAR"
    )
    q = q[texto.str.contains(patron, regex=True, na=False)].copy()
    if q.empty:
        return pd.DataFrame()

    return (
        q[["Fecha", "EquipoCorto", "Observacion"]]
        .drop_duplicates()
        .sort_values("Fecha", ascending=False)
        .reset_index(drop=True)
    )


def cobertura_monitoreo(
    mediciones: pd.DataFrame,
    ventana_dias: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Cobertura por PUNTO FÍSICO en una ventana relativa a la última fecha global.
    N_Puntos proviene de DIM_EQUIPO.
    Se consideran solo puntos físicos numéricos (1..N_Puntos); los puntos
    térmicos de piñón/catalina A/B/C no aumentan el denominador.
    """
    equipos, _ = cargar_dimensiones()
    fecha_global = pd.to_datetime(mediciones["Fecha"].max())
    inicio = fecha_global - pd.Timedelta(days=int(ventana_dias))

    filas = []
    detalle = []

    for _, e in equipos.sort_values("OrdenEquipo").iterrows():
        equipo = e["EquipoCorto"]
        tag = e["TAG"]
        plan = int(e["N_Puntos"])

        qeq = mediciones[mediciones["TAG"].eq(tag)].copy()
        qwin = qeq[qeq["Fecha"].ge(inicio)].copy()

        puntos_medidos = set()
        for p in qwin["Punto"].dropna():
            s = str(p).replace(".0", "").strip()
            if s.isdigit():
                n = int(s)
                if 1 <= n <= plan:
                    puntos_medidos.add(n)

        esperados = set(range(1, plan + 1))
        faltantes = sorted(esperados - puntos_medidos)
        ultima = qeq["Fecha"].max() if not qeq.empty else pd.NaT
        desfase = (
            int((fecha_global.normalize() - pd.to_datetime(ultima).normalize()).days)
            if pd.notna(ultima) else None
        )

        filas.append({
            "TAG": tag,
            "EquipoCorto": equipo,
            "OrdenEquipo": int(e["OrdenEquipo"]),
            "PuntosPlanificados": plan,
            "PuntosMedidos": len(puntos_medidos),
            "CoberturaPct": 100.0 * len(puntos_medidos) / plan if plan else 0.0,
            "PuntosFaltantes": len(faltantes),
            "UltimaMedicion": ultima,
            "DiasDesfase": desfase,
            "RondasPeriodo": int(qwin["Fecha"].nunique()),
        })

        for n in sorted(esperados):
            qp = qeq[qeq["Punto"].astype(str).str.replace(".0", "", regex=False).eq(str(n))]
            ult_p = qp["Fecha"].max() if not qp.empty else pd.NaT
            medido = n in puntos_medidos
            detalle.append({
                "TAG": tag,
                "EquipoCorto": equipo,
                "Punto": n,
                "EstadoCobertura": "MEDIDO" if medido else "PENDIENTE",
                "UltimaMedicion": ult_p,
                "EnVentana": medido,
            })

    return (
        pd.DataFrame(filas).sort_values("OrdenEquipo").reset_index(drop=True),
        pd.DataFrame(detalle),
    )


# ============================================================================
# V5 · REGLAS DE CONFIABILIDAD Y PROYECCIÓN
# ============================================================================

def _ajuste_lineal_metricas(q: pd.DataFrame) -> dict | None:
    """Ajuste lineal y métricas de validación para una ventana de velocidad."""
    q = (
        q.sort_values("Fecha")
        .drop_duplicates(subset=["Fecha"], keep="last")
        .copy()
    )
    if len(q) < 4:
        return None

    fechas = pd.to_datetime(q["Fecha"])
    x = (fechas - fechas.min()).dt.total_seconds().to_numpy() / 86400.0
    y = q["Valor"].astype(float).to_numpy()

    if len(np.unique(x)) < 2:
        return None

    slope, intercept = np.polyfit(x, y, 1)
    yhat = slope * x + intercept
    resid = y - yhat

    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 1.0
    rmse = float(np.sqrt(np.mean(resid ** 2)))
    mae = float(np.mean(np.abs(resid)))

    # Escala para comparar error entre puntos sin dividir por valores pequeños.
    escala = max(float(np.ptp(y)), float(np.mean(np.abs(y))) * 0.25, 0.75)
    nrmse = rmse / escala

    # Backtest temporal: entrenar sin las últimas observaciones y predecirlas.
    holdout = 2 if len(q) >= 8 else 1
    train_n = len(q) - holdout
    back_mae = np.nan
    back_nmae = np.nan
    if train_n >= 4:
        xt = x[:train_n]
        yt = y[:train_n]
        s_t, i_t = np.polyfit(xt, yt, 1)
        pred = s_t * x[train_n:] + i_t
        back_mae = float(np.mean(np.abs(y[train_n:] - pred)))
        back_nmae = back_mae / escala

    # Estabilidad de la pendiente: comparar dos ventanas solapadas internas.
    estabilidad = 0.0
    if len(q) >= 6:
        k = max(4, int(math.ceil(len(q) * 0.65)))
        qa = q.head(k)
        qb = q.tail(k)

        def _slope(qq):
            ff = pd.to_datetime(qq["Fecha"])
            xx = (ff - ff.min()).dt.total_seconds().to_numpy() / 86400.0
            yy = qq["Valor"].astype(float).to_numpy()
            if len(np.unique(xx)) < 2:
                return np.nan
            return float(np.polyfit(xx, yy, 1)[0])

        s1 = _slope(qa)
        s2 = _slope(qb)
        if np.isfinite(s1) and np.isfinite(s2):
            if slope > 0 and s1 > 0 and s2 > 0:
                ratio = min(abs(s1), abs(s2)) / max(abs(s1), abs(s2), 1e-12)
                estabilidad = float(np.clip(ratio, 0.0, 1.0))
            elif slope <= 0 and s1 <= 0 and s2 <= 0:
                estabilidad = 1.0

    # Puntuación compuesta. Premia ajuste, predicción retrospectiva,
    # bajo error, estabilidad y cantidad de información.
    r2_score = float(np.clip(r2, 0.0, 1.0))
    rmse_score = float(np.exp(-2.5 * max(nrmse, 0.0)))
    back_score = (
        float(np.exp(-2.5 * max(back_nmae, 0.0)))
        if np.isfinite(back_nmae) else 0.35
    )
    n_score = float(min(len(q) / 15.0, 1.0))
    span_days = max(float(x[-1] - x[0]), 0.0)
    span_score = float(min(span_days / 120.0, 1.0))

    score = (
        0.30 * r2_score
        + 0.20 * rmse_score
        + 0.25 * back_score
        + 0.15 * estabilidad
        + 0.07 * n_score
        + 0.03 * span_score
    )

    return {
        "q": q,
        "x": x,
        "y": y,
        "slope": float(slope),
        "intercept": float(intercept),
        "r2": float(r2),
        "rmse": rmse,
        "mae": mae,
        "nrmse": float(nrmse),
        "back_mae": float(back_mae) if np.isfinite(back_mae) else np.nan,
        "back_nmae": float(back_nmae) if np.isfinite(back_nmae) else np.nan,
        "estabilidad": float(estabilidad),
        "score": float(score),
        "span_days": span_days,
    }


def _seleccionar_modelo_adaptativo(q: pd.DataFrame) -> dict | None:
    """
    Evalúa varias ventanas recientes y selecciona la de mejor validación.
    Evita fijar arbitrariamente siempre 6 mediciones.
    """
    q = (
        q.sort_values("Fecha")
        .drop_duplicates(subset=["Fecha"], keep="last")
        .copy()
    )
    if len(q) < 6:
        return None

    candidatos_n = [6, 8, 10, 12, 15, 20, 25, len(q)]
    candidatos_n = sorted(set(n for n in candidatos_n if 6 <= n <= len(q)))

    modelos = []
    for nwin in candidatos_n:
        m = _ajuste_lineal_metricas(q.tail(nwin))
        if m is None:
            continue
        m["nwin"] = int(nwin)
        modelos.append(m)

    if not modelos:
        return None

    # Se exige suficiente información reciente, pero se deja que gane la
    # ventana más representativa por desempeño matemático.
    modelos.sort(
        key=lambda m: (
            m["score"],
            m["r2"],
            -m["nrmse"],
            m["nwin"],
        ),
        reverse=True,
    )
    return modelos[0]


def _intervalo_cruce_bootstrap(
    modelo: dict,
    umbral: float,
    fecha_actual: pd.Timestamp,
    valor_actual: float,
    horizonte_max_dias: int,
    simulaciones: int = 400,
) -> tuple[int | None, int | None]:
    """
    Intervalo empírico 10–90 % de días al umbral mediante bootstrap residual.
    No modifica la estimación central; cuantifica sensibilidad del ajuste.
    """
    if valor_actual >= umbral:
        return 0, 0

    x = modelo["x"]
    y = modelo["y"]
    slope = modelo["slope"]
    intercept = modelo["intercept"]
    yhat = slope * x + intercept
    resid = y - yhat

    if len(resid) < 4 or np.allclose(resid, 0):
        return None, None

    rng = np.random.default_rng(20261107)
    cruces = []
    x_last = float(x[-1])

    for _ in range(int(simulaciones)):
        eps = rng.choice(resid, size=len(resid), replace=True)
        ys = yhat + eps
        try:
            s, i = np.polyfit(x, ys, 1)
        except Exception:
            continue
        if not np.isfinite(s) or s <= 0:
            continue

        estimado_en_ultima = float(s * x_last + i)
        if estimado_en_ultima >= umbral:
            dias = 0.0
        else:
            dias = (umbral - estimado_en_ultima) / s

        if 0 <= dias <= horizonte_max_dias:
            cruces.append(float(dias))

    if len(cruces) < max(30, simulaciones * 0.15):
        return None, None

    return (
        int(math.floor(np.quantile(cruces, 0.10))),
        int(math.ceil(np.quantile(cruces, 0.90))),
    )


def proyeccion_lineal_punto(
    mediciones: pd.DataFrame,
    equipo: str,
    cod_punto: str,
    n: int = 6,  # se conserva por compatibilidad; ya no fija la ventana
    r2_min: float = 0.65,
    horizonte_max_dias: int = 180,
) -> dict:
    """
    Proyección adaptativa y conservadora de velocidad RMS.

    Reglas:
    - Si existe mantenimiento/reemplazo explícito, usa SOLO el ciclo vigente.
    - Prueba varias ventanas recientes (6, 8, 10, 12, 15, 20, 25 y ciclo).
    - Selecciona la ventana con mejor combinación de R², RMSE, backtest,
      estabilidad de pendiente, cantidad de datos y cobertura temporal.
    - Solo proyecta si la pendiente es positiva y la validación es suficiente.
    - Calcula incertidumbre empírica del cruce mediante bootstrap residual.

    Los umbrales de proyección siguen siendo los oficiales del dashboard:
      5.0 mm/s -> entrada a ALERTA
      7.0 mm/s -> entrada a PELIGRO
    """
    qall = mediciones[
        (mediciones["EquipoCorto"].eq(equipo))
        & (mediciones["CodPunto"].eq(cod_punto))
        & (mediciones["TipoVariable"].eq("Vibracion-Velocidad"))
    ].copy()

    qall = (
        qall.sort_values("Fecha")
        .drop_duplicates(subset=["Fecha"], keep="last")
        .copy()
    )

    evento = None
    try:
        evento = evento_mantenimiento_relevante(mediciones, equipo, cod_punto)
    except Exception:
        evento = None

    q = qall.copy()
    ciclo_estructurado = False
    fecha_mantenimiento = None

    if evento is not None:
        fecha_mantenimiento = pd.to_datetime(evento["fecha"])
        q = q[pd.to_datetime(q["Fecha"]).ge(fecha_mantenimiento)].copy()
        ciclo_estructurado = True

    base = {
        "valido": False,
        "metodo": "Regresión lineal adaptativa",
        "n": int(len(q)),
        "n_total_ciclo": int(len(q)),
        "ventana_seleccionada": None,
        "r2": np.nan,
        "rmse": np.nan,
        "mae": np.nan,
        "backtest_mae": np.nan,
        "score_modelo": np.nan,
        "estabilidad": np.nan,
        "pendiente_dia": np.nan,
        "pendiente_mes": np.nan,
        "valor_actual": float(qall.iloc[-1]["Valor"]) if not qall.empty else np.nan,
        "fecha_actual": pd.to_datetime(qall.iloc[-1]["Fecha"]) if not qall.empty else pd.NaT,
        "confianza": "No confiable",
        "dias_alerta": None,
        "fecha_alerta": None,
        "dias_peligro": None,
        "fecha_peligro": None,
        "dias_alerta_min": None,
        "dias_alerta_max": None,
        "dias_peligro_min": None,
        "dias_peligro_max": None,
        "ciclo_estructurado": ciclo_estructurado,
        "fecha_mantenimiento": fecha_mantenimiento,
        "motivo": "",
        "serie": q,
    }

    if len(q) < 6:
        if ciclo_estructurado:
            base["motivo"] = (
                "El ciclo vigente tiene menos de 6 mediciones; no se proyecta "
                "usando datos anteriores al mantenimiento."
            )
        else:
            base["motivo"] = "Se requieren al menos 6 mediciones válidas."
        return base

    modelo = _seleccionar_modelo_adaptativo(q)
    if modelo is None:
        base["motivo"] = "No fue posible construir un modelo temporal válido."
        return base

    qm = modelo["q"]
    slope = modelo["slope"]
    r2 = modelo["r2"]
    valor_actual = float(qall.iloc[-1]["Valor"])
    fecha_actual = pd.to_datetime(qall.iloc[-1]["Fecha"])

    base.update({
        "n": int(len(qm)),
        "ventana_seleccionada": int(len(qm)),
        "r2": float(r2),
        "rmse": float(modelo["rmse"]),
        "mae": float(modelo["mae"]),
        "backtest_mae": (
            float(modelo["back_mae"])
            if np.isfinite(modelo["back_mae"]) else np.nan
        ),
        "score_modelo": float(modelo["score"]),
        "estabilidad": float(modelo["estabilidad"]),
        "pendiente_dia": float(slope),
        "pendiente_mes": float(slope * 30.0),
        "valor_actual": valor_actual,
        "fecha_actual": fecha_actual,
        "serie": qm,
    })

    # GATES DE CONFIABILIDAD
    if slope <= 0:
        base["motivo"] = "La tendencia seleccionada no es creciente."
        return base

    if r2 < float(r2_min):
        base["motivo"] = (
            "El ajuste de la ventana seleccionada no alcanza la consistencia mínima."
        )
        return base

    if modelo["nrmse"] > 0.30:
        base["motivo"] = "El error residual del modelo es demasiado alto."
        return base

    if np.isfinite(modelo["back_nmae"]) and modelo["back_nmae"] > 0.35:
        base["motivo"] = (
            "La validación retrospectiva muestra un error demasiado alto."
        )
        return base

    if modelo["score"] < 0.64:
        base["motivo"] = "La calidad combinada del modelo no es suficiente."
        return base

    if modelo["estabilidad"] < 0.25:
        base["motivo"] = (
            "La pendiente cambia demasiado dentro de la ventana seleccionada."
        )
        return base

    base["valido"] = True

    if (
        modelo["score"] >= 0.80
        and r2 >= 0.75
        and len(qm) >= 10
        and (
            not np.isfinite(modelo["back_nmae"])
            or modelo["back_nmae"] <= 0.20
        )
    ):
        base["confianza"] = "Alta"
    else:
        base["confianza"] = "Media"

    def cruce_central(umbral: float):
        if valor_actual >= umbral:
            return 0, fecha_actual

        # Se proyecta desde el valor ajustado en la fecha actual para mantener
        # coherencia con la recta seleccionada, no desde un único pico aislado.
        x_last = float(modelo["x"][-1])
        valor_modelado_actual = float(
            modelo["slope"] * x_last + modelo["intercept"]
        )
        dias = (umbral - valor_modelado_actual) / modelo["slope"]
        if dias < 0:
            return 0, fecha_actual
        if dias > horizonte_max_dias:
            return None, None
        return (
            int(math.ceil(dias)),
            fecha_actual + pd.Timedelta(days=float(dias)),
        )

    da, fa = cruce_central(5.0)
    dp, fp = cruce_central(7.0)
    base["dias_alerta"], base["fecha_alerta"] = da, fa
    base["dias_peligro"], base["fecha_peligro"] = dp, fp

    if da is not None:
        lo, hi = _intervalo_cruce_bootstrap(
            modelo, 5.0, fecha_actual, valor_actual, horizonte_max_dias
        )
        base["dias_alerta_min"], base["dias_alerta_max"] = lo, hi

    if dp is not None:
        lo, hi = _intervalo_cruce_bootstrap(
            modelo, 7.0, fecha_actual, valor_actual, horizonte_max_dias
        )
        base["dias_peligro_min"], base["dias_peligro_max"] = lo, hi

    if da is None and dp is None:
        base["motivo"] = (
            f"Modelo válido, pero los umbrales no se alcanzarían dentro de "
            f"{horizonte_max_dias} días."
        )
    else:
        base["motivo"] = (
            "Modelo adaptativo validado con error, backtest y estabilidad."
        )

    return base


def eventos_mantenimiento_detalle(
    mediciones: pd.DataFrame,
    equipo: str,
) -> pd.DataFrame:
    """
    Extrae eventos explícitos de mantenimiento desde Observacion y conserva
    punto/componente para poder relacionarlos con el componente seleccionado.
    """
    q = mediciones[
        mediciones["EquipoCorto"].eq(equipo)
        & mediciones["Observacion"].notna()
    ].copy()
    if q.empty:
        return pd.DataFrame()

    txt = q["Observacion"].astype(str).str.upper().str.strip()
    patron = (
        r"OVH|OVERHAUL|MANTEN|CAMBIO\s*(?:DE\s*)?RODAM|"
        r"RODAM.*CAMBIO|REEMPLAZ.*RODAM|CAMBIO\s*RODAM|"
        r"ALINEA|REPAR"
    )
    q = q[txt.str.contains(patron, regex=True, na=False)].copy()
    if q.empty:
        return pd.DataFrame()

    cols = ["Fecha","EquipoCorto","TAG","CodPunto","Punto","Componente","Observacion"]
    cols = [c for c in cols if c in q.columns]
    return (
        q[cols]
        .drop_duplicates()
        .sort_values("Fecha", ascending=False)
        .reset_index(drop=True)
    )


def evento_mantenimiento_relevante(
    mediciones: pd.DataFrame,
    equipo: str,
    cod_punto: str,
) -> dict | None:
    """
    Busca el evento explícito más reciente relacionado con el punto físico o
    componente del código seleccionado. Si no puede relacionarlo, usa el evento
    de equipo únicamente como referencia y lo marca como tal.
    """
    qsel = mediciones[
        (mediciones["EquipoCorto"].eq(equipo))
        & (mediciones["CodPunto"].eq(cod_punto))
    ].copy()
    if qsel.empty:
        return None

    rr = qsel.sort_values("Fecha").iloc[-1]
    punto = str(rr.get("Punto",""))
    componente = str(rr.get("Componente",""))

    ev = eventos_mantenimiento_detalle(mediciones, equipo)
    if ev.empty:
        return None

    # Primero mismo punto físico.
    ep = ev[ev.get("Punto", pd.Series(index=ev.index, dtype=object)).astype(str).eq(punto)]
    if not ep.empty:
        e = ep.sort_values("Fecha", ascending=False).iloc[0]
        return {"fecha": e["Fecha"], "observacion": e["Observacion"], "alcance": "Punto físico"}

    # Luego mismo componente.
    if "Componente" in ev.columns:
        ec = ev[ev["Componente"].astype(str).eq(componente)]
        if not ec.empty:
            e = ec.sort_values("Fecha", ascending=False).iloc[0]
            return {"fecha": e["Fecha"], "observacion": e["Observacion"], "alcance": "Componente"}

    # Finalmente evento general del equipo, solo como referencia.
    e = ev.sort_values("Fecha", ascending=False).iloc[0]
    return {"fecha": e["Fecha"], "observacion": e["Observacion"], "alcance": "Equipo (referencia)"}


def rachas_operativas_velocidad(
    mediciones: pd.DataFrame,
    equipo: str,
    cod_punto: str,
    fecha_inicio=None,
) -> pd.DataFrame:
    """
    Regla de confiabilidad V5 para velocidad:
      SANO OPERATIVO: <= 5 mm/s
      DEGRADADO: >5 a 7 mm/s
      CRÍTICO: >7 mm/s

    Se alinea con los límites oficiales ya aprobados:
    Normal + Tolerable = sano operativo; Alerta = degradado; Peligro = crítico.
    """
    q = mediciones[
        (mediciones["EquipoCorto"].eq(equipo))
        & (mediciones["CodPunto"].eq(cod_punto))
        & (mediciones["TipoVariable"].eq("Vibracion-Velocidad"))
    ].copy()
    if fecha_inicio is not None:
        q = q[pd.to_datetime(q["Fecha"]).ge(pd.to_datetime(fecha_inicio))]

    q = (
        q.sort_values("Fecha")
        .drop_duplicates(subset=["Fecha"], keep="last")
        .copy()
    )
    if q.empty:
        return pd.DataFrame()

    def clas(v):
        v = float(v)
        if v <= 5.0:
            return "SANO"
        if v <= 7.0:
            return "DEGRADADO"
        return "CRITICO"

    q["CondicionOperativa"] = q["Valor"].map(clas)
    q["Grupo"] = q["CondicionOperativa"].ne(q["CondicionOperativa"].shift()).cumsum()
    out = (
        q.groupby(["Grupo","CondicionOperativa"], as_index=False)
        .agg(
            Inicio=("Fecha","min"),
            Fin=("Fecha","max"),
            Mediciones=("Fecha","count"),
            ValorInicial=("Valor","first"),
            ValorFinal=("Valor","last"),
        )
    )
    out["Dias"] = (
        pd.to_datetime(out["Fin"]) - pd.to_datetime(out["Inicio"])
    ).dt.days.astype(int)
    return out


def confiabilidad_ciclo_actual(
    mediciones: pd.DataFrame,
    equipo: str,
    cod_punto: str,
) -> dict:
    """
    Calcula indicadores desde el último evento de mantenimiento explícito.
    Si no existe evento, no inventa un inicio de ciclo.
    """
    evento = evento_mantenimiento_relevante(mediciones, equipo, cod_punto)
    q = mediciones[
        (mediciones["EquipoCorto"].eq(equipo))
        & (mediciones["CodPunto"].eq(cod_punto))
        & (mediciones["TipoVariable"].eq("Vibracion-Velocidad"))
    ].copy()
    q = q.sort_values("Fecha")
    if q.empty:
        return {"evento": evento, "disponible": False}

    fecha_ultima = pd.to_datetime(q["Fecha"].max())
    if evento is None:
        return {
            "evento": None, "disponible": False, "fecha_ultima": fecha_ultima,
            "dias_desde_mantto": None, "dias_sano": None,
            "dias_degradado": None, "estado_ciclo": None,
            "fecha_salida_sano": None,
        }

    fecha_m = pd.to_datetime(evento["fecha"])
    qc = q[pd.to_datetime(q["Fecha"]).ge(fecha_m)].copy()
    if qc.empty:
        return {
            "evento": evento, "disponible": False, "fecha_ultima": fecha_ultima,
            "dias_desde_mantto": int((fecha_ultima.normalize()-fecha_m.normalize()).days),
            "dias_sano": None, "dias_degradado": None, "estado_ciclo": None,
            "fecha_salida_sano": None,
        }

    qc["Cond"] = np.where(qc["Valor"] <= 5.0, "SANO",
                  np.where(qc["Valor"] <= 7.0, "DEGRADADO", "CRITICO"))
    primera_fuera_sano = qc[qc["Valor"] > 5.0]["Fecha"].min()
    dias_desde = int((fecha_ultima.normalize() - fecha_m.normalize()).days)

    if pd.isna(primera_fuera_sano):
        dias_sano = dias_desde
        dias_degradado = 0
        salida = None
    else:
        salida = pd.to_datetime(primera_fuera_sano)
        dias_sano = max(int((salida.normalize() - fecha_m.normalize()).days), 0)
        dias_degradado = max(int((fecha_ultima.normalize() - salida.normalize()).days), 0)

    return {
        "evento": evento,
        "disponible": True,
        "fecha_ultima": fecha_ultima,
        "fecha_mantenimiento": fecha_m,
        "dias_desde_mantto": dias_desde,
        "dias_sano": dias_sano,
        "dias_degradado": dias_degradado,
        "estado_ciclo": str(qc.iloc[-1]["Cond"]),
        "fecha_salida_sano": salida,
    }


def ciclos_mantenimiento(
    mediciones: pd.DataFrame,
    equipo: str,
    cod_punto: str,
) -> dict:
    """
    Intervalos entre eventos explícitos relacionados con el punto físico/componente.

    Estimador central: mediana entre cambios, por robustez ante intervalos extremos.
    Incertidumbre: bootstrap de la mediana (P10–P90), cuando hay >=2 intervalos.
    No usa Weibull con muestras pequeñas.
    """
    qsel = mediciones[
        (mediciones["EquipoCorto"].eq(equipo))
        & (mediciones["CodPunto"].eq(cod_punto))
    ].copy()

    if qsel.empty:
        return {"eventos": pd.DataFrame(), "intervalos": [], "proyeccion": None}

    rr = qsel.sort_values("Fecha").iloc[-1]
    punto = str(rr.get("Punto", ""))
    componente = str(rr.get("Componente", ""))

    ev = eventos_mantenimiento_detalle(mediciones, equipo)
    if ev.empty:
        return {"eventos": ev, "intervalos": [], "proyeccion": None}

    # El mantenimiento afecta el punto físico/componente, no una sola dirección.
    rel = pd.DataFrame()
    if "Punto" in ev.columns:
        rel = ev[ev["Punto"].astype(str).eq(punto)].copy()

    if rel.empty and "Componente" in ev.columns:
        rel = ev[ev["Componente"].astype(str).eq(componente)].copy()

    if rel.empty:
        return {"eventos": rel, "intervalos": [], "proyeccion": None}

    fechas = sorted(pd.to_datetime(rel["Fecha"].drop_duplicates()).tolist())
    intervalos = [
        int((fechas[i] - fechas[i - 1]).days)
        for i in range(1, len(fechas))
        if fechas[i] > fechas[i - 1]
    ]

    proy = None
    if len(intervalos) >= 2:
        arr = np.asarray(intervalos, dtype=float)
        mediana = float(np.median(arr))
        media = float(np.mean(arr))
        desviacion = float(np.std(arr, ddof=1)) if len(arr) >= 2 else 0.0
        mad = float(np.median(np.abs(arr - mediana)))
        ultima = fechas[-1]
        fecha_est = ultima + pd.Timedelta(days=mediana)

        # Bootstrap robusto y determinístico de la mediana.
        rng = np.random.default_rng(20261107)
        boots = []
        for _ in range(2000):
            sample = rng.choice(arr, size=len(arr), replace=True)
            boots.append(float(np.median(sample)))

        p10 = float(np.quantile(boots, 0.10))
        p90 = float(np.quantile(boots, 0.90))
        fecha_min = ultima + pd.Timedelta(days=p10)
        fecha_max = ultima + pd.Timedelta(days=p90)

        if len(intervalos) >= 6:
            confianza = "Alta"
        elif len(intervalos) >= 4:
            confianza = "Media"
        else:
            confianza = "Baja"

        proy = {
            "metodo": "Mediana entre cambios",
            "intervalos": len(intervalos),
            "mediana_dias": mediana,
            "media_dias": media,
            "desviacion_dias": desviacion,
            "mad_dias": mad,
            "ultima_fecha": ultima,
            "fecha_estimada": fecha_est,
            "dias_estimados": int(round(mediana)),
            "dias_p10": int(round(p10)),
            "dias_p90": int(round(p90)),
            "fecha_estimada_min": fecha_min,
            "fecha_estimada_max": fecha_max,
            "confianza": confianza,
        }

    return {
        "eventos": rel.sort_values("Fecha", ascending=False),
        "intervalos": intervalos,
        "proyeccion": proy,
    }


def cobertura_global(
    mediciones: pd.DataFrame,
    ventana_dias: int = 30,
) -> dict:
    cob, det = cobertura_monitoreo(mediciones, ventana_dias)
    total_plan = int(cob["PuntosPlanificados"].sum())
    total_med = int(cob["PuntosMedidos"].sum())
    pct = 100.0 * total_med / total_plan if total_plan else 0.0
    return {
        "cobertura": cob,
        "detalle": det,
        "planificados": total_plan,
        "medidos": total_med,
        "pendientes": total_plan - total_med,
        "pct": pct,
    }


def confiabilidad_ciclo_actual(
    mediciones: pd.DataFrame,
    equipo: str,
    cod_punto: str,
) -> dict:
    """
    Indicadores del ciclo desde el último evento explícito:
      SANO <=5 mm/s
      DEGRADADO >5 a 7 mm/s
      CRITICO >7 mm/s

    Las duraciones se interpretan como tiempo calendario desde el primer cruce
    observado de cada umbral dentro del ciclo.
    """
    evento = evento_mantenimiento_relevante(mediciones, equipo, cod_punto)
    q = mediciones[
        (mediciones["EquipoCorto"].eq(equipo))
        & (mediciones["CodPunto"].eq(cod_punto))
        & (mediciones["TipoVariable"].eq("Vibracion-Velocidad"))
    ].copy().sort_values("Fecha")

    if q.empty:
        return {"evento": evento, "disponible": False}

    fecha_ultima = pd.to_datetime(q["Fecha"].max())
    if evento is None:
        return {
            "evento": None, "disponible": False, "fecha_ultima": fecha_ultima,
            "dias_desde_mantto": None, "dias_sano": None,
            "dias_degradado": None, "dias_critico": None,
            "estado_ciclo": None, "fecha_salida_sano": None,
            "fecha_entrada_critico": None,
        }

    fecha_m = pd.to_datetime(evento["fecha"])
    qc = q[pd.to_datetime(q["Fecha"]).ge(fecha_m)].copy()
    dias_desde = int((fecha_ultima.normalize() - fecha_m.normalize()).days)

    if qc.empty:
        return {
            "evento": evento, "disponible": False, "fecha_ultima": fecha_ultima,
            "fecha_mantenimiento": fecha_m, "dias_desde_mantto": dias_desde,
            "dias_sano": None, "dias_degradado": None, "dias_critico": None,
            "estado_ciclo": None, "fecha_salida_sano": None,
            "fecha_entrada_critico": None,
        }

    qc["Cond"] = np.where(
        qc["Valor"] <= 5.0, "SANO",
        np.where(qc["Valor"] <= 7.0, "DEGRADADO", "CRITICO")
    )

    salida_sano = qc[qc["Valor"] > 5.0]["Fecha"].min()
    entrada_crit = qc[qc["Valor"] > 7.0]["Fecha"].min()

    if pd.isna(salida_sano):
        dias_sano = dias_desde
        dias_degradado = 0
        dias_critico = 0
        salida = None
        crit = None
    else:
        salida = pd.to_datetime(salida_sano)
        dias_sano = max(int((salida.normalize() - fecha_m.normalize()).days), 0)

        if pd.isna(entrada_crit):
            dias_degradado = max(int((fecha_ultima.normalize() - salida.normalize()).days), 0)
            dias_critico = 0
            crit = None
        else:
            crit = pd.to_datetime(entrada_crit)
            dias_degradado = max(int((crit.normalize() - salida.normalize()).days), 0)
            dias_critico = max(int((fecha_ultima.normalize() - crit.normalize()).days), 0)

    return {
        "evento": evento,
        "disponible": True,
        "fecha_ultima": fecha_ultima,
        "fecha_mantenimiento": fecha_m,
        "dias_desde_mantto": dias_desde,
        "dias_sano": dias_sano,
        "dias_degradado": dias_degradado,
        "dias_critico": dias_critico,
        "estado_ciclo": str(qc.iloc[-1]["Cond"]),
        "fecha_salida_sano": salida,
        "fecha_entrada_critico": crit,
    }


def confiabilidad_ciclo_actual(
    mediciones: pd.DataFrame,
    equipo: str,
    cod_punto: str,
) -> dict:
    """
    Duraciones acumuladas dentro del ciclo desde el último evento explícito.
    Aproximación por intervalos: la condición observada en una medición se
    mantiene hasta la siguiente medición. El tramo entre el mantenimiento y
    la primera medición toma la condición de esa primera medición.

    SANO <=5; DEGRADADO >5 a 7; CRITICO >7.
    """
    evento = evento_mantenimiento_relevante(mediciones, equipo, cod_punto)
    q = mediciones[
        (mediciones["EquipoCorto"].eq(equipo))
        & (mediciones["CodPunto"].eq(cod_punto))
        & (mediciones["TipoVariable"].eq("Vibracion-Velocidad"))
    ].copy().sort_values("Fecha").drop_duplicates(subset=["Fecha"], keep="last")

    if q.empty:
        return {"evento": evento, "disponible": False}

    fecha_ultima = pd.to_datetime(q["Fecha"].max())
    if evento is None:
        return {
            "evento": None, "disponible": False, "fecha_ultima": fecha_ultima,
            "dias_desde_mantto": None, "dias_sano": None,
            "dias_degradado": None, "dias_critico": None,
            "estado_ciclo": None,
        }

    fecha_m = pd.to_datetime(evento["fecha"])
    qc = q[pd.to_datetime(q["Fecha"]).ge(fecha_m)].copy()
    dias_desde = max(int((fecha_ultima.normalize() - fecha_m.normalize()).days), 0)
    if qc.empty:
        return {
            "evento": evento, "disponible": False, "fecha_ultima": fecha_ultima,
            "fecha_mantenimiento": fecha_m, "dias_desde_mantto": dias_desde,
            "dias_sano": None, "dias_degradado": None, "dias_critico": None,
            "estado_ciclo": None,
        }

    qc["Cond"] = np.where(
        qc["Valor"] <= 5.0, "SANO",
        np.where(qc["Valor"] <= 7.0, "DEGRADADO", "CRITICO")
    )
    fechas = pd.to_datetime(qc["Fecha"]).tolist()
    conds = qc["Cond"].tolist()

    acumulado = {"SANO": 0, "DEGRADADO": 0, "CRITICO": 0}

    # Mantenimiento -> primera medición.
    if fechas:
        gap0 = max(int((fechas[0].normalize() - fecha_m.normalize()).days), 0)
        acumulado[conds[0]] += gap0

    # Cada medición mantiene su estado hasta la siguiente.
    for i in range(len(fechas)-1):
        dias = max(int((fechas[i+1].normalize() - fechas[i].normalize()).days), 0)
        acumulado[conds[i]] += dias

    return {
        "evento": evento,
        "disponible": True,
        "fecha_ultima": fecha_ultima,
        "fecha_mantenimiento": fecha_m,
        "dias_desde_mantto": dias_desde,
        "dias_sano": int(acumulado["SANO"]),
        "dias_degradado": int(acumulado["DEGRADADO"]),
        "dias_critico": int(acumulado["CRITICO"]),
        "estado_ciclo": str(qc.iloc[-1]["Cond"]),
    }
