from pydantic_settings import BaseSettings, SettingsConfigDict

oauth_states: set = set()


class Settings(BaseSettings):
    OAUTH_GOOGLE_CLIENT_ID: str
    OAUTH_GOOGLE_CLIENT_SECRET: str
    OAUTH_GOOGLE_REDIRECT_URI: str
    OAUTH_GOOGLE_BASE_URL: str
    GOOGLE_DRIVE_SCOPE: list[str] = [
        "openid",
        "profile",
        "email",
        "https://www.googleapis.com/auth/drive",
    ]

    model_config = SettingsConfigDict(env_file="src/gateway_auth/.env")
