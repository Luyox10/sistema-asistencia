"""Genera un dataset CSV de ejemplo para una institución ficticia.

Datos históricos adecuados para una RNN: cada par (alumno, curso) tiene una
probabilidad base de asistencia propia, lo que produce secuencias con
tendencia real que el LSTM puede aprovechar.
"""

import csv
import random
from datetime import date, timedelta

random.seed(42)

INSTITUCION = "Universidad Demo Andina"
CURSOS = {
    "MAT101": "Matemática I",
    "FIS102": "Física II",
    "PSI103": "Psicología General",
}
N_ALUMNOS = 40
N_SESIONES = 30
INICIO = date(2026, 1, 12)  # lunes

rows = []
for i in range(1, N_ALUMNOS + 1):
    sid = f"ALU{i:03d}"
    nombre = f"Alumno{i:03d}"
    apellido = "Sintético"
    for cid, cname in CURSOS.items():
        # Tendencia propia del alumno en ese curso (0.50 - 0.97)
        p_base = random.uniform(0.50, 0.97)
        for s in range(N_SESIONES):
            ses_id = f"{cid}-S{s + 1:02d}"
            fecha = INICIO + timedelta(weeks=s)
            status = 1 if random.random() < p_base else 0
            rows.append(
                [sid, nombre, apellido, cid, cname, ses_id,
                 fecha.isoformat(), status, INSTITUCION]
            )

out = r"C:\Users\abrah\Downloads\sistema-asistencia\data\dataset_institucion_demo.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(
        ["student_id", "nombres", "apellidos", "course_id", "course_name",
         "session_id", "session_date", "attendance_status", "institucion"]
    )
    w.writerows(rows)

print(f"{out}: {len(rows)} filas, {N_ALUMNOS} alumnos, {len(CURSOS)} cursos, "
      f"{N_SESIONES} sesiones/curso")
