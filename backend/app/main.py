from fastapi import FastAPI
from app.routers import router
from app.database import engine, Base

# Create tables (Alembic recommended for production)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Hospital Management System")
app.include_router(router)

@app.get("/")
async def root():
    return {"status": "ok"}
