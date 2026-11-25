"""Servicio de predicción de asistencia con el modelo LSTM.

El modelo recibe una secuencia de las últimas ``ventana`` asistencias
(attendance_status ∈ {0, 1}) de un estudiante en un curso, ordenadas por
fecha de sesión, y devuelve la probabilidad de asistencia a la próxima
sesión. Solo se usan sesiones estrictamente anteriores a la sesión
objetivo: nunca se utiliza información futura ni la asistencia de la
propia sesión que se quiere predecir.
"""

import json
import threading
from pathlib import Path

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from .motor_inferencia import inferir

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class ModeloNoDisponibleError(Exception):
    """El modelo no pudo cargarse o no existe el archivo."""


class EntradaInvalidaError(Exception):
    """La entrada no cumple la forma o los valores requeridos."""


class HistorialInsuficienteError(Exception):
    """No hay suficientes sesiones previas para formar la ventana."""


def _load_config() -> dict:
    path = _BACKEND_DIR / settings.MODEL_CONFIG_PATH
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_config = _load_config()
VENTANA: int = _config["ventana"]
UMBRAL: float = _config["umbral"]

_model = None
_model_lock = threading.Lock()


def get_model():
    """Carga perezosa del modelo (singleton thread-safe)."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                path = _BACKEND_DIR / settings.MODEL_PATH
                if not path.exists():
                    raise ModeloNoDisponibleError(
                        f"No existe el archivo de modelo: {path}"
                    )
                try:
                    import keras

                    _model = keras.models.load_model(path)
                except Exception as exc:
                    raise ModeloNoDisponibleError(
                        f"Error al cargar el modelo: {exc}"
                    ) from exc
    return _model


def preparar_secuencia(historial: list[int | float]) -> np.ndarray:
    """Convierte el historial en un array (1, ventana, 1) validado."""
    if len(historial) != VENTANA:
        raise EntradaInvalidaError(
            f"Se requieren exactamente {VENTANA} valores, recibidos {len(historial)}"
        )
    for v in historial:
        if v not in (0, 1):
            raise EntradaInvalidaError(
                f"attendance_status solo admite 0 o 1, recibido: {v!r}"
            )
    return np.array(historial, dtype=np.float32).reshape(1, VENTANA, 1)


def predecir_secuencia(historial: list[int]) -> dict:
    """Predice a partir de una secuencia ya validada."""
    x = preparar_secuencia(historial)
    prob = float(get_model().predict(x, verbose=0)[0][0])
    return {
        "probabilidad": prob,
        "prediccion": int(prob >= UMBRAL),
        "umbral": UMBRAL,
    }


def obtener_historial(
    db: Session, student_id: str, course_id: str, fecha_limite
) -> list[int]:
    """Últimas `VENTANA` asistencias del estudiante en el curso, solo de
    sesiones estrictamente anteriores a `fecha_limite`, en orden
    cronológico ascendente."""
    rows = db.execute(
        text(
            """
            SELECT a.attendance_status
            FROM asistencias a
            JOIN sesiones s ON a.session_id = s.session_id
            WHERE a.student_id = :sid
              AND s.course_id = :cid
              AND s.session_date < :fecha
            ORDER BY s.session_date DESC
            LIMIT :n
            """
        ),
        {"sid": student_id, "cid": course_id, "fecha": fecha_limite, "n": VENTANA},
    ).fetchall()
    historial = [int(r[0]) for r in rows][::-1]
    if len(historial) < VENTANA:
        raise HistorialInsuficienteError(
            f"Solo hay {len(historial)} sesiones previas; se necesitan {VENTANA}"
        )
    return historial


def predecir_asistencia(
    db: Session, student_id: str, course_id: str, session_id: str
) -> dict:
    """Predice la asistencia de un estudiante a una sesión futura.

    Lanza EntradaInvalidaError si la sesión no existe, no pertenece al
    curso o ya tiene una asistencia registrada para ese estudiante.
    """
    sesion = db.execute(
        text("SELECT course_id, session_date FROM sesiones WHERE session_id = :sid"),
        {"sid": session_id},
    ).fetchone()
    if sesion is None:
        raise EntradaInvalidaError(f"Sesión no encontrada: {session_id}")
    if sesion[0] != course_id:
        raise EntradaInvalidaError(
            f"La sesión {session_id} no pertenece al curso {course_id}"
        )
    fecha_sesion = sesion[1]

    ya_registrada = db.execute(
        text(
            "SELECT 1 FROM asistencias WHERE student_id = :sid AND session_id = :ses"
        ),
        {"sid": student_id, "ses": session_id},
    ).fetchone()
    if ya_registrada is not None:
        raise EntradaInvalidaError(
            f"La asistencia de {student_id} a {session_id} ya está registrada; "
            "no es una predicción futura"
        )

    historial = obtener_historial(db, student_id, course_id, fecha_sesion)
    resultado = predecir_secuencia(historial)
    return {
        "student_id": student_id,
        "course_id": course_id,
        "session_id": session_id,
        "historial_usado": historial,
        **resultado,
        "experto": inferir(historial, resultado["probabilidad"]),
    }


def historial_desde_df(df, student_id: str, course_id: str, antes_de=None) -> list[int]:
    """Últimas `VENTANA` asistencias de un DataFrame de dataset, solo del
    estudiante y curso indicados y (opcionalmente) anteriores a `antes_de`.
    Misma regla que obtener_historial pero sobre datos cargados en memoria."""
    sub = df[(df.student_id == student_id) & (df.course_id == course_id)]
    if antes_de is not None:
        sub = sub[sub.session_date < antes_de]
    sub = sub.sort_values("session_date")
    historial = [int(v) for v in sub.attendance_status.tail(VENTANA)]
    if len(historial) < VENTANA:
        raise HistorialInsuficienteError(
            f"{student_id} en {course_id}: solo {len(historial)} registros; "
            f"se necesitan {VENTANA}"
        )
    return historial


def predecir_desde_df(
    df, student_id: str | None = None, course_id: str | None = None
) -> list[dict]:
    """Genera predicciones por alumno/curso directamente desde un dataset
    cargado (sin tocar la base de datos). Para cada par (student_id,
    course_id) usa sus últimas 7 asistencias y predice la próxima sesión.
    Los pares con menos de 7 registros se reportan como insuficientes."""
    pares = df[["student_id", "course_id"]].drop_duplicates()
    if student_id:
        pares = pares[pares.student_id == student_id]
    if course_id:
        pares = pares[pares.course_id == course_id]

    resultados = []
    for row in pares.itertuples(index=False):
        sid, cid = row.student_id, row.course_id
        try:
            historial = historial_desde_df(df, sid, cid)
            resultado = predecir_secuencia(historial)
            resultados.append(
                {
                    "student_id": sid,
                    "course_id": cid,
                    "estado": "ok",
                    "historial_usado": historial,
                    **resultado,
                    "experto": inferir(historial, resultado["probabilidad"]),
                }
            )
        except HistorialInsuficienteError:
            n = int(
                ((df.student_id == sid) & (df.course_id == cid)).sum()
            )
            resultados.append(
                {
                    "student_id": sid,
                    "course_id": cid,
                    "estado": "historial_insuficiente",
                    "registros": n,
                }
            )
    resultados.sort(key=lambda r: (r["student_id"], r["course_id"]))
    return resultados


def prediccion_existente(
    db: Session, student_id: str, session_id: str
) -> dict | None:
    """Devuelve la predicción almacenada para (student_id, session_id) o None."""
    row = db.execute(
        text(
            """
            SELECT prediction_id, student_id, session_id,
                   attendance_probability, predicted_status, created_at
            FROM predicciones
            WHERE student_id = :sid AND session_id = :ses
            """
        ),
        {"sid": student_id, "ses": session_id},
    ).mappings().first()
    return dict(row) if row else None


def guardar_prediccion(
    db: Session, student_id: str, session_id: str, probabilidad: float, prediccion: int
) -> dict:
    """Inserta el resultado en la tabla predicciones. No duplica: si ya
    existe una fila para (student_id, session_id) la devuelve tal cual."""
    existente = prediccion_existente(db, student_id, session_id)
    if existente is not None:
        return existente
    db.execute(
        text(
            """
            INSERT INTO predicciones
                (student_id, session_id, attendance_probability, predicted_status)
            VALUES (:sid, :ses, :prob, :pred)
            """
        ),
        {"sid": student_id, "ses": session_id, "prob": probabilidad, "pred": prediccion},
    )
    db.commit()
    return prediccion_existente(db, student_id, session_id)
