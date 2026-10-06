import os
from pydantic import BaseModel

class AppConfig(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Enterprise Core API")
    environment: str = os.getenv("ENVIRONMENT", "dev")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://mongodb-service:27017/enterprise_db")
    version: str = os.getenv("APP_VERSION", "1.0.0")

config = AppConfig()
