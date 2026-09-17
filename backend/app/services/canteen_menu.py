import json
import re
import uuid
import logging
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canteen_menu import CanteenMenu
from app.utils.llm import get_client, get_model

logger = logging.getLogger("ezlove.canteen_menu")

SEASONS = {1: "冬季", 2: "冬季", 3: "春季", 4: "春季", 5: "春季",
           6: "夏季", 7: "夏季", 8: "夏季", 9: "秋季", 10: "秋季",
           11: "秋季", 12: "冬季"}

MEAL_LABELS = {"lunch": "午餐", "dinner": "晚餐"}


async def generate_menu(
    db: AsyncSession,
    community_id: uuid.UUID,
    menu_date: date,
    meal_type: str = "lunch",
) -> CanteenMenu:
    existing = (await db.execute(
        select(CanteenMenu).where(
            CanteenMenu.community_id == community_id,
            CanteenMenu.menu_date == menu_date,
            CanteenMenu.meal_type == meal_type,
        )
    )).scalar_one_or_none()
    if existing:
        return existing

    recent = (await db.execute(
        select(CanteenMenu).where(
            CanteenMenu.community_id == community_id,
            CanteenMenu.menu_date < menu_date,
        ).order_by(CanteenMenu.menu_date.desc()).limit(5)
    )).scalars().all()

    recent_context = ""
    if recent:
        lines = []
        for m in recent:
            names = [d["name"] for d in (m.dishes or {}).get("items", [])]
            lines.append(f"- {m.menu_date} {MEAL_LABELS.get(m.meal_type, m.meal_type)}: {', '.join(names)}")
        recent_context = "\n".join(lines)
    else:
        recent_context = "暂无历史菜单"

    season = SEASONS.get(menu_date.month, "夏季")
    meal_label = MEAL_LABELS.get(meal_type, "午餐")

    system_prompt = f"""你是社区老年食堂的营养配餐助手。请为{menu_date.isoformat()}的{meal_label}生成一份适合老年人的菜单。

要求：
1. 季节：当前是{season}，选择当季食材
2. 营养：注重低盐低油，易消化，富含蛋白质和钙
3. 多样性：避免与最近几天的菜品重复
4. 数量：2-3道荤菜，2-3道素菜，1道汤，1种主食

最近几天的菜单（避免重复）：
{recent_context}

请严格按以下JSON格式返回，不要多余文字：
{{"items":[{{"name":"菜名","description":"简短描述（营养亮点）","category":"荤菜或素菜"}}],"soup":"汤名 — 简短描述","staple":"主食描述","summary":"一句话总结今日菜品特色"}}"""

    client = get_client()
    if not client:
        dishes = _default_menu(season)
    else:
        try:
            response = await client.chat.completions.create(
                model=get_model(),
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请生成{menu_date.isoformat()} {meal_label}的菜单"},
                ],
            )
            text = response.choices[0].message.content or ""
            match = re.search(r'```(?:json)?\s*(.*?)```', text, re.DOTALL)
            if match:
                text = match.group(1)
            dishes = json.loads(text.strip())
        except Exception as e:
            logger.warning("AI menu generation failed: %s", e)
            dishes = _default_menu(season)

    menu = CanteenMenu(
        id=uuid.uuid4(),
        community_id=community_id,
        menu_date=menu_date,
        meal_type=meal_type,
        dishes=dishes,
        status="draft",
        generated_by="ai" if client else "manual",
    )
    db.add(menu)
    await db.commit()
    await db.refresh(menu)
    return menu


async def get_today_menu(
    db: AsyncSession,
    community_id: uuid.UUID,
) -> list[CanteenMenu]:
    result = await db.execute(
        select(CanteenMenu).where(
            CanteenMenu.community_id == community_id,
            CanteenMenu.menu_date == date.today(),
            CanteenMenu.status == "published",
        ).order_by(CanteenMenu.meal_type)
    )
    return list(result.scalars().all())


async def list_menus(
    db: AsyncSession,
    community_id: uuid.UUID,
    limit: int = 14,
) -> list[CanteenMenu]:
    result = await db.execute(
        select(CanteenMenu).where(
            CanteenMenu.community_id == community_id,
        ).order_by(CanteenMenu.menu_date.desc(), CanteenMenu.meal_type).limit(limit)
    )
    return list(result.scalars().all())


async def update_menu_dishes(
    db: AsyncSession,
    menu_id: uuid.UUID,
    community_id: uuid.UUID,
    dishes: dict,
) -> CanteenMenu | None:
    menu = (await db.execute(
        select(CanteenMenu).where(
            CanteenMenu.id == menu_id,
            CanteenMenu.community_id == community_id,
        )
    )).scalar_one_or_none()
    if not menu:
        return None
    menu.dishes = dishes
    await db.commit()
    await db.refresh(menu)
    return menu


async def publish_menu(
    db: AsyncSession,
    menu_id: uuid.UUID,
    community_id: uuid.UUID,
    worker_id: uuid.UUID,
) -> CanteenMenu | None:
    menu = (await db.execute(
        select(CanteenMenu).where(
            CanteenMenu.id == menu_id,
            CanteenMenu.community_id == community_id,
        )
    )).scalar_one_or_none()
    if not menu:
        return None
    menu.status = "published"
    menu.published_by = worker_id
    menu.published_at = datetime.now()
    await db.commit()
    await db.refresh(menu)
    return menu


async def delete_menu(
    db: AsyncSession,
    menu_id: uuid.UUID,
    community_id: uuid.UUID,
) -> bool:
    menu = (await db.execute(
        select(CanteenMenu).where(
            CanteenMenu.id == menu_id,
            CanteenMenu.community_id == community_id,
        )
    )).scalar_one_or_none()
    if not menu:
        return False
    await db.delete(menu)
    await db.commit()
    return True


def _default_menu(season: str) -> dict:
    if season == "夏季":
        return {
            "items": [
                {"name": "清蒸鲈鱼", "description": "富含蛋白质，少油清淡", "category": "荤菜"},
                {"name": "番茄炒蛋", "description": "维C丰富，开胃下饭", "category": "荤菜"},
                {"name": "蒜蓉西兰花", "description": "高纤维，增强免疫", "category": "素菜"},
                {"name": "凉拌黄瓜", "description": "清热解暑，爽口开胃", "category": "素菜"},
            ],
            "soup": "冬瓜排骨汤 — 清热消暑，补钙养胃",
            "staple": "杂粮饭（大米+小米+红豆）",
            "summary": "夏日清淡菜品，注重消暑开胃与营养均衡",
        }
    return {
        "items": [
            {"name": "红烧肉", "description": "软烂入味，补充能量", "category": "荤菜"},
            {"name": "清炒时蔬", "description": "当季新鲜蔬菜", "category": "素菜"},
            {"name": "蒸蛋羹", "description": "易消化，富含蛋白", "category": "荤菜"},
            {"name": "素炒豆芽", "description": "清脆爽口，维C丰富", "category": "素菜"},
        ],
        "soup": "萝卜排骨汤 — 暖胃滋补",
        "staple": "米饭",
        "summary": "家常营养搭配，温暖可口",
    }
