from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_secret: str = "changeme"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "newsbrief"
    postgres_user: str = "newsbrief"
    postgres_password: str = "newsbrief"

    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "newsbrief-raw"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
