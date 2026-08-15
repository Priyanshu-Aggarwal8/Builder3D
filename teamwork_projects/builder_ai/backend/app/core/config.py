from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Builder AI Backend"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = "sqlite:///./builder_ai.db"
    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        case_sensitive = True


settings = Settings()
