from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída desde variables de entorno / archivo .env"""

    # Credenciales de TiDB
    TIDB_HOST: str = "localhost"
    TIDB_PORT: int = 4000
    TIDB_USER: str = "root"
    TIDB_PASSWORD: str = ""
    TIDB_DATABASE: str = "sistema_asistencia"
    # Ruta al certificado CA (p. ej. isrgrootx1.pem de TiDB Cloud).
    # Vacío = conexión sin TLS (solo para TiDB local).
    TIDB_SSL_CA: str = ""

    # Ruta al modelo Keras entrenado
    MODEL_PATH: str = "models/modelo_asistencia.keras"
    MODEL_CONFIG_PATH: str = "models/model_config.json"

    # Orígenes permitidos para CORS (frontend Vite)
    CORS_ORIGINS: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.TIDB_USER}:{self.TIDB_PASSWORD}"
            f"@{self.TIDB_HOST}:{self.TIDB_PORT}/{self.TIDB_DATABASE}"
        )


settings = Settings()
