from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OAUTH_GOOGLE_CLIENT_ID: str
    OAUTH_GOOGLE_CLIENT_SECRET: str

    model_config = SettingsConfigDict(env_file="src/gateway_auth/.env")
