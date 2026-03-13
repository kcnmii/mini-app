from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "doc-mini-api"
    app_env: str = "development"
    telegram_app_url: str = "https://example.com"
    frontend_origin: str = "https://example.com"
    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    jwt_secret: str = "change-me"
    docgen_url: str = "http://localhost:4001"
    service_url_gotenberg: str = "http://localhost:3000"
    service_user_gotenberg: str = ""
    service_password_gotenberg: str = ""
    sqlite_path: str = "./data/docmini.sqlite3"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
