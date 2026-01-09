from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "ResearchRAG"
    debug: bool = False

    # Database
    database_url: str = "postgresql://localhost:5432/researchrag"

    # OpenAI / LLM
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o"
    vision_model: str = "gpt-4o"

    # Vector search
    embedding_dimension: int = 1536
    similarity_top_k: int = 5

    # File storage
    upload_dir: str = "./uploads"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
