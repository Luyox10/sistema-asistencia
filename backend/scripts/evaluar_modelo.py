"""Evalúa el modelo LSTM sobre un dataset con split temporal.

Para cada par (student_id, course_id) se construyen ventanas de VENTANA
asistencias y la etiqueta es la asistencia de la sesión siguiente. El
20% más reciente de las fechas del dataset actúa como conjunto de prueba
(las características siempre son anteriores a la etiqueta: sin fuga de
datos futuros). Escribe las métricas reales en models/metricas_modelo.json.

Uso (desde backend/):
    .\\venv\\Scripts\\python.exe scripts\\evaluar_modelo.py [ruta_csv]
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from app.services.dataset_service import cargar_y_validar  # noqa: E402
from app.services.prediction_service import UMBRAL, VENTANA, get_model  # noqa: E402

_BACKEND = Path(__file__).resolve().parents[1]
_DATA_DEFAULT = _BACKEND.parent / "data" / "dataset_institucion_demo.csv"
_METRICAS = _BACKEND / "models" / "metricas_modelo.json"
_PROPORCION_TEST = 0.2


def construir_muestras(df):
    """Ventanas de VENTANA valores -> etiqueta siguiente, por par
    (student_id, course_id) ordenado por fecha. Devuelve también la fecha
    de la etiqueta para el split temporal."""
    X, y, fechas_y = [], [], []
    for (_, _), grupo in df.groupby(["student_id", "course_id"]):
        grupo = grupo.sort_values("session_date")
        vals = grupo.attendance_status.to_numpy()
        fechas = grupo.session_date.to_numpy()
        for i in range(len(vals) - VENTANA):
            X.append(vals[i : i + VENTANA])
            y.append(int(vals[i + VENTANA]))
            fechas_y.append(fechas[i + VENTANA])
    X = np.array(X, dtype=np.float32).reshape(-1, VENTANA, 1)
    return X, np.array(y), np.array(fechas_y)


def main() -> int:
    ruta_csv = Path(sys.argv[1]) if len(sys.argv) > 1 else _DATA_DEFAULT
    if not ruta_csv.exists():
        print(f"ERROR: no existe el dataset {ruta_csv}")
        return 1

    df, _ = cargar_y_validar(ruta_csv.read_bytes(), ruta_csv.name)
    X, y, fechas_y = construir_muestras(df)
    if len(y) == 0:
        print("ERROR: no hay suficientes registros para formar ventanas")
        return 1

    corte = np.quantile(fechas_y.astype("datetime64[D]").astype(int), 1 - _PROPORCION_TEST)
    mascara_test = fechas_y.astype("datetime64[D]").astype(int) >= corte
    if mascara_test.sum() == 0:
        print("ERROR: el conjunto de prueba quedó vacío")
        return 1

    probs = get_model().predict(X[mascara_test], verbose=0).ravel()
    pred = (probs >= UMBRAL).astype(int)
    y_test = y[mascara_test].astype(int)

    tp = int(((pred == 1) & (y_test == 1)).sum())
    tn = int(((pred == 0) & (y_test == 0)).sum())
    fp = int(((pred == 1) & (y_test == 0)).sum())
    fn = int(((pred == 0) & (y_test == 1)).sum())

    accuracy = (tp + tn) / len(y_test)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    # ROC-AUC por el método de rangos (Mann–Whitney U)
    orden = probs.argsort()
    rangos = np.empty(len(probs))
    rangos[orden] = np.arange(1, len(probs) + 1)
    n_pos, n_neg = int(y_test.sum()), int((y_test == 0).sum())
    roc_auc = (
        (rangos[y_test == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
        if n_pos and n_neg
        else float("nan")
    )

    metricas = {
        "evaluado": True,
        "fecha_evaluacion": datetime.now(timezone.utc).isoformat(),
        "dataset": ruta_csv.name,
        "metodo": (
            "Split temporal: ventanas cuyo objetivo cae en el "
            f"{int(_PROPORCION_TEST * 100)}% mas reciente de fechas"
        ),
        "muestras_test": int(mascara_test.sum()),
        "ventana": VENTANA,
        "umbral": UMBRAL,
        "accuracy": round(float(accuracy), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(roc_auc), 4),
        "matriz_confusion": {
            "verdaderos_positivos": tp,
            "verdaderos_negativos": tn,
            "falsos_positivos": fp,
            "falsos_negativos": fn,
        },
    }

    with open(_METRICAS, "w", encoding="utf-8") as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2)

    print(f"Dataset: {ruta_csv.name} | muestras test: {metricas['muestras_test']}")
    for k in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        print(f"  {k}: {metricas[k]}")
    print(f"Métricas escritas en {_METRICAS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
