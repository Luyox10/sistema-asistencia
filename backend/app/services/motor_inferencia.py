"""Motor de inferencia del sistema experto híbrido.

Combina la salida del modelo LSTM (probabilidad de asistencia) con hechos
derivados del historial reciente (ausencias en la ventana, racha
consecutiva y tendencia) y evalúa las reglas IF-THEN declaradas en
``models/base_conocimientos.json``. Las reglas se evalúan en orden de
prioridad: la primera que cumple todas sus condiciones define la
conclusión; el resto de reglas activadas se reportan para explicabilidad.
"""

import json
import operator
import threading
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_BASE_PATH = _BACKEND_DIR / "models" / "base_conocimientos.json"

_OPERADORES = {
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
    "==": operator.eq,
    "!=": operator.ne,
}

_kb = None
_lock = threading.Lock()


class BaseConocimientosError(Exception):
    """La base de conocimientos no existe o está mal formada."""


def base_conocimientos() -> dict:
    """Carga perezosa y thread-safe de la base de conocimientos."""
    global _kb
    if _kb is None:
        with _lock:
            if _kb is None:
                if not _BASE_PATH.exists():
                    raise BaseConocimientosError(
                        f"No existe la base de conocimientos: {_BASE_PATH}"
                    )
                try:
                    with open(_BASE_PATH, encoding="utf-8") as f:
                        kb = json.load(f)
                except Exception as exc:
                    raise BaseConocimientosError(
                        f"Error al leer la base de conocimientos: {exc}"
                    ) from exc
                for regla in kb.get("reglas", []):
                    for cond in regla.get("condiciones", []):
                        if cond["operador"] not in _OPERADORES:
                            raise BaseConocimientosError(
                                f"Operador no soportado en {regla['id']}: "
                                f"{cond['operador']}"
                            )
                _kb = kb
    return _kb


def calcular_hechos(historial: list[int], probabilidad: float) -> dict:
    """Deriva los hechos a partir de la ventana de asistencias y la
    probabilidad del modelo. ``historial`` son los últimos 7 valores
    (0 = falta, 1 = asistió) en orden cronológico."""
    ausencias = historial.count(0)

    racha = 0
    for v in reversed(historial):
        if v == 0:
            racha += 1
        else:
            break

    mitad = len(historial) // 2
    tasa_antes = sum(historial[:mitad]) / mitad
    tasa_despues = sum(historial[mitad:]) / (len(historial) - mitad)
    if tasa_despues < tasa_antes:
        tendencia = "empeorando"
    elif tasa_despues > tasa_antes:
        tendencia = "mejorando"
    else:
        tendencia = "estable"

    return {
        "probabilidad": probabilidad,
        "ausencias_ultimas": ausencias,
        "racha_ausencias": racha,
        "tendencia": tendencia,
        "porcentaje_asistencia": round(sum(historial) / len(historial), 4),
    }


def _cumple(condicion: dict, hechos: dict) -> bool:
    campo, op, valor = condicion["campo"], condicion["operador"], condicion["valor"]
    if campo not in hechos:
        return False
    return _OPERADORES[op](hechos[campo], valor)


def evaluar(hechos: dict) -> dict:
    """Evalúa las reglas sobre los hechos. Devuelve la conclusión de la
    regla de mayor prioridad que se activa, la lista de todas las reglas
    activadas y los hechos usados."""
    activadas = []
    regla_default = None
    conclusion = None
    for regla in base_conocimientos()["reglas"]:
        if all(_cumple(c, hechos) for c in regla["condiciones"]):
            if regla["condiciones"]:
                activadas.append(regla["id"])
            else:
                regla_default = regla
            if conclusion is None:
                conclusion = regla["conclusion"]
    if conclusion is None:
        raise BaseConocimientosError(
            "Ninguna regla se activó: falta la regla por defecto (condiciones vacías)"
        )
    if not activadas and regla_default is not None:
        activadas.append(regla_default["id"])
    return {
        **conclusion,
        "reglas_activadas": activadas,
        "hechos": hechos,
    }


def inferir(historial: list[int], probabilidad: float) -> dict:
    """Atajo: calcula hechos y evalúa en un solo paso."""
    return evaluar(calcular_hechos(historial, probabilidad))
