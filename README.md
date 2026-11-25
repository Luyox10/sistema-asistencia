# Sistema de Predicción de Asistencia Estudiantil

Sistema experto híbrido que predice la asistencia estudiantil: un modelo
de red neuronal LSTM (TensorFlow/Keras) estima la probabilidad de
asistencia y un motor de inferencia basado en reglas IF-THEN asigna el
nivel de riesgo, la etiqueta (asiste / probable asistencia / no asiste)
y genera alertas tempranas. API REST en FastAPI, base de datos TiDB y
frontend en React.

## Stack

- **Frontend:** React 19 + Vite + TypeScript + Recharts + Axios + React Router
- **Backend:** Python 3.12 + FastAPI + SQLAlchemy + TensorFlow/Keras
- **Base de datos:** TiDB Cloud (compatible con MySQL, conexión vía PyMySQL + TLS)

## Estructura

```
sistema-asistencia/
    frontend/
        src/
            api/            # Cliente Axios + tipos TypeScript
            components/     # Layout, StatCard, badges, barras
            pages/          # Dashboard, Estudiantes, Cursos,
                            # Asistencias, Predicciones,
                            # HistorialPredicciones
    backend/
        app/
            routes/         # dashboard, estudiantes, cursos,
                            # asistencias, predicciones, health
            services/
                prediction_service.py   # Carga del modelo LSTM + inferencia
                dataset_service.py      # Validación y registro de datasets
                motor_inferencia.py     # Motor de reglas IF-THEN
            config.py       # Settings (variables de entorno)
            database.py     # Engine SQLAlchemy + TLS + get_db
            schemas.py      # Esquemas Pydantic
            main.py         # Punto de entrada FastAPI
        models/
            modelo_asistencia.keras   # Modelo LSTM entrenado
            model_config.json         # Config real del modelo
            base_conocimientos.json   # Reglas IF-THEN del experto
            metricas_modelo.json      # Métricas de evaluación
        scripts/
            contar_registros.py   # Tablas, columnas y conteos
            importar_csv.py       # Importación vía staging (sin duplicados)
            validar_sistema.py    # Suite de pruebas de integración
            validar_reglas.py     # Pruebas de la base de conocimientos
            evaluar_modelo.py     # Métricas del modelo (split temporal)
            generar_dataset_demo.py  # Genera el CSV de ejemplo
        certs/isrgrootx1.pem      # CA raíz de TiDB Cloud
        requirements.txt
        .env.example
    data/                   # Dataset CSV
    README.md
    .gitignore
```

## Prerequisitos

- Node.js 18+ y npm
- Python 3.10+ (requerido por TensorFlow)
- Credenciales de la base de datos TiDB `sistema_asistencia`

## Instalación

### Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edita `.env` con tus credenciales (`TIDB_HOST`, `TIDB_PORT`, `TIDB_USER`,
`TIDB_PASSWORD`, `TIDB_DATABASE`, `TIDB_SSL_CA`). Para TiDB Cloud descarga
el certificado CA desde el panel del cluster y apunta `TIDB_SSL_CA` a él
(en este proyecto se usa `certs/isrgrootx1.pem`, ISRG Root X1). Para un
TiDB local sin TLS, deja `TIDB_SSL_CA` vacío.

### Frontend

```powershell
cd frontend
npm install
```

## Ejecución

### Backend (desde `backend/`)

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health DB: http://localhost:8000/api/health/database

### Frontend (desde `frontend/`)

```powershell
npm run dev
```

- Aplicación: http://localhost:5173

