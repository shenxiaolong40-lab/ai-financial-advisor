from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    user_mode: str = "single"
    database_url: str = "sqlite:///./finance.db"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:5500,null"

    @property
    def is_single_user(self) -> bool:
        return self.user_mode == "single"

    @property
    def origins_list(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
