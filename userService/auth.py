from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
from sqlalchemy.ext.asyncio import AsyncSession
from database import SessionLocal
from crud import get_user_by_email, create_user
from redis_client import redis_client

SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

auth_router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


async def get_db():
    async with SessionLocal() as db:
        yield db


@auth_router.post("/register")
async def register_user(email: str, password: str, db: AsyncSession = Depends(get_db)):
    existing_user = await get_user_by_email(db, email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await create_user(db, email, password)


@auth_router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, form_data.username)
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.encode({"sub": user.email, "exp": datetime.utcnow() + access_token_expires}, SECRET_KEY,
                              algorithm=ALGORITHM)

    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = jwt.encode({"sub": user.email, "exp": datetime.utcnow() + refresh_token_expires}, SECRET_KEY,
                               algorithm=ALGORITHM)

    redis_client.set(user.email, refresh_token, ex=refresh_token_expires.total_seconds())

    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


@auth_router.post("/refresh")
async def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        stored_refresh_token = redis_client.get(email)
        if not stored_refresh_token or stored_refresh_token != refresh_token:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = jwt.encode({"sub": email, "exp": datetime.utcnow() + access_token_expires}, SECRET_KEY,
                                      algorithm=ALGORITHM)

        return {"access_token": new_access_token, "token_type": "bearer"}

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
