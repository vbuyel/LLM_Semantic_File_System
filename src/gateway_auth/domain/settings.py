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
    GOOGLE_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    AGENT_SERVER: str
    FILE_OPS_SERVER: str
    EVENT_DB_URL: str = "http://localhost:8003"
    EVENT_DB_WS_URL: str = "ws://localhost:8003/ws/gateway"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
