from dataclasses import dataclass
from dotenv import load_dotenv
import os
load_dotenv()

@dataclass(frozen=True)
class Settings:
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8080"))
    ollama_enabled: bool = os.getenv("OLLAMA_ENABLED", "false").lower() == "true"
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    approved_workspace: str = os.getenv("APPROVED_WORKSPACE", "./workspace")
    autonomy_mode: str = os.getenv("AUTONOMY_MODE", "approval")
    worker_interval_seconds: int = int(os.getenv("WORKER_INTERVAL_SECONDS", "10"))
    auto_remediate: bool = os.getenv("AUTO_REMEDIATE", "false").lower() == "true"
    current_role: str = os.getenv("CURRENT_ROLE", "operator")
    worker_name: str = os.getenv("WORKER_NAME", "worker-a")
    secret_provider: str = os.getenv("SECRET_PROVIDER", "file")

settings = Settings()
