from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus

class Setting(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    secret_key: SecretStr
    algorithm: str = "HS256"
    access_token_expired_minutes: int = 30

    POSTGRES_USER: str
    POSTGRES_PASSWORD: SecretStr
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str

    @property
    def database_url(self):
        password = quote_plus(self.POSTGRES_PASSWORD.get_secret_value())
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{password}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

setting = Setting()