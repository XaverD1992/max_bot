from sqlalchemy import Column, BigInteger, String, Integer, Enum
from sqlalchemy.orm import relationship
from src.models.base import Base
import enum

class UserRole(enum.Enum):
    RESIDENT = "resident"
    MODERATOR = "moderator"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=False)  # chat_id
    phone = Column(String(20), nullable=True)
    name = Column(String(100), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.RESIDENT, nullable=False)
    
    initiatives = relationship("Initiative", back_populates="author", foreign_keys="Initiative.author_id")
    votes = relationship("Vote", back_populates="user")
    
    def __repr__(self):
        return f"<User(chat_id={self.id}, role={self.role.value})>"