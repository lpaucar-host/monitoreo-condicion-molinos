from __future__ import annotations

from pathlib import Path
import io
import os
import re
import math
import zipfile
import pandas as pd
import numpy as np


def _leer_csv_bytes(raw: bytes) -> pd.DataFrame:
    texto = None
    for enc in ("utf-8-sig", "cp1252", "latin1"):
        try:
            texto = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:
        raise ValueError("No fue posible decodificar el CSV.")

    df = pd.read_csv(io.StringIO(texto), sep=";")
    if len(df.columns) < 2:
        raise ValueError("El CSV no contiene dos columnas espectrales.")

    df = df.iloc[:, :2].copy()
    df.columns = [str(c).strip() for c in df.columns]
    df.iloc[:, 0] = pd.to_numeric(df.iloc[:, 0], errors="coerce")
    df.iloc[:, 1] = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    return df.dropna()


def _normalizar_espectro(df: pd.DataFrame, variable: str) -> pd.DataFrame:
    fcol, acol = df.columns[:2]
    frecuencia = df[fcol].astype(float).to_numpy()

    if "cpm" in fcol.lower():
        frecuencia_hz = frecuencia / 60.0
        unidad_original = "CPM"
    else:
        frecuencia_hz = frecuencia
        unidad_original = "Hz"

    out = pd.DataFrame({
        "FrecuenciaHz": frecuencia_hz,
        "Amplitud": df[acol].astype(float).to_numpy(),
    })
    out["Variable"] = variable
    out.attrs["unidad_frecuencia_original"] = unidad_original
    out.attrs["unidad_amplitud"] = (
        "mm/s" if variable.lower().startswith("vel")
        else "gE" if variable.lower().startswith("env")
        else "g"
    )
    return out


def cargar_zip_espectros(zip_path: str | Path) -> dict:
    """
    Lee estructura:
      Contraeje/<Punto>/<dd-mm-aaaa>/<Variable>.csv
    Devuelve dict[(punto, fecha, variable)] = DataFrame normalizado en Hz.
    """
    zip_path = Path(zip_path)
    salida = {}

    with zipfile.ZipFile(zip_path, "r") as z:
        for nombre in z.namelist():
            if not nombre.lower().endswith(".csv"):
                continue

            partes = nombre.split("/")
            if len(partes) < 4:
                continue

            punto = partes[-3]
            fecha = pd.to_datetime(partes[-2], dayfirst=True)
            variable = _variable_canonica(Path(partes[-1]).stem)

            df = _leer_csv_bytes(z.read(nombre))
            salida[(punto, fecha, variable)] = _normalizar_espectro(df, variable)

    return salida


def rms_espectral(df: pd.DataFrame) -> float:
    amp = df.loc[df["FrecuenciaHz"] > 0, "Amplitud"].astype(float).to_numpy()
    return float(np.sqrt(np.sum(amp ** 2))) if len(amp) else np.nan


def amplitud_cercana(df: pd.DataFrame, frecuencia_hz: float) -> tuple[float, float]:
    if df.empty:
        return np.nan, np.nan
    f = df["FrecuenciaHz"].to_numpy(dtype=float)
    a = df["Amplitud"].to_numpy(dtype=float)
    i = int(np.argmin(np.abs(f - float(frecuencia_hz))))
    return float(f[i]), float(a[i])


def picos_locales(df: pd.DataFrame, n: int = 15, min_rel: float = 0.03) -> pd.DataFrame:
    """Detector ligero de máximos locales, sin dependencia de scipy."""
    f = df["FrecuenciaHz"].to_numpy(dtype=float)
    a = df["Amplitud"].to_numpy(dtype=float)

    if len(a) < 3:
        return pd.DataFrame(columns=["FrecuenciaHz", "Amplitud"])

    maxamp = float(np.max(a))
    threshold = maxamp * float(min_rel)
    inds = []

    for i in range(1, len(a) - 1):
        if a[i] >= a[i - 1] and a[i] > a[i + 1] and a[i] >= threshold:
            inds.append(i)

    inds = sorted(inds, key=lambda i: a[i], reverse=True)[:int(n)]
    return pd.DataFrame({
        "FrecuenciaHz": [float(f[i]) for i in inds],
        "Amplitud": [float(a[i]) for i in inds],
    })


