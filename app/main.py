from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(title="Predictor")
app.include_router(router)
