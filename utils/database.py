"""Database utilities for the network automation agent.

This module provides database models and utilities for managing network
device inventory using SQLAlchemy with SQLite. The module includes:

- Device model definition
- Database engine and session management
- Context manager for safe database sessions
- Database initialization functions

The database stores network device configuration information including
connection parameters and device identification.
"""

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from contextlib import contextmanager
from typing import Generator

# Database URL for the inventory database
DATABASE_URL = "sqlite:///inventory.db"

# Create database engine and session factory
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Device(Base):
    """SQLAlchemy model for network device configurations.

    Represents a network device in the inventory database with all necessary
    connection parameters. Each device has a unique name and required fields
    for establishing SSH connections through Netmiko.

    Attributes:
        id: Unique identifier for the device record
        name: Unique name identifier for the device
        host: IP address or hostname of the network device
        username: Username for SSH authentication
        password_env_var: Name of environment variable containing the password
        device_type: Device type identifier for Netmiko (e.g., 'cisco_ios')
    """

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    host = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password_env_var = Column(String, nullable=False)
    device_type = Column(String, nullable=False)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Provides a safe way to get and use database sessions. Automatically
    handles session creation, commit/rollback on exceptions, and proper
    cleanup by closing the session after use.

    Yields:
        Database session object for use in operations

    Example:
        with get_db() as db:
            devices = db.query(Device).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_db_and_tables():
    """Creates the database tables if they don't already exist.

    Initializes the database schema by creating all defined tables
    based on the SQLAlchemy models. This function should be called
    during application startup to ensure the database structure exists.
    """
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_db_and_tables()
    print("Database and tables created.")