def energia_banda(df: pd.DataFrame, fmin: float, fmax: float) -> float:
    m = (
        df["FrecuenciaHz"].ge(float(fmin))
        & df["FrecuenciaHz"].lt(float(fmax))
    )
    a = df.loc[m, "Amplitud"].astype(float).to_numpy()
    return float(np.sqrt(np.sum(a ** 2))) if len(a) else 0.0


def resumen_historial(espectros: dict) -> pd.DataFrame:
    filas = []
    for (punto, fecha, variable), df in espectros.items():
        picos = picos_locales(df, n=1, min_rel=0.02)
        filas.append({
            "Punto": punto,
            "Fecha": fecha,
            "Variable": variable,
            "RMS_Espectral": rms_espectral(df),
            "PicoHz": (
                float(picos.iloc[0]["FrecuenciaHz"])
                if not picos.empty else np.nan
            ),
            "PicoAmplitud": (
                float(picos.iloc[0]["Amplitud"])
                if not picos.empty else np.nan
            ),
            "FmaxHz": float(df["FrecuenciaHz"].max()),
            "ResolucionHz": float(np.median(np.diff(df["FrecuenciaHz"]))),
        })
    return (
        pd.DataFrame(filas)
        .sort_values(["Punto", "Variable", "Fecha"])
        .reset_index(drop=True)
    )


def familia_armonica(
    df: pd.DataFrame,
    fundamental_hz: float,
    max_armonico: int = 10,
    incluir_vecinos: bool = True,
) -> pd.DataFrame:
    """
    Rastrea una familia n*f0. Si incluir_vecinos=True integra ±1 bin para
    capturar energía distribuida/sidebands inmediatamente adyacentes.
    """
    f = df["FrecuenciaHz"].to_numpy(dtype=float)
    a = df["Amplitud"].to_numpy(dtype=float)
    resolucion = float(np.median(np.diff(f))) if len(f) > 1 else 0.0

    filas = []
    for n in range(1, int(max_armonico) + 1):
        target = float(fundamental_hz) * n
        if incluir_vecinos:
            m = np.abs(f - target) <= resolucion + 1e-9
            energia = float(np.sqrt(np.sum(a[m] ** 2))) if np.any(m) else 0.0
            i = int(np.argmin(np.abs(f - target)))
            amp_central = float(a[i])
            freq_real = float(f[i])
        else:
            i = int(np.argmin(np.abs(f - target)))
            energia = float(a[i])
            amp_central = float(a[i])
            freq_real = float(f[i])

        filas.append({
            "Armonico": n,
            "ObjetivoHz": target,
            "FrecuenciaHz": freq_real,
            "AmplitudCentral": amp_central,
            "EnergiaLocal": energia,
        })

    return pd.DataFrame(filas)


def comparar_periodos(
    espectros: dict,
    punto: str,
    variable: str,
    n_base: int = 2,
    n_reciente: int = 3,
) -> pd.DataFrame:
    """
    Compara promedio de las primeras n_base fechas contra las últimas n_reciente
    en cada línea espectral común.
    """
    claves = sorted(
        [
            k for k in espectros
            if k[0] == punto and k[2].lower() == variable.lower()
        ],
        key=lambda k: k[1],
    )

    if len(claves) < max(n_base, n_reciente):
        return pd.DataFrame()

    dfs = [espectros[k] for k in claves]
    grid = dfs[0]["FrecuenciaHz"].to_numpy(dtype=float)

    amps = []
    for df in dfs:
        f = df["FrecuenciaHz"].to_numpy(dtype=float)
        a = df["Amplitud"].to_numpy(dtype=float)
        if len(f) == len(grid) and np.allclose(f, grid, rtol=1e-6, atol=1e-6):
            amps.append(a)
        else:
            amps.append(np.interp(grid, f, a))

    A = np.vstack(amps)
    base = A[:n_base].mean(axis=0)
    recent = A[-n_reciente:].mean(axis=0)

    ratio = np.divide(
        recent,
        base,
        out=np.full_like(recent, np.nan),
        where=base > max(float(np.max(base)) * 0.01, 1e-12),
    )

    return pd.DataFrame({
        "FrecuenciaHz": grid,
        "BasePromedio": base,
        "RecientePromedio": recent,
        "CambioAbsoluto": recent - base,
        "Ratio": ratio,
    })