## API

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/dashboard` | Totales y % de asistencia |
| GET | `/api/dashboard/evolucion` | Asistencia por fecha |
| GET | `/api/dashboard/por-curso` | Resumen por curso |
| GET | `/api/estudiantes`, `/{id}`, `/{id}/asistencias` | Estudiantes |
| GET | `/api/cursos`, `/{id}`, `/{id}/sesiones`, `/{id}/estadisticas`, `/{id}/sesiones-pendientes/{sid}` | Cursos |
| GET | `/api/asistencias` (filtros: `student_id`, `course_id`, `fecha_desde`, `fecha_hasta`, `limit`, `offset`) | Asistencias |
| GET | `/api/asistencias/estudiante/{id}`, `/curso/{id}`, `/historial/{sid}/{cid}` | Consultas específicas |
| GET | `/api/predicciones`, `/estudiante/{id}` | Predicciones almacenadas |
| GET | `/api/predicciones/{sid}/{cid}/{ses}` | Predicción en vivo (no guarda) |
| POST | `/api/predicciones` | Genera y guarda (dedup por student+sesión) |
| POST | `/api/datasets/validar` | Valida un CSV subido (multipart `file`) |
| POST | `/api/predicciones/desde-dataset` | Predicciones por alumno desde CSV subido |
| POST | `/api/datasets` | Sube y registra un dataset en memoria (devuelve `dataset_id`) |
| GET | `/api/datasets`, `/{id}` | Lista / reporte de datasets cargados |
| DELETE | `/api/datasets/{id}` | Elimina el dataset de memoria |
| GET | `/api/datasets/{id}/dashboard` · `/evolucion` · `/por-curso` | Agregados del dataset |
| GET | `/api/datasets/{id}/estudiantes` · `/estudiantes/{sid}/asistencias` | Estudiantes del dataset |
| GET | `/api/datasets/{id}/cursos` · `/cursos/{cid}/sesiones` · `/cursos/{cid}/estadisticas` | Cursos del dataset |
| GET | `/api/datasets/{id}/asistencias` (mismos filtros) · `/historial/{sid}/{cid}` | Asistencias del dataset |
| GET | `/api/datasets/{id}/predicciones` (`student_id`, `course_id` opcionales) | Predicciones por alumno sobre el dataset |

### Flujo dataset-first

El frontend funciona sobre el **dataset activo**: se sube un CSV en la
página "Datasets", queda registrado en memoria con un `dataset_id` y todas
las vistas (dashboard, estudiantes, cursos, historial, predicciones) se
alimentan de él — sin tocar TiDB. Las predicciones generadas se guardan en
el historial local del navegador con el nombre del dataset de origen. La
memoria de datasets se vacía al reiniciar el backend.

## Esquema del dataset CSV

Cabecera exacta requerida (orden libre, columnas extra se ignoran):

```csv
student_id,course_id,session_id,session_date,attendance_status,institucion
```

| Columna | Tipo | Reglas |
|---|---|---|
| `student_id` | texto | Requerido, no vacío |
| `course_id` | texto | Requerido, no vacío |
| `session_id` | texto | Requerido, no vacío |
| `session_date` | fecha `YYYY-MM-DD` | Requerido, válido |
| `attendance_status` | entero | Solo `0` (inasistencia) o `1` (asistencia) |
| `institucion` | texto | **Opcional** — identifica la institución |

Reglas adicionales:

- Sin filas duplicadas por par (`student_id`, `session_id`).
- Cada par (estudiante, curso) necesita **mínimo 7 registros** para
  generar predicción; con menos se reporta `historial_insuficiente`.
- La predicción por alumno usa sus últimas 7 asistencias ordenadas por
  fecha y estima la probabilidad de asistir a la **próxima** sesión.
- Los datos se procesan en memoria: no se escribe nada en TiDB.
- Columnas opcionales extra admitidas: `nombres`, `apellidos`,
  `course_name` (se usan para mostrar nombres en la interfaz).

Dataset de ejemplo incluido: `data/dataset_institucion_demo.csv`
(3600 filas, 40 alumnos, 3 cursos, 30 sesiones por curso, institución
ficticia "Universidad Demo Andina"). Se regenera con
`backend/scripts/generar_dataset_demo.py`.

Reglas del modelo: ventana de 7 asistencias estrictamente anteriores a la
sesión objetivo, solo del mismo curso y estudiante; rechaza sesiones ya
registradas (409) e historiales insuficientes (422).

## Sistema experto híbrido

Cada predicción combina la salida del LSTM con reglas IF-THEN declaradas
en `backend/models/base_conocimientos.json`. El motor de inferencia
(`app/services/motor_inferencia.py`) deriva hechos de la ventana de 7
asistencias y la probabilidad del modelo:

| Hecho | Definición |
| --- | --- |
| `probabilidad` | Salida sigmoide del LSTM (0..1) |
| `ausencias_ultimas` | Inasistencias dentro de la ventana |
| `racha_ausencias` | Inasistencias consecutivas más recientes |
| `tendencia` | `empeorando` / `estable` / `mejorando` (mitades de la ventana) |
| `porcentaje_asistencia` | Tasa de asistencia en la ventana |

Las reglas se evalúan en orden de prioridad; la primera que cumple sus
condiciones define la conclusión y el resto se reporta en
`reglas_activadas` para explicabilidad:

- **Riesgo alto** → etiqueta `no asiste` + alerta (racha ≥3,
  probabilidad <0.3 o ≥5 ausencias en la ventana).
- **Riesgo medio** → etiqueta `probable asistencia` + alerta
  (probabilidad <0.5, racha ≥2, ≥3 ausencias o tendencia empeorando).
- **Riesgo bajo** → etiqueta `asiste`, sin alerta (regla por defecto).

La respuesta de cada predicción incluye el bloque `experto` con
`nivel_riesgo`, `alerta`, `etiqueta`, `recomendacion`,
`reglas_activadas` y `hechos`. Las tres etiquetas son salidas del sistema
experto (reglas sobre la probabilidad binaria del modelo), no clases
nativas del LSTM.

## Scripts (desde `backend/`)

```powershell
# Tablas, columnas y nº de registros
.\venv\Scripts\python.exe scripts\contar_registros.py

# Valida el CSV sin tocar la BD
.\venv\Scripts\python.exe scripts\importar_csv.py --solo-validar

# Importa el CSV a asistencias vía staging_asistencias
.\venv\Scripts\python.exe scripts\importar_csv.py

# Suite de pruebas de integración (backend en :8000)
.\venv\Scripts\python.exe scripts\validar_sistema.py

# Valida las reglas IF-THEN del motor de inferencia
.\venv\Scripts\python.exe scripts\validar_reglas.py

# Evalúa el modelo (split temporal) y escribe metricas_modelo.json
.\venv\Scripts\python.exe scripts\evaluar_modelo.py [ruta_csv]
```

## Notas

- `models/metricas_modelo.json` contiene métricas reales calculadas con
  `scripts/evaluar_modelo.py` sobre el dataset demo (split temporal,
  600 muestras de prueba). Son métricas **sobre ese dataset**; vuelve a
  ejecutar el script con otro CSV para evaluar otros datos.
- Las predicciones solo se pueden generar sobre sesiones sin asistencia
  registrada para el estudiante.
