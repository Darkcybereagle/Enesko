from functools import lru_cache
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    app_name:str="Enesko"
    app_env:str="development"
    database_url:str="sqlite:///./enesko.db"
    cors_origins:str="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3002,http://127.0.0.1:3002"
    jwt_secret:str="CHANGE_ME_BEFORE_PRODUCTION_ENESKO_SECRET"
    jwt_algorithm:str="HS256"
    access_token_expire_minutes:int=60
    local_admin_password:str="EneskoLocal2026!"
    local_tenant_password:str="TenantLocal2026!"
    model_config=SettingsConfigDict(env_file=".env",extra="ignore")

    @property
    def cors_origin_list(self)->list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings()->Settings:
    return Settings()

settings=get_settings()