def diagnostico_preliminar_contraeje(espectros: dict) -> dict:
    """
    Resumen cuantitativo inicial para 3V y 4H.
    No asigna GMF hasta contar con RPM y dientes.
    """
    resumen = resumen_historial(espectros)
    salida = {"resumen": resumen}

    for punto in ("3V", "4H"):
        q = resumen[
            (resumen["Punto"] == punto)
            & (resumen["Variable"].str.lower() == "velocidad")
        ].sort_values("Fecha")

        if len(q) >= 2:
            base = float(q.head(2)["RMS_Espectral"].mean())
            latest = float(q.iloc[-1]["RMS_Espectral"])
            salida[f"{punto}_vel_base"] = base
            salida[f"{punto}_vel_latest"] = latest
            salida[f"{punto}_vel_cambio_pct"] = (
                100.0 * (latest / base - 1.0) if base > 0 else np.nan
            )

    return salida



def _variable_canonica(nombre: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", str(nombre))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower().strip()
    if s.startswith("vel"):
        return "Velocidad"
    if s.startswith("acel"):
        return "Aceleración"
    if s.startswith("env"):
        return "Envolvente"
    return str(nombre).strip()


def cargar_directorio_espectros(base_dir: str | Path) -> dict:
    """
    Lee carpetas del tipo:
      <base>/<Punto>/<dd-mm-aaaa>/<Velocidad|Aceleración|Envolvente>.csv

    Devuelve dict[(punto, fecha, variable)] = DataFrame normalizado en Hz.
    """
    base_dir = Path(base_dir)
    salida = {}
    if not base_dir.exists():
        return salida

    for archivo in sorted(base_dir.rglob("*.csv")):
        try:
            rel = archivo.relative_to(base_dir)
        except ValueError:
            continue
        partes = rel.parts
        if len(partes) < 3:
            continue
        punto = partes[-3]
        try:
            fecha = pd.to_datetime(partes[-2], dayfirst=True)
        except Exception:
            continue
        variable = _variable_canonica(archivo.stem)
        try:
            raw = archivo.read_bytes()
            df = _leer_csv_bytes(raw)
            salida[(punto, fecha, variable)] = _normalizar_espectro(df, variable)
        except Exception:
            continue
    return salida


def espectro_por_clave(espectros: dict, punto: str, fecha, variable: str) -> pd.DataFrame:
    fecha = pd.to_datetime(fecha)
    return espectros.get((punto, fecha, _variable_canonica(variable)), pd.DataFrame()).copy()


def evolucion_rms(espectros: dict, punto: str, variable: str) -> pd.DataFrame:
    variable = _variable_canonica(variable)
    filas = []
    for (p, fecha, var), df in espectros.items():
        if p == punto and _variable_canonica(var) == variable:
            filas.append({"Fecha": fecha, "RMS_Espectral": rms_espectral(df)})
    return pd.DataFrame(filas).sort_values("Fecha").reset_index(drop=True) if filas else pd.DataFrame()


def matriz_evolucion(espectros: dict, punto: str, variable: str):
    """Retorna frecuencia común, fechas y matriz de amplitudes para heatmap."""
    variable = _variable_canonica(variable)
    claves = sorted(
        [k for k in espectros if k[0] == punto and _variable_canonica(k[2]) == variable],
        key=lambda k: k[1],
    )
    if not claves:
        return np.array([]), [], np.empty((0,0))
    base = espectros[claves[0]]
    grid = base["FrecuenciaHz"].to_numpy(dtype=float)
    filas=[]
    fechas=[]
    for k in claves:
        df=espectros[k]
        f=df["FrecuenciaHz"].to_numpy(dtype=float)
        a=df["Amplitud"].to_numpy(dtype=float)
        if len(f)==len(grid) and np.allclose(f,grid,rtol=1e-7,atol=1e-8):
            vals=a
        else:
            vals=np.interp(grid,f,a)
        filas.append(vals)
        fechas.append(k[1])
    return grid, fechas, np.vstack(filas)


def unidad_amplitud(variable: str) -> str:
    v=_variable_canonica(variable)
    return {"Velocidad":"mm/s","Aceleración":"g","Envolvente":"gE"}.get(v,"")


def resumen_comparativo(espectros: dict, punto: str, variable: str, fecha_actual=None, fecha_ref=None) -> dict:
    variable=_variable_canonica(variable)
    claves=sorted([k for k in espectros if k[0]==punto and _variable_canonica(k[2])==variable],key=lambda k:k[1])
    if not claves:
        return {}
    fechas=[k[1] for k in claves]
    if fecha_actual is None:
        fecha_actual=fechas[-1]
    if fecha_ref is None:
        fecha_ref=fechas[0]
    fecha_actual=pd.to_datetime(fecha_actual)
    fecha_ref=pd.to_datetime(fecha_ref)
    da=espectros.get((punto,fecha_actual,variable))
    dr=espectros.get((punto,fecha_ref,variable))
    if da is None or dr is None:
        return {}
    rms_a=rms_espectral(da); rms_r=rms_espectral(dr)
    picos=picos_locales(da,n=10,min_rel=.03)
    peak_hz=float(picos.iloc[0]["FrecuenciaHz"]) if not picos.empty else np.nan
    peak_amp=float(picos.iloc[0]["Amplitud"]) if not picos.empty else np.nan
    return {
        "fecha_actual":fecha_actual,
        "fecha_ref":fecha_ref,
        "rms_actual":rms_a,
        "rms_ref":rms_r,
        "cambio_pct":100*(rms_a/rms_r-1) if rms_r>0 else np.nan,
        "pico_hz":peak_hz,
        "pico_amp":peak_amp,
        "unidad":unidad_amplitud(variable),
        "picos":picos,
    }


# Datos mecánicos estructurados SOLO para Molino 1A y Molino 1.
# Molino 1 queda preparado sin inventar valores hasta contar con su ficha real.
DATOS_MECANICOS = {
    "Molino 1A": {
        "TAG": "MOL-RD08-YA",
        "PotenciaHP": 800.0,
        "RPMContraeje": 240.0,
        "DientesPinion": 19,
        "DientesCatalina": 293,
        "RodamientoLA": "22244CC",
        "RodamientoLL": "22244CC",
        "PuntoLA": "3",
        "PuntoLL": "4",
    },
    "Molino 1": {
        "TAG": "MOL-RD01-YA",
        "PotenciaHP": None,
        "RPMContraeje": None,
        "DientesPinion": None,
        "DientesCatalina": None,
        "RodamientoLA": None,
        "RodamientoLL": None,
        "PuntoLA": None,
        "PuntoLL": None,
    },
}


def datos_mecanicos_equipo(equipo: str) -> dict:
    return dict(DATOS_MECANICOS.get(equipo, {}))


def _serie_variable(espectros: dict, punto: str, variable: str):
    var = _variable_canonica(variable)
    claves = sorted(
        [k for k in espectros if k[0] == punto and _variable_canonica(k[2]) == var],
        key=lambda k: k[1],
    )
    return [(k[1], espectros[k]) for k in claves]


def _amp_local(df: pd.DataFrame, objetivo_hz: float, bins: int = 1):
    if df.empty:
        return np.nan, np.nan, np.nan
    f = df["FrecuenciaHz"].to_numpy(dtype=float)
    a = df["Amplitud"].to_numpy(dtype=float)
    i = int(np.argmin(np.abs(f - float(objetivo_hz))))
    lo = max(0, i - int(bins))
    hi = min(len(a), i + int(bins) + 1)
    energia = float(np.sqrt(np.sum(a[lo:hi] ** 2)))
    return float(f[i]), float(a[i]), energia


def metricas_engranaje(
    espectros: dict,
    punto: str = "4H",
    rpm: float = 240.0,
    dientes_pinion: int = 19,
    dientes_catalina: int = 293,
    n_base: int = 2,
) -> dict:
    """
    Evalúa GMF, armónicos 1–4 y sidebands ±1X alrededor de cada armónico.
    Usa velocidad RMS espectral. No confunde el resultado con severidad ISO.
    """
    f1 = float(rpm) / 60.0
    gmf = f1 * int(dientes_pinion)
    rpm_catalina = float(rpm) * int(dientes_pinion) / int(dientes_catalina)

    serie = _serie_variable(espectros, punto, "Velocidad")
    if not serie:
        return {}

    filas = []
    for fecha, df in serie:
        harm = []
        side = []
        for n in range(1, 5):
            _, _, ec = _amp_local(df, n * gmf, bins=1)
            _, _, em = _amp_local(df, n * gmf - f1, bins=1)
            _, _, ep = _amp_local(df, n * gmf + f1, bins=1)
            harm.append(ec)
            side.append(math.sqrt(em ** 2 + ep ** 2))
        filas.append({
            "Fecha": pd.to_datetime(fecha),
            "GMF_RSS": float(np.sqrt(np.sum(np.asarray(harm) ** 2))),
            "Sideband1X_RSS": float(np.sqrt(np.sum(np.asarray(side) ** 2))),
        })

    hist = pd.DataFrame(filas).sort_values("Fecha")
    base = hist.head(max(1, int(n_base)))
    latest = hist.iloc[-1]

    gmf_base = float(base["GMF_RSS"].mean())
    sb_base = float(base["Sideband1X_RSS"].mean())
    gmf_latest = float(latest["GMF_RSS"])
    sb_latest = float(latest["Sideband1X_RSS"])

    return {
        "f1_hz": f1,
        "gmf_hz": gmf,
        "rpm_catalina": rpm_catalina,
        "gmf_harm_base": gmf_base,
        "gmf_harm_latest": gmf_latest,
        "gmf_harm_growth_pct": 100.0 * (gmf_latest / gmf_base - 1.0) if gmf_base > 0 else np.nan,
        "sideband_base": sb_base,
        "sideband_latest": sb_latest,
        "sideband_growth_pct": 100.0 * (sb_latest / sb_base - 1.0) if sb_base > 0 else np.nan,
        "historial": hist,
    }


def metricas_familia_candidata_rodamiento(
    espectros: dict,
    punto: str = "4H",
    rpm: float = 240.0,
    frecuencia_candidata_hz: float = 30.800216666666664,
    n_armonicos: int = 10,
    n_base: int = 2,
) -> dict:
    """
    Rastrea una familia no sincrónica observada en envolvente y velocidad.
    NO la etiqueta BPFO/BPFI sin factores exactos del rodamiento.
    """
    f1 = float(rpm) / 60.0
    orden = float(frecuencia_candidata_hz) / f1 if f1 > 0 else np.nan

    salida = {
        "frecuencia_hz": float(frecuencia_candidata_hz),
        "orden_x": orden,
    }

    for variable in ("Velocidad", "Aceleración", "Envolvente"):
        serie = _serie_variable(espectros, punto, variable)
        filas = []
        for fecha, df in serie:
            energias = []
            presentes = 0
            maxamp = float(df["Amplitud"].max()) if not df.empty else 0.0
            for n in range(1, int(n_armonicos) + 1):
                _, amp, energia = _amp_local(df, frecuencia_candidata_hz * n, bins=1)
                energias.append(energia)
                if maxamp > 0 and amp >= maxamp * 0.05:
                    presentes += 1
            filas.append({
                "Fecha": pd.to_datetime(fecha),
                "FamiliaRSS": float(np.sqrt(np.sum(np.asarray(energias) ** 2))),
                "ArmonicosPresentes": int(presentes),
            })

        hist = pd.DataFrame(filas).sort_values("Fecha") if filas else pd.DataFrame()
        if hist.empty:
            continue

        base = float(hist.head(max(1, int(n_base)))["FamiliaRSS"].mean())
        latest = float(hist.iloc[-1]["FamiliaRSS"])
        salida[f"{variable}_base"] = base
        salida[f"{variable}_latest"] = latest
        salida[f"{variable}_growth_pct"] = (
            100.0 * (latest / base - 1.0) if base > 0 else np.nan
        )
        salida[f"{variable}_armonicos"] = int(hist.iloc[-1]["ArmonicosPresentes"])
        salida[f"{variable}_historial"] = hist

    return salida


def _cambio_rms(espectros: dict, punto: str, variable: str, n_base: int = 2):
    evo = evolucion_rms(espectros, punto, variable)
    if evo.empty:
        return np.nan
    base = float(evo.head(max(1, int(n_base)))["RMS_Espectral"].mean())
    latest = float(evo.iloc[-1]["RMS_Espectral"])
    return 100.0 * (latest / base - 1.0) if base > 0 else np.nan


def _energia_banda_historial(
    espectros: dict,
    punto: str,
    variable: str,
    fmin: float,
    fmax: float,
    n_base: int = 2,
):
    serie = _serie_variable(espectros, punto, variable)
    if not serie:
        return np.nan
    vals = [
        (pd.to_datetime(fecha), energia_banda(df, fmin, fmax))
        for fecha, df in serie
    ]
    hist = pd.DataFrame(vals, columns=["Fecha", "Energia"]).sort_values("Fecha")
    base = float(hist.head(max(1, int(n_base)))["Energia"].mean())
    latest = float(hist.iloc[-1]["Energia"])
    return 100.0 * (latest / base - 1.0) if base > 0 else np.nan


def diagnostico_contraeje_molino1a(espectros: dict) -> dict:
    """
    Motor determinístico de evidencia física.
    Compara tres hipótesis: engranaje, rodamiento LL y soltura/holgura.
    No usa una red neuronal ni fuerza una causa única.
    """
    datos = datos_mecanicos_equipo("Molino 1A")
    rpm = float(datos["RPMContraeje"])
    gear = metricas_engranaje(
        espectros,
        punto="4H",
        rpm=rpm,
        dientes_pinion=int(datos["DientesPinion"]),
        dientes_catalina=int(datos["DientesCatalina"]),
    )
    bearing = metricas_familia_candidata_rodamiento(
        espectros, punto="4H", rpm=rpm
    )

    vel4 = _cambio_rms(espectros, "4H", "Velocidad")
    vel3 = _cambio_rms(espectros, "3V", "Velocidad")
    env4 = _cambio_rms(espectros, "4H", "Envolvente")
    acc100_300 = _energia_banda_historial(
        espectros, "4H", "Aceleración", 100.0, 300.0
    )

    # ---- Engranaje ----
    s_gear = 0
    evid_gear = []
    if gear:
        if gear["gmf_harm_growth_pct"] >= 50:
            s_gear += 30
            evid_gear.append(
                f"Armónicos de GMF crecen {gear['gmf_harm_growth_pct']:+.0f}%"
            )
        if gear["sideband_growth_pct"] >= 100:
            s_gear += 30
            evid_gear.append(
                f"Bandas laterales ±1X alrededor de GMF crecen {gear['sideband_growth_pct']:+.0f}%"
            )
    if np.isfinite(acc100_300) and acc100_300 >= 100:
        s_gear += 20
        evid_gear.append(
            f"Energía de aceleración 100–300 Hz crece {acc100_300:+.0f}%"
        )
    if np.isfinite(vel4) and np.isfinite(vel3) and vel4 - vel3 >= 100:
        s_gear += 20
        evid_gear.append("El cambio está localizado en 4H respecto a 3V")
    s_gear = min(s_gear, 100)

    # ---- Rodamiento lado libre ----
    s_brg = 0
    evid_brg = []
    env_family = bearing.get("Envolvente_growth_pct", np.nan)
    env_harm = bearing.get("Envolvente_armonicos", 0)
    if np.isfinite(env4) and env4 >= 30:
        s_brg += 20
        evid_brg.append(f"RMS de envolvente 4H crece {env4:+.0f}%")
    if np.isfinite(env_family) and env_family >= 50:
        s_brg += 30
        evid_brg.append(
            f"Familia 30.8 Hz en envolvente crece {env_family:+.0f}%"
        )
    if int(env_harm) >= 4:
        s_brg += 20
        evid_brg.append(
            f"Familia no sincrónica presenta {int(env_harm)} armónicos relevantes"
        )
    orden = bearing.get("orden_x", np.nan)
    if np.isfinite(orden) and abs(orden - round(orden)) >= 0.10:
        s_brg += 10
        evid_brg.append(f"Frecuencia candidata = {orden:.2f}X, no sincrónica con el eje")
    # Sin BPFO/BPFI exactos, se limita la certeza.
    s_brg = min(s_brg, 65)

    # ---- Soltura / holgura ----
    # Se usa como hipótesis secundaria: una familia extensa de armónicos y
    # crecimiento localizado puede verse amplificada por juego o pérdida de rigidez.
    s_loose = 0
    evid_loose = []
    fam_vel = bearing.get("Velocidad_growth_pct", np.nan)
    if np.isfinite(fam_vel) and fam_vel >= 200:
        s_loose += 20
        evid_loose.append("Familia extensa de armónicos en velocidad")
    if np.isfinite(vel4) and np.isfinite(vel3) and vel4 - vel3 >= 100:
        s_loose += 15
        evid_loose.append("Respuesta localizada en el apoyo 4H")
    if gear and gear["sideband_growth_pct"] >= 200:
        s_loose += 10
        evid_loose.append("Modulación intensa que puede amplificarse por juego mecánico")
    s_loose = min(s_loose, 45)

    def nivel(score, cap=False):
        if score >= 75:
            return "Alta"
        if score >= 50:
            return "Media"
        return "Baja"

    hipotesis = [
        {
            "Hipotesis": "Engranaje piñón–catalina",
            "Puntaje": int(round(s_gear)),
            "Confianza": nivel(s_gear),
            "Evidencias": evid_gear,
        },
        {
            "Hipotesis": "Rodamiento lado libre 22244CC",
            "Puntaje": int(round(s_brg)),
            "Confianza": nivel(s_brg),
            "Evidencias": evid_brg,
        },
        {
            "Hipotesis": "Soltura / holgura mecánica",
            "Puntaje": int(round(s_loose)),
            "Confianza": nivel(s_loose),
            "Evidencias": evid_loose,
        },
    ]
    hipotesis.sort(key=lambda x: x["Puntaje"], reverse=True)

    return {
        "datos_mecanicos": datos,
        "engranaje": gear,
        "rodamiento": bearing,
        "cambio_vel_4H_pct": vel4,
        "cambio_vel_3V_pct": vel3,
        "cambio_env_4H_pct": env4,
        "cambio_acc_100_300_pct": acc100_300,
        "hipotesis": hipotesis,
        "principal": hipotesis[0] if hipotesis else None,
        "nota_rodamiento": (
            "La familia 30.8 Hz equivale aproximadamente a 7.70X del eje y aparece con "
            "armónicos en envolvente. Es compatible con una frecuencia candidata de rodamiento, "
            "pero no se etiqueta BPFO/BPFI hasta disponer de factores geométricos o frecuencias "
            "de defecto verificadas del 22244CC."
        ),
    }
