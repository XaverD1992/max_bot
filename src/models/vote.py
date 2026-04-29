from sqlalchemy import Column, BigInteger, Integer, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.models.base import Base

class Vote(Base):
    __tablename__ = "votes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    initiative_id = Column(Integer, ForeignKey("initiatives.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Уникальное ограничение: один пользователь — один голос на инициативу
    __table_args__ = (
        UniqueConstraint("user_id", "initiative_id", name="uq_vote_user_initiative"),
    )
    
    user = relationship("User", back_populates="votes")
    initiative = relationship("Initiative", back_populates="votes")
    
    def __repr__(self):
        return f"<Vote(user_id={self.user_id}, initiative_id={self.initiative_id})>"