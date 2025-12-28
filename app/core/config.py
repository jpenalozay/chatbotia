"""
Configuración centralizada para el Chatbot RAG Demo
Versión simplificada - Solo LLM Local (Ollama/Mistral)
"""
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Cargar variables de entorno
BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / '.env'

if ENV_PATH.exists():
    load_dotenv(ENV_PATH.as_posix())
else:
    load_dotenv(find_dotenv())


class DatabaseConfig:
    """Configuración de base de datos MySQL"""
    USER: str = os.getenv("DB_USER", "root")
    PASSWORD: str = os.getenv("DB_PASS", "root")
    HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("DB_PORT", "3306"))
    NAME: str = os.getenv("DB_NAME", "chatbot_db")
    
    # Pool configuration
    POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))
    POOL_PRE_PING: bool = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"
    ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"
    
    @property
    def url(self) -> str:
        return f"mysql+pymysql://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}?charset=utf8mb4"


class OllamaConfig:
    """Configuración de Ollama (LLM Local)"""
    HOST: str = os.getenv("OLLAMA_HOST", "http://localhost")
    PORT: int = int(os.getenv("OLLAMA_PORT", "11434"))
    MODEL: str = os.getenv("OLLAMA_MODEL", "mistral")
    TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    
    @property
    def base_url(self) -> str:
        return f"{self.HOST}:{self.PORT}"


class WebConfig:
    """Configuración del servidor web"""
    SECRET_KEY: str = os.getenv("WEB_SECRET", "demo-secret-key-change-in-production")
    HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("WEB_PORT", "9090"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    RELOAD: bool = False


class DemoConfig:
    """Configuración específica para el modo demo"""
    COMPANY_ID: int = 2  # ID real de la empresa demo en BD
    USER_ID: int = 1  # ID del usuario demo
    COMPANY_CODE: str = os.getenv("DEMO_COMPANY_CODE", "0001")
    COMPANY_NAME: str = os.getenv("DEMO_COMPANY_NAME", "Demo Company")


class AppConfig:
    """Configuración principal de la aplicación"""
    # Sub-configuraciones
    db = DatabaseConfig()
    ollama = OllamaConfig()
    web = WebConfig()
    demo = DemoConfig()
    
    # Configuraciones generales
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "demo")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Lima")
    
    # CORS
    CORS_ORIGINS: list = ["*"]  # Permitir todos en demo
    
    @classmethod
    def validate(cls) -> bool:
        """Valida configuraciones críticas"""
        required = [
            (cls.db.USER, "DB_USER"),
            (cls.db.PASSWORD, "DB_PASS"),
        ]
        
        missing = [var for value, var in required if not value]
        if missing:
            print(f"⚠️ Advertencia: Variables faltantes: {', '.join(missing)}")
            print("⚠️ Usando valores por defecto")
        
        return True


# Instancia global de configuración
settings = AppConfig()

# Validar configuración al importar
if os.getenv("SKIP_CONFIG_VALIDATION") != "true":
    settings.validate()
