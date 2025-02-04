# models.py
from sqlalchemy import Boolean, Column, Integer, String, Table, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from enum import Enum
from .database import Base
import uuid

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

preferences = Table(
    'preferences',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('preferred_user_id', Integer, ForeignKey('users.id'))
)

restrictions = Table(
    'restrictions',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('restricted_user_id', Integer, ForeignKey('users.id'))
)

group_members = Table(
    'group_members',
    Base.metadata,
    Column('group_id', Integer, ForeignKey('groups.id')),
    Column('user_id', Integer, ForeignKey('users.id'))
)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(SQLEnum(UserRole), default=UserRole.USER)
    status = Column(SQLEnum(UserStatus), default=UserStatus.ACTIVE)
    is_verified = Column(Boolean, default=False)
    created_at = Column(String, default=datetime.utcnow)
    updated_at = Column(String, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    preferred_users = relationship(
        'User',
        secondary=preferences,
        primaryjoin=(id == preferences.c.user_id),
        secondaryjoin=(id == preferences.c.preferred_user_id),
        backref='preferred_by'
    )
    
    restricted_users = relationship(
        'User',
        secondary=restrictions,
        primaryjoin=(id == restrictions.c.user_id),
        secondaryjoin=(id == restrictions.c.restricted_user_id),
        backref='restricted_by'
    )
    
    groups = relationship('Group', secondary=group_members, back_populates='members')

class Group(Base):
    __tablename__ = 'groups'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(String)
    max_members = Column(Integer, default=10)
    created_at = Column(String, default=datetime.utcnow)
    updated_at = Column(String, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('users.id'))
    
    members = relationship('User', secondary=group_members, back_populates='groups')
    created_by = relationship('User', foreign_keys=[created_by_id])