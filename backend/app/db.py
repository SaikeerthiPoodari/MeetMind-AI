import os
from collections.abc import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meetmind.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try: yield db
    finally: db.close()

def init_db() -> None:
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    # The demo uses create_all for a zero-setup start. Apply the small additive
    # compatibility upgrade as well when an older local SQLite database exists.
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            columns = {item["name"] for item in inspect(connection).get_columns("meetings")}
            for name, definition in {
                "full_name": "VARCHAR(160) NOT NULL DEFAULT ''",
                "avatar_url": "TEXT NOT NULL DEFAULT ''",
                "share_code": "VARCHAR(20)",
                "executive_summary": "TEXT NOT NULL DEFAULT ''",
                "short_summary": "TEXT NOT NULL DEFAULT ''",
                "detailed_summary": "TEXT NOT NULL DEFAULT ''",
                "detected_language": "VARCHAR(12) NOT NULL DEFAULT 'und'",
            }.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE meetings ADD COLUMN {name} {definition}"))
            user_columns = {item["name"] for item in inspect(connection).get_columns("users")}
            for name, definition in {
                "full_name": "VARCHAR(160) NOT NULL DEFAULT ''",
                "avatar_url": "TEXT NOT NULL DEFAULT ''",
            }.items():
                if name not in user_columns:
                    connection.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))
