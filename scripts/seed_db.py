"""Наполнение и очистка БД тестовыми данными.

Команды:
  python scripts/seed_db.py seed   — добавить тестовые записи
  python scripts/seed_db.py clear  — удалить все записи из БД
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete, select
from src.database.session import async_session_factory
from src.models import User, UserRole, Initiative, InitiativeStatus, InitiativeCategory, Vote


USERS = [
    (111111111, "Иван Жительов",    "+79000000001", UserRole.RESIDENT),
    (222222222, "Мария Модератова", "+79000000002", UserRole.MODERATOR),
    (333333333, "Пётр Админов",     "+79000000003", UserRole.ADMIN),
    (444444444, "Анна Петрова",     "+79000000004", UserRole.RESIDENT),
    (555555555, "Сергей Сидоров",   "+79000000005", UserRole.MODERATOR),
    (666666666, "Елена Никольская","+79000000006", UserRole.RESIDENT),
    (777777777, "Дмитрий Волков",   "+79000000007", UserRole.RESIDENT),
    (888888888, "Ольга Смирнова",   "+79000000008", UserRole.RESIDENT),
    (999999999, "Алексей Кузнецов", "+79000000009", UserRole.RESIDENT),
    (101010101, "Татьяна Орлова",   "+79000000010", UserRole.RESIDENT),
]

INITIATIVES = [
    (
        "Ремонт дороги на ул. Ленина",
        "Дорога покрылась ямами после зимы, требуется асфальтирование.",
        InitiativeCategory.ROADS, "ул. Ленина, д. 10-25",
        InitiativeStatus.APPROVED, 111111111, None,
    ),
    (
        "Установка детской площадки в парке",
        "Нужно оборудовать новую площадку с горками и турниками для детей 3-12 лет.",
        InitiativeCategory.PLAYGROUNDS, "Центральный парк, северная часть",
        InitiativeStatus.APPROVED, 444444444, None,
    ),
    (
        "Замена уличного освещения на ул. Гагарина",
        "Фонари не работают полгода, жители устанавливают самодельные.",
        InitiativeCategory.LIGHTING, "ул. Гагарина, д. 5-15",
        InitiativeStatus.APPROVED, 666666666, None,
    ),
    (
        "Обустройство зоны отдыха у реки",
        "Установить скамейки и урны, высадить кустарники на набережной.",
        InitiativeCategory.IMPROVEMENT, "Набережная р. Москвы",
        InitiativeStatus.APPROVED, 777777777, None,
    ),
    (
        "Жалоба на отключение горячей воды",
        "Регулярно отключают ГВС без предупреждения, обращения в УК не помогают.",
        InitiativeCategory.UTILITIES, "ул. Садовая, д. 17",
        InitiativeStatus.PENDING, 111111111, None,
    ),
    (
        "Установка ливневой канализации на ул. Садовой",
        "После дождя остаётся глубокая лужа, мешающая передвижению пешеходам.",
        InitiativeCategory.ROADS, "ул. Садовая, перекрёсток с ул. Пушкина",
        InitiativeStatus.PENDING, 999999999, None,
    ),
    (
        "Отключение освещения в подъезде дома 33",
        "В подъезде не работает освещение уже полмесяца, угроза безопасности.",
        InitiativeCategory.LIGHTING, "ул. Мира, д. 33, подъезд N2",
        InitiativeStatus.REJECTED, 444444444, "Жалоба относится к УК, а не к муниципалитету",
    ),
    (
        "Ремонт крыши в доме 8",
        "Крыша протекает, требуется капитальный ремонт перед зимой.",
        InitiativeCategory.UTILITIES, "ул. Лесная, д. 8",
        InitiativeStatus.APPROVED, 888888888, None,
    ),
    (
        "Озеленение пустыря между домами 12 и 14",
        "Преобразовать пустырь в сквер с скамейками для жителей.",
        InitiativeCategory.IMPROVEMENT, "ул. Зелёная, между д. 12 и д. 14",
        InitiativeStatus.PENDING, 555555555, None,
    ),
    (
        "Ямы на дороге у школы N5",
        "Дорога к школе покрыта ямами, опасность для детей и родителей.",
        InitiativeCategory.ROADS, "ул. Школьная, у школы N5",
        InitiativeStatus.REJECTED, 999999999, "Участок территории не входит в муниципальную надежду",
    ),
    (
        "Установка новых мусорных баков в дворе",
        "Текущие баки повреждены и не захватываются.",
        InitiativeCategory.UTILITIES, "ул. Рабочая, д. 12",
        InitiativeStatus.IN_PROGRESS, 777777777, None,
    ),
    (
        "Благоустройство детской площадки в садике",
        "Установка новых площадок и ремонт старого оборудования.",
        InitiativeCategory.IMPROVEMENT, "Детский сад N4",
        InitiativeStatus.COMPLETED, 111111111, None,
    ),
]


async def seed():
    async with async_session_factory() as session:
        # --- users ---
        for uid, name, phone, role in USERS:
            existing = (await session.execute(select(User).where(User.id == uid))).scalar_one_or_none()
            if existing:
                continue
            session.add(User(id=uid, name=name, phone=phone, role=role))
        await session.commit()
        print(f"added users: {len(USERS)}")

        # --- initiatives ---
        for title, desc, cat, loc, status, author_id, reject_reason in INITIATIVES:
            session.add(Initiative(
                title=title, description=desc,
                category=cat, location=loc,
                status=status, author_id=author_id,
                reject_reason=reject_reason,
            ))
        await session.commit()
        print(f"added initiatives: {len(INITIATIVES)}")

        # --- votes ---
        approved_rows = (await session.execute(
            select(Initiative).where(Initiative.status == InitiativeStatus.APPROVED)
        )).scalars().all()

        users_rows = (await session.execute(select(User))).scalars().all()
        users_map = {u.id: u for u in users_rows}
        residents = [u for u in users_rows if u.role == UserRole.RESIDENT]

        added = 0
        for resident in residents:
            for init in approved_rows[:4]:
                exists = (await session.execute(
                    select(Vote).where(
                        Vote.user_id == resident.id,
                        Vote.initiative_id == init.id,
                    )
                )).scalar_one_or_none()
                if exists:
                    continue
                session.add(Vote(user_id=resident.id, initiative_id=init.id))
                added += 1

        await session.commit()
        print(f"added votes: {added}")
        print("done")


async def clear():
    async with async_session_factory() as session:
        rv = await session.execute(delete(Vote))
        ri = await session.execute(delete(Initiative))
        ru = await session.execute(delete(User))
        await session.commit()
        print("cleared: "
              f"{rv.rowcount} votes, "
              f"{ri.rowcount} initiatives, "
              f"{ru.rowcount} users")


async def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "seed"
    if cmd == "seed":
        await seed()
    elif cmd == "clear":
        await clear()
    else:
        print(f"unknown command: {cmd!r}, use 'seed' or 'clear'")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
