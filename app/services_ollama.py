import requests
from app.config import settings
def ollama_generate(prompt, system=None):
    full = prompt if not system else f"System:\n{system}\n\nUser:\n{prompt}"
    r=requests.post(f"{settings.ollama_base_url.rstrip('/')}/api/generate",json={"model":settings.ollama_model,"prompt":full,"stream":False},timeout=180)
    r.raise_for_status(); return r.json().get("response","").strip()
