"""Valida la base de conocimientos y el motor de inferencia.

Comprueba que cada regla IF-THEN produce la conclusión esperada con
hechos de prueba conocidos y que siempre existe una regla por defecto.

Uso (desde backend/):
    .\\venv\\Scripts\\python.exe scripts\\validar_reglas.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.motor_inferencia import (  # noqa: E402
    base_conocimientos,
    calcular_hechos,
    evaluar,
)

# (descripcion, hechos, nivel_riesgo, etiqueta, alerta, regla_prioritaria)
CASOS = [
    (
        "Racha de 4 faltas seguidas",
        {"probabilidad": 0.9, "ausencias_ultimas": 4, "racha_ausencias": 4,
         "tendencia": "empeorando", "porcentaje_asistencia": 0.4286},
        "alto", "no asiste", True, "R1",
    ),
    (
        "Probabilidad muy baja sin racha",
        {"probabilidad": 0.2, "ausencias_ultimas": 2, "racha_ausencias": 0,
         "tendencia": "estable", "porcentaje_asistencia": 0.7143},
        "alto", "no asiste", True, "R2",
    ),
    (
        "Cinco faltas dispersas",
        {"probabilidad": 0.6, "ausencias_ultimas": 5, "racha_ausencias": 0,
         "tendencia": "estable", "porcentaje_asistencia": 0.2857},
        "alto", "no asiste", True, "R3",
    ),
    (
        "Probabilidad bajo el umbral sin otros factores",
        {"probabilidad": 0.4, "ausencias_ultimas": 2, "racha_ausencias": 0,
         "tendencia": "estable", "porcentaje_asistencia": 0.7143},
        "medio", "probable asistencia", True, "R4",
    ),
    (
        "Dos faltas seguidas con buen modelo",
        {"probabilidad": 0.8, "ausencias_ultimas": 2, "racha_ausencias": 2,
         "tendencia": "empeorando", "porcentaje_asistencia": 0.7143},
        "medio", "probable asistencia", True, "R5",
    ),
    (
        "Tres faltas sin racha",
        {"probabilidad": 0.8, "ausencias_ultimas": 3, "racha_ausencias": 1,
         "tendencia": "estable", "porcentaje_asistencia": 0.5714},
        "medio", "probable asistencia", True, "R6",
    ),
    (
        "Tendencia empeorando sola",
        {"probabilidad": 0.8, "ausencias_ultimas": 2, "racha_ausencias": 0,
         "tendencia": "empeorando", "porcentaje_asistencia": 0.7143},
        "medio", "probable asistencia", True, "R7",
    ),
    (
        "Asistencia perfecta",
        {"probabilidad": 0.95, "ausencias_ultimas": 0, "racha_ausencias": 0,
         "tendencia": "estable", "porcentaje_asistencia": 1.0},
        "bajo", "asiste", False, "R8",
    ),
]


def main() -> int:
    kb = base_conocimientos()
    print(f"Base de conocimientos: {len(kb['reglas'])} reglas\n")

    fallos = 0
    for desc, hechos, riesgo, etiqueta, alerta, regla in CASOS:
        r = evaluar(hechos)
        ok = (
            r["nivel_riesgo"] == riesgo
            and r["etiqueta"] == etiqueta
            and r["alerta"] == alerta
            and r["reglas_activadas"][0] == regla
        )
        marca = "PASS" if ok else "FAIL"
        if not ok:
            fallos += 1
        print(f"[{marca}] {desc}: {r['nivel_riesgo']}/{r['etiqueta']} "
              f"(regla {r['reglas_activadas'][0]})")

    # Comprobación de consistencia: hechos derivados de una ventana real
    hechos = calcular_hechos([1, 1, 0, 0, 0, 1, 0], 0.4)
    assert hechos["racha_ausencias"] == 1
    assert hechos["ausencias_ultimas"] == 4
    print(f"\nHechos derivados de [1,1,0,0,0,1,0]: {hechos}")

    print(f"\nResultado: {len(CASOS) - fallos}/{len(CASOS)} casos PASS")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
