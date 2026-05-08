"""
CrowdShield Database — SQLite via SQLAlchemy
Tables: areas, personnel, area_personnel (join), cameras
"""

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime,
    ForeignKey, Table, Text
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os

# ------------------------------------------------------------------
# Engine setup  (database stored inside the project root)
# ------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'crowdshield.db')
DB_PATH = os.path.abspath(DB_PATH)

engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# ------------------------------------------------------------------
# Association table (Areas ↔ Personnel — many-to-many)
# ------------------------------------------------------------------
area_personnel = Table(
    'area_personnel', Base.metadata,
    Column('area_id',      Integer, ForeignKey('areas.id'),     primary_key=True),
    Column('personnel_id', Integer, ForeignKey('personnel.id'), primary_key=True),
)

# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------

class Area(Base):
    __tablename__ = 'areas'

    id             = Column(Integer, primary_key=True, autoincrement=True)
    name           = Column(String(120), nullable=False)
    description    = Column(Text, default='')
    capacity_limit = Column(Integer, default=0)     # 0 = not set
    created_at     = Column(DateTime, default=datetime.utcnow)

    cameras   = relationship('Camera',    back_populates='area', cascade='all, delete-orphan')
    personnel = relationship('Personnel', secondary=area_personnel, back_populates='areas')

    def to_dict(self):
        return {
            'id':             self.id,
            'name':           self.name,
            'description':    self.description,
            'capacity_limit': self.capacity_limit,
            'created_at':     self.created_at.isoformat() if self.created_at else None,
            'camera_count':   len(self.cameras),
            'personnel_count':len(self.personnel),
        }


class Personnel(Base):
    __tablename__ = 'personnel'

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(120), nullable=False)
    email      = Column(String(200), default='')
    phone      = Column(String(30),  default='')
    role       = Column(String(80),  default='Security Officer')
    created_at = Column(DateTime, default=datetime.utcnow)

    areas = relationship('Area', secondary=area_personnel, back_populates='personnel')

    def to_dict(self):
        return {
            'id':         self.id,
            'name':       self.name,
            'email':      self.email,
            'phone':      self.phone,
            'role':       self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Camera(Base):
    __tablename__ = 'cameras'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    area_id     = Column(Integer, ForeignKey('areas.id'), nullable=False)
    session_id  = Column(String(30), unique=True, nullable=False)
    name        = Column(String(120), nullable=False)
    camera_type = Column(String(20), default='other')   # entry | exit | center | perimeter | other
    description = Column(String(200), default='')
    filepath    = Column(String(500), default='')
    created_at  = Column(DateTime, default=datetime.utcnow)

    area = relationship('Area', back_populates='cameras')

    def to_dict(self):
        return {
            'id':          self.id,
            'area_id':     self.area_id,
            'session_id':  self.session_id,
            'name':        self.name,
            'camera_type': self.camera_type,
            'description': self.description,
            'filepath':    self.filepath,
            'created_at':  self.created_at.isoformat() if self.created_at else None,
        }


# ------------------------------------------------------------------
# Init
# ------------------------------------------------------------------

def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    print(f"[DB] SQLite ready at: {DB_PATH}")


def get_db():
    """Get a new DB session (use as context manager or close manually)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
