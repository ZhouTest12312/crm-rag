from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DEEPSEEK_API_KEY: str = "sk-41d274fea44142a7b3b754cd114059fe"
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    # 密钥，生产环境一定要改成复杂字符串，不要硬编码写死代码
    JWT_SECRET_KEY: str = "edu-crm-langgraph-jwt-secret-change-me-2026-32b"
    JWT_ALGORITHM: str = "HS256"
    # token过期秒数，这里7天
    JWT_ACCESS_TOKEN_EXPIRES: int = 60 * 60 * 24 * 7
    # 与手写仓 edu-crm-agent 共用同一 MySQL 库（查单/取消）
    DATABASE_URL: str = (
        "mysql+aiomysql://root:123456@127.0.0.1:3306/edu_crm_agent?charset=utf8mb4"
    )
    # 制度 RAG：Postgres + pgvector（与业务 MySQL 分离）
    VECTOR_DATABASE_URL: str = (
        "postgresql://postgres:postgres@127.0.0.1:5432/edu_crm_vectors"
    )
    # 本地 fastembed 模型（中文制度）；改模型后需 --force 重建索引
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"

settings = Settings()
