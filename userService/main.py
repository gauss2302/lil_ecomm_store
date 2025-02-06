from fastapi import FastAPI
from auth import auth_router
from database import init_db

app = FastAPI(title="User Service")

app.include_router(auth_router, prefix="/auth", tags=["Auth"])


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/")
async def root():
    return {"message": "User Service is running"}