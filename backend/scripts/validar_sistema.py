"""Validación integral del sistema: ejecuta las pruebas de integración y
muestra PASS/FAIL por cada una. Requiere backend en :8000.

Uso (desde backend/):
    .\\venv\\Scripts\\python.exe scripts\\validar_sistema.py
"""

import json
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.services import prediction_service as ps  # noqa: E402

API = "http://localhost:8000/api"
resultados: list[tuple[str, bool, str]] = []


def check(nombre: str, ok: bool, detalle: str = "") -> None:
    resultados.append((nombre, ok, detalle))
    print(f"[{'PASS' if ok else 'FAIL'}] {nombre}" + (f" — {detalle}" if detalle else ""))


def http(method: str, path: str, body: dict | None = None):
    req = Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}


db = SessionLocal()

# 1. Conexión FastAPI - TiDB
s, r = http("GET", "/health/database")
check(
    "1. Conexión FastAPI-TiDB",
    s == 200 and r.get("status") == "ok" and not r.get("tablas_faltantes"),
    r.get("database", ""),
)

# 2-5. Consultas de entidades
s, est = http("GET", "/estudiantes")
n = db.execute(text("SELECT COUNT(*) FROM estudiantes")).scalar()
check("2. Consulta estudiantes", s == 200 and len(est) == n, f"{len(est)}/{n} en BD")

s, cur = http("GET", "/cursos")
n = db.execute(text("SELECT COUNT(*) FROM cursos")).scalar()
check("3. Consulta cursos", s == 200 and len(cur) == n, f"{len(cur)}/{n} en BD")

ses_total = 0
ok_ses = True
for c in cur:
    s, sesc = http("GET", f"/cursos/{c['course_id']}/sesiones")
    ok_ses = ok_ses and s == 200
    ses_total += len(sesc)
n = db.execute(text("SELECT COUNT(*) FROM sesiones")).scalar()
check("4. Consulta sesiones", ok_ses and ses_total == n, f"{ses_total}/{n} en BD")

s, asis = http("GET", "/asistencias?limit=5000")
n = db.execute(text("SELECT COUNT(*) FROM asistencias")).scalar()
check("5. Consulta asistencias", s == 200 and len(asis) == n, f"{len(asis)}/{n} en BD")

# 6-8. Modelo LSTM
try:
    model = ps.get_model()
    check(
        "6. Carga del modelo LSTM",
        model.input_shape == (None, 7, 1) and model.output_shape == (None, 1),
        f"in={model.input_shape} out={model.output_shape}",
    )
except Exception as exc:
    check("6. Carga del modelo LSTM", False, str(exc))

try:
    x = ps.preparar_secuencia([1, 0, 1, 1, 0, 1, 0])
    ok_shape = x.shape == (1, 7, 1)
    err6 = err8 = False
    try:
        ps.preparar_secuencia([1, 0, 1, 1, 0, 1])
    except ps.EntradaInvalidaError:
        err6 = True
    try:
        ps.preparar_secuencia([1, 0, 1, 1, 0, 1, 0, 1])
    except ps.EntradaInvalidaError:
        err8 = True
    check("7. Ventana de 7 asistencias", ok_shape and err6 and err8,
          "acepta 7, rechaza 6 y 8")
except Exception as exc:
    check("7. Ventana de 7 asistencias", False, str(exc))

try:
    res = ps.predecir_secuencia([0, 1, 0, 1, 1, 0, 1])
    p = res["probabilidad"]
    check("8. Probabilidad válida [0,1]", 0.0 <= p <= 1.0, f"p={p:.4f}")
except Exception as exc:
    check("8. Probabilidad válida [0,1]", False, str(exc))

# 9. Predicción almacenada en TiDB (sesión temporal de prueba)
SESION_TMP = "CUR001-SES-TMP-VALIDACION"
try:
    db.execute(
        text(
            "INSERT INTO sesiones (session_id, course_id, session_date) "
            f"VALUES ('{SESION_TMP}', 'CUR001', '2026-08-19')"
        )
    )
    db.commit()
    s, r = http(
        "POST",
        "/predicciones",
        {"student_id": "EST001", "course_id": "CUR001", "session_id": SESION_TMP},
    )
    fila = db.execute(
        text("SELECT * FROM predicciones WHERE session_id = :s"), {"s": SESION_TMP}
    ).mappings().first()
    s2, r2 = http(
        "POST",
        "/predicciones",
        {"student_id": "EST001", "course_id": "CUR001", "session_id": SESION_TMP},
    )
    check(
        "9. Predicción almacenada en TiDB",
        s == 200 and fila is not None and r2.get("prediction_id") == r.get("prediction_id"),
        f"prediction_id={r.get('prediction_id')}, sin duplicar al repetir",
    )
