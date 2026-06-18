from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import User, Initiative, Vote, UserRole, InitiativeStatus
from src.logging_config import logger

# === User ===
async def get_or_create_user(db: AsyncSession, chat_id: int, name: str = None, phone: str = None) -> User:
    logger.info(f"Checking user {chat_id}")
    stmt = select(User).where(User.id == chat_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    logger.info(f"User found: {user}")

    if not user:
        logger.info(f"Creating new user {chat_id}")
        user = User(id=chat_id, name=name, phone=phone)
        db.add(user)
        logger.info("Added to session")
        await db.flush()
        await db.commit()  # Сохраняем нового пользователя
        logger.info(f"Committed, created new user: {chat_id}")
    elif phone and not user.phone:
        user.phone = phone
        await db.commit()  # Сохраняем обновление телефона
        logger.info(f"Committed, обновлён телефон для пользователя {chat_id}")

    return user

async def set_user_role(db: AsyncSession, chat_id: int, role: UserRole) -> bool:
    stmt = update(User).where(User.id == chat_id).values(role=role)
    result = await db.execute(stmt)
    await db.commit()
    logger.info(f"Пользователю {chat_id} назначена роль: {role.value}")
    return result.rowcount > 0

# === Initiative ===
async def create_initiative(db: AsyncSession, author_id: int, title: str, description: str,
                            category, location: str) -> Initiative:
    initiative = Initiative(
        author_id=author_id,
        title=title,
        description=description,
        category=category,
        location=location
    )
    db.add(initiative)
    await db.flush()
    await db.commit()  # Сохраняем изменения
    logger.info(f"Создана инициатива #{initiative.id} от пользователя {author_id}")
    return initiative

async def get_initiative_by_id(db: AsyncSession, initiative_id: int) -> Initiative | None:
    stmt = select(Initiative).where(Initiative.id == initiative_id).options(selectinload(Initiative.votes))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_approved_initiatives(db: AsyncSession, category=None, limit: int = 20):
    stmt = select(Initiative).where(Initiative.status == InitiativeStatus.APPROVED).options(selectinload(Initiative.votes))
    if category:
        stmt = stmt.where(Initiative.category == category)
    stmt = stmt.order_by(Initiative.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

async def update_initiative_status(db: AsyncSession, initiative: Initiative, status: InitiativeStatus):
    initiative.status = status
    await db.flush()
    await db.commit()  # Сохраняем изменения
    logger.info(f"Инициатива #{initiative.id} переведена в статус: {status.value}")

# === Vote ===
async def has_user_voted(db: AsyncSession, user_id: int, initiative_id: int) -> bool:
    stmt = select(Vote).where(Vote.user_id == user_id, Vote.initiative_id == initiative_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None

async def add_vote(db: AsyncSession, user_id: int, initiative_id: int) -> bool:
    if await has_user_voted(db, user_id, initiative_id):
        return False
    vote = Vote(user_id=user_id, initiative_id=initiative_id)
    db.add(vote)
    await db.flush()
    await db.commit()  # Сохраняем изменения
    logger.info(f"Пользователь {user_id} проголосовал за инициативу #{initiative_id}")
    return True

async def get_user_by_id(db: AsyncSession, chat_id: int) -> User | None:
    stmt = select(User).where(User.id == chat_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

async def get_moderators(db: AsyncSession) -> list[User]:
    """Получить всех пользователей с ролью модератора или админа"""
    logger.info("Вход в get_moderators")
    stmt = select(User).where(
        User.role.in_([UserRole.MODERATOR, UserRole.ADMIN])
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_pending_initiatives(db: AsyncSession) -> list[Initiative]:
    """Получить инициативы, ожидающие модерации"""
    stmt = select(Initiative).where(Initiative.status == InitiativeStatus.PENDING).options(selectinload(Initiative.votes))
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_user_initiatives(db: AsyncSession, chat_id: int, limit: int = 10) -> list[Initiative]:
    """Получить инициативы конкретного пользователя"""
    stmt = select(Initiative).where(Initiative.author_id == chat_id).options(selectinload(Initiative.votes))
    stmt = stmt.order_by(Initiative.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def update_initiative_status_with_reason(db: AsyncSession, initiative: Initiative, status: InitiativeStatus, reject_reason: str = None):
    """Обновить статус инициативы с причиной отклонения"""
    initiative.status = status
    if reject_reason is not None:
        initiative.reject_reason = reject_reason
    await db.flush()
    await db.commit()
    logger.info(f"Инициатива #{initiative.id} переведена в статус: {status.value}")