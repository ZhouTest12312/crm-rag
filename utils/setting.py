from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 敏感项不设真实默认值，必须从 .env 读取
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES: int = 60 * 60 * 24 * 7
    DATABASE_URL: str = (
        "mysql+aiomysql://user:password@127.0.0.1:3306/edu_crm_agent?charset=utf8mb4"
    )
    VECTOR_DATABASE_URL: str = (
        "postgresql://postgres:postgres@127.0.0.1:5432/edu_crm_vectors"
    )
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"


settings = Settings()
