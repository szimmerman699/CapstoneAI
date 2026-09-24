from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    anthropic_api_key: str = ""
    model_name: str = "claude-sonnet-5"
    max_tokens: int = 4096

    model_config = {"env_file": ".env", "env_prefix": ""}
    pinecone_api_key: str = ""
settings = Settings()