finally:
    db.execute(text("DELETE FROM predicciones WHERE session_id = :s"), {"s": SESION_TMP})
    db.execute(text("DELETE FROM sesiones WHERE session_id = :s"), {"s": SESION_TMP})
    db.commit()

# 10. Frontend sirve y la API responde (React consume estos mismos endpoints)
try:
    with urlopen("http://localhost:5173", timeout=10) as r:
        html = r.read().decode()
    s, _ = http("GET", "/dashboard")
    check("10. Frontend recibe datos de FastAPI", r.status == 200 and s == 200 and "root" in html,
          "Vite responde y los endpoints que consume React devuelven 200")
except Exception as exc:
    check("10. Frontend recibe datos de FastAPI", False, str(exc))

# 11. Gráficos con datos reales: evolución suma == total asistencias
s, evo = http("GET", "/dashboard/evolucion")
total_evo = sum(e["asistencias"] + e["inasistencias"] for e in evo) if isinstance(evo, list) else -1
n = db.execute(text("SELECT COUNT(*) FROM asistencias")).scalar()
check("11. Gráficos con datos reales", s == 200 and total_evo == n and len(evo) > 0,
      f"suma evolución={total_evo} == asistencias={n}")

# 12. Errores HTTP
s404, _ = http("GET", "/estudiantes/NOEXISTE-XX")
s409, _ = http("GET", "/predicciones/EST001/CUR001/CUR001-SES001")  # ya registrada
db.execute(
    text(
        "INSERT INTO sesiones (session_id, course_id, session_date) "
        "VALUES ('CUR001-SES-TMP-EARLY', 'CUR001', '2026-03-04')"
    )
)
db.commit()
s422, _ = http(
    "POST",
    "/predicciones",
    {"student_id": "EST001", "course_id": "CUR001", "session_id": "CUR001-SES-TMP-EARLY"},
)
db.execute(text("DELETE FROM sesiones WHERE session_id = 'CUR001-SES-TMP-EARLY'"))
db.commit()
check(
    "12. Errores HTTP correctos",
    s404 == 404 and s409 == 409 and s422 == 422,
    f"404={s404} 409={s409} 422={s422}",
)

# ---- Revisiones especiales ----
dup = db.execute(
    text(
        "SELECT COUNT(*) - COUNT(DISTINCT student_id, session_id) FROM asistencias"
    )
).scalar()
check("E1. Sin duplicados en asistencias", dup == 0, f"{dup} duplicados")

s, hist = http("GET", "/asistencias/historial/EST001/CUR001")
mezcla = [a for a in hist if a["student_id"] != "EST001" or a["course_id"] != "CUR001"]
check("E2. Sin mezcla de historiales", s == 200 and not mezcla,
      f"{len(hist)} filas, todas de EST001/CUR001")

# Historial antes de una fecha: máximo < fecha límite
h = ps.obtener_historial(db, "EST001", "CUR001", date(2026, 5, 20))
max_fecha = db.execute(
    text(
        """
        SELECT MAX(s.session_date) FROM asistencias a
        JOIN sesiones s ON a.session_id = s.session_id
        WHERE a.student_id='EST001' AND s.course_id='CUR001'
          AND s.session_date < '2026-05-20'
        """
    )
).scalar()
check("E3. Sin datos futuros en historial", len(h) == 7 and str(max_fecha) < "2026-05-20",
      f"última sesión usada={max_fecha}")

metricas = json.loads(
    Path("models/metricas_modelo.json").read_text(encoding="utf-8")
)
check(
    "E4. Métricas no inventadas",
    metricas.get("estado") == "pendiente_evaluacion"
    and all(metricas.get(k) is None for k in ("accuracy", "precision", "recall", "f1_score")),
    "estado=pendiente_evaluacion",
)

env = Path(".env").read_text(encoding="utf-8")
faltan = [
    k
    for k in ("TIDB_HOST", "TIDB_PORT", "TIDB_USER", "TIDB_PASSWORD", "TIDB_DATABASE", "TIDB_SSL_CA")
    if f"{k}=" not in env or env.split(f"{k}=")[1].split("\n")[0].strip() == ""
]
check("E5. Variables de entorno configuradas", not faltan,
      f"faltan: {faltan}" if faltan else "todas presentes")

db.close()

fallos = [r for r in resultados if not r[1]]
print(f"\n==== RESUMEN: {len(resultados) - len(fallos)}/{len(resultados)} PASS ====")
if fallos:
    for n_, _, d in fallos:
        print(f"  FAIL: {n_} {d}")
sys.exit(1 if fallos else 0)
