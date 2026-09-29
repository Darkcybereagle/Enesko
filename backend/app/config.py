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

    whatsapp_graph_url:str="https://graph.facebook.com"
    whatsapp_api_version:str="v23.0"
    whatsapp_phone_number_id:str=""
    whatsapp_access_token:str=""
    whatsapp_verify_token:str="CHANGE_ME_WHATSAPP_VERIFY_TOKEN"

    smtp_host:str=""
    smtp_port:int=587
    smtp_username:str=""
    smtp_password:str=""
    smtp_from_email:str=""
    smtp_use_tls:bool=True
    inbound_webhook_secret:str="CHANGE_ME_INBOUND_WEBHOOK_SECRET"

    cinema_feed_url:str=""
    cinema_feed_token:str=""
    parking_feed_url:str=""
    parking_feed_token:str=""

    model_config=SettingsConfigDict(env_file=".env",extra="ignore")

    @property
    def cors_origin_list(self)->list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def whatsapp_configured(self)->bool:
        return bool(self.whatsapp_phone_number_id and self.whatsapp_access_token)

    @property
    def email_configured(self)->bool:
        return bool(self.smtp_host and self.smtp_from_email)

    @property
    def cinema_feed_configured(self)->bool:
        return bool(self.cinema_feed_url)

    @property
    def parking_feed_configured(self)->bool:
        return bool(self.parking_feed_url)

@lru_cache
def get_settings()->Settings:
    return Settings()

settings=get_settings()
