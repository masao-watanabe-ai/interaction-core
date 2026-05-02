from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://chatai:chatai_password@db:5432/chatai"
    redis_url: str = "redis://redis:6379/0"
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 30

    # Google OAuth — GCP コンソールで取得して .env に設定
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    frontend_url: str = "http://localhost:3000"

    # Cookie 設定: HTTPS 環境では True に設定
    cookie_secure: bool = False

    # OpenAI — 未設定時はルールベース分析にフォールバック
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # 開発用フラグ: false にすると /auth/dev-login が 403 を返す
    dev_login_enabled: bool = True

    model_config = {"env_file": ".env"}


settings = Settings()

ASYNC_DATABASE_URL = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://", 1
)
