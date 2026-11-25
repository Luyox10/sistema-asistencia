# Instrucciones de instalación

## 1. Instalar lo necesario

- **Python 3.12** → https://www.python.org/downloads/
- **Node.js 18+** → https://nodejs.org/

## 2. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copia el archivo de entorno:

```powershell
Copy-Item .env.example .env
```

Edita `.env` y pon tus credenciales de TiDB (host, usuario, contraseña,
base de datos) y `TIDB_SSL_CA=certs/isrgrootx1.pem`.

Levantar:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

## 3. Frontend

En otra terminal:

```powershell
cd frontend
npm install
npm run dev
```

## 4. Usar

Abre `http://localhost:5173`, ve a **Datasets** y sube
`data/dataset_institucion_demo.csv` o tu propio CSV.

> Nota: los datasets se guardan en memoria; si reinicias el backend,
> vuelve a subir el CSV.
