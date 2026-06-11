from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.models.base import Base
import enum

class InitiativeStatus(enum.Enum):
    PENDING = "pending"       # На модерации
    APPROVED = "approved"     # Одобрено, опубликовано
    REJECTED = "rejected"     # Отклонено
    IN_PROGRESS = "in_progress" # Реализуется
    COMPLETED = "completed"     # Завершена

class InitiativeCategory(enum.Enum):
    ROADS = "дороги"
    IMPROVEMENT = "благоустройство"
    PLAYGROUNDS = "детские площадки"
    LIGHTING = "освещение"
    UTILITIES = "ЖКХ"

class Initiative(Base):
    __tablename__ = "initiatives"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(InitiativeCategory), nullable=False)
    location = Column(String(300), nullable=False)  # текстовое описание
    status = Column(Enum(InitiativeStatus), default=InitiativeStatus.PENDING, nullable=False)
    author_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    reject_reason = Column(Text, nullable=True)  # Причина отклонения
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    author = relationship("User", back_populates="initiatives", foreign_keys=[author_id])
    votes = relationship("Vote", back_populates="initiative", cascade="all, delete-orphan")
    
    @property
    def votes_count(self) -> int:
        return len(self.votes)
    
    def __repr__(self):
        return f"<Initiative(id={self.id}, title='{self.title}', status={self.status.value})>"