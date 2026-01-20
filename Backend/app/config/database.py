from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Decide cuál base de datos usar
USE_LOCAL = os.getenv("USE_LOCAL_DB", "false").lower() == "true"

if USE_LOCAL:
    DATABASE_URL = os.getenv("DATABASE_LOCAL_URL")
else:
    DATABASE_URL = os.getenv("DATABASE_NUBE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada en el entorno")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
