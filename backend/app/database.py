from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

# TLS: TiDB Cloud requiere conexión cifrada. Si se define TIDB_SSL_CA se
# verifica el certificado contra esa CA; si está vacío se asume TiDB local
# sin TLS.
connect_args: dict = {}
if settings.TIDB_SSL_CA:
    connect_args["ssl_ca"] = settings.TIDB_SSL_CA

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependencia de FastAPI que entrega una sesión de SQLAlchemy."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> None:
    """Comprueba la conexión con TiDB. Lanza excepción si falla."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def get_table_columns(table_name: str) -> list[dict] | None:
    """Devuelve las columnas de una tabla o None si no existe."""
    insp = inspect(engine)
    if not insp.has_table(table_name):
        return None
    return [
        {
            "nombre": c["name"],
            "tipo": str(c["type"]),
            "nullable": c["nullable"],
            "pk": c["name"] in (insp.get_pk_constraint(table_name).get("constrained_columns") or []),
        }
        for c in insp.get_columns(table_name)
    ]


def get_existing_tables() -> list[str]:
    """Lista las tablas existentes en la base de datos."""
    return inspect(engine).get_table_names()
