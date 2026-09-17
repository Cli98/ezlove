import json
import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.community import CommunityElder
from app.models.view_event import ViewEvent
from app.models.canteen import CanteenRecord
from app.models.community_event import CommunityEvent
from app.models.alert import Alert
from app.models.care_relation import CareRelation
from app.models.care_moment import CareMoment
from app.models.user import User

logger = logging.getLogger("ezlove.risk_scoring")


async def calculate_risk_score(
    db: AsyncSession,
    elder_record: CommunityElder,
) -> dict:
    now = datetime.now()
    elder_id = elder_record.elder_id
    community_id = elder_record.community_id
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # ── 检测是否有家属绑定 ──
    has_family = (await db.execute(
        select(func.count()).where(
            CareRelation.elder_user_id == elder_id,
            CareRelation.status == "active",
        )
    )).scalar() > 0

    if has_family:
        weights = {
            "view_frequency": 0.25,
            "canteen_attendance": 0.20,
            "last_active": 0.25,
            "alert_density": 0.15,
            "base_risk": 0.15,
        }
    else:
        weights = {
            "view_frequency": 0.0,
            "canteen_attendance": 0.35,
            "last_active": 0.30,
            "alert_density": 0.15,
            "base_risk": 0.20,
        }

    # ── 维度①: 牵挂查看频率 ──
    moments_count = (await db.execute(
        select(func.count(CareMoment.id)).where(
            CareMoment.elder_id == elder_id,
            CareMoment.created_at >= seven_days_ago,
        )
    )).scalar() or 0

    viewed_count = 0
    if moments_count > 0:
        moments = (await db.execute(
            select(CareMoment.id).where(
                CareMoment.elder_id == elder_id,
                CareMoment.created_at >= seven_days_ago,
            )
        )).scalars().all()

        for mid in moments:
            v = (await db.execute(
                select(ViewEvent.id).where(
                    ViewEvent.moment_id == mid,
                    ViewEvent.viewer_id == elder_id,
                ).limit(1)
            )).scalar_one_or_none()
            if v:
                viewed_count += 1

    view_rate = viewed_count / moments_count if moments_count > 0 else 1.0
    score_view = int((1 - view_rate) * 100) if has_family else 0

    # ── 维度②: 食堂出勤频率 ──
    canteen_records = (await db.execute(
        select(CanteenRecord).where(
            CanteenRecord.community_id == community_id,
            CanteenRecord.parse_status == "success",
            CanteenRecord.created_at >= seven_days_ago,
        )
    )).scalars().all()

    elder_id_str = str(elder_id)
    total_meals = 0
    present_meals = 0
    for rec in canteen_records:
        for att in (rec.parsed_data or {}).get("attendees", []):
            if att.get("elder_id") == elder_id_str:
                total_meals += 1
                if att.get("present") is True:
                    present_meals += 1

    canteen_rate = present_meals / total_meals if total_meals > 0 else 1.0
    score_canteen = int((1 - canteen_rate) * 100)

    # ── 维度③: 最后活跃距今（多源：ViewEvent + 食堂 + 社区活动）──
    last_times = []

    last_view = (await db.execute(
        select(ViewEvent.viewed_at).where(
            ViewEvent.viewer_id == elder_id,
        ).order_by(desc(ViewEvent.viewed_at)).limit(1)
    )).scalar_one_or_none()
    if last_view:
        last_times.append(last_view)

    last_event = (await db.execute(
        select(CommunityEvent.created_at).where(
            CommunityEvent.elder_id == elder_id,
        ).order_by(desc(CommunityEvent.created_at)).limit(1)
    )).scalar_one_or_none()
    if last_event:
        last_times.append(last_event)

    elder_name_result = await db.execute(
        select(User.nickname).where(User.id == elder_id)
    )
    elder_name_for_canteen = elder_name_result.scalar_one_or_none()
    if elder_name_for_canteen:
        recent_canteen = (await db.execute(
            select(CanteenRecord.created_at).where(
                CanteenRecord.community_id == community_id,
                CanteenRecord.parse_status == "success",
            ).order_by(desc(CanteenRecord.created_at)).limit(20)
        )).scalars().all()
        for rec_time in recent_canteen:
            recs = (await db.execute(
                select(CanteenRecord).where(
                    CanteenRecord.community_id == community_id,
                    CanteenRecord.created_at == rec_time,
                )
            )).scalars().all()
            for r in recs:
                for att in (r.parsed_data or {}).get("attendees", []):
                    if att.get("elder_id") == elder_id_str and att.get("present") is True:
                        last_times.append(rec_time)
                        break
                else:
                    continue
                break
            else:
                continue
            break

    last_active = max(last_times) if last_times else None
    if not last_active:
        hours_inactive = 999
    else:
        hours_inactive = (now - last_active).total_seconds() / 3600

    if hours_inactive <= 6:
        score_inactive = 0
    elif hours_inactive <= 12:
        score_inactive = 30
    elif hours_inactive <= 24:
        score_inactive = 60
    else:
        score_inactive = 100

    # ── 维度④: 近期告警密度 ──
    alert_count = (await db.execute(
        select(func.count(Alert.id)).where(
            Alert.elder_id == elder_id,
            Alert.created_at >= thirty_days_ago,
        )
    )).scalar() or 0

    rel_ids = (await db.execute(
        select(CareRelation.id).where(CareRelation.elder_user_id == elder_id)
    )).scalars().all()
    if rel_ids:
        family_alert_count = (await db.execute(
            select(func.count(Alert.id)).where(
                Alert.care_relation_id.in_(rel_ids),
                Alert.created_at >= thirty_days_ago,
            )
        )).scalar() or 0
        alert_count += family_alert_count

    if alert_count == 0:
        score_alerts = 0
    elif alert_count <= 2:
        score_alerts = 30
    elif alert_count <= 5:
        score_alerts = 60
    else:
        score_alerts = 100

    # ── 维度⑤: 基础风险等级 ──
    base_scores = {"A": 80, "B": 50, "C": 20}
    score_base = base_scores.get(elder_record.care_level, 20)

    # ── 加权总分 ──
    total_score = int(
        score_view * weights["view_frequency"]
        + score_canteen * weights["canteen_attendance"]
        + score_inactive * weights["last_active"]
        + score_alerts * weights["alert_density"]
        + score_base * weights["base_risk"]
    )
    total_score = min(100, max(0, total_score))

    if total_score <= 30:
        risk_level = "normal"
    elif total_score <= 60:
        risk_level = "attention"
    elif total_score <= 80:
        risk_level = "warning"
    else:
        risk_level = "critical"

    details = {
        "has_family": has_family,
        "view_frequency": {"score": score_view, "weight": weights["view_frequency"], "view_rate": round(view_rate, 2), "moments": moments_count, "viewed": viewed_count},
        "canteen_attendance": {"score": score_canteen, "weight": weights["canteen_attendance"], "rate": round(canteen_rate, 2), "total_meals": total_meals, "present": present_meals},
        "last_active": {"score": score_inactive, "weight": weights["last_active"], "hours_inactive": round(hours_inactive, 1)},
        "alert_density": {"score": score_alerts, "weight": weights["alert_density"], "count_30d": alert_count},
        "base_risk": {"score": score_base, "weight": weights["base_risk"], "care_level": elder_record.care_level},
    }

    # 写回
    elder_record.risk_score = total_score
    elder_record.risk_level = risk_level
    elder_record.risk_calculated_at = now
    elder_record.risk_details = details

    # 每日快照 upsert
    from app.models.risk_snapshot import RiskScoreSnapshot
    today = now.date() if hasattr(now, 'date') else now
    existing_snap = (await db.execute(
        select(RiskScoreSnapshot).where(
            RiskScoreSnapshot.elder_id == elder_record.id,
            RiskScoreSnapshot.snapshot_date == today,
        )
    )).scalar_one_or_none()
    if existing_snap:
        existing_snap.score = total_score
        existing_snap.level = risk_level
    else:
        db.add(RiskScoreSnapshot(
            elder_id=elder_record.id,
            community_id=elder_record.community_id,
            score=total_score,
            level=risk_level,
            snapshot_date=today,
        ))

    return {
        "risk_score": total_score,
        "risk_level": risk_level,
        "risk_details": details,
    }


async def recalculate_all(
    db: AsyncSession,
    community_id: uuid.UUID,
) -> int:
    elders = (await db.execute(
        select(CommunityElder).where(CommunityElder.community_id == community_id)
    )).scalars().all()

    count = 0
    for elder in elders:
        try:
            await calculate_risk_score(db, elder)
            count += 1
        except Exception:
            logger.exception(f"计算老人 {elder.elder_id} 风险分数失败")

    await db.flush()
    return count


async def get_ai_analysis(
    db: AsyncSession,
    elder_record: CommunityElder,
) -> dict:
    from app.config import settings

    elder_name_result = await db.execute(
        select(User.nickname).where(User.id == elder_record.elder_id)
    )
    elder_name = elder_name_result.scalar_one_or_none() or "未知"

    risk_details = elder_record.risk_details or {}
    risk_score = elder_record.risk_score or 0

    has_family = risk_details.get("has_family", True)
    family_line = (
        f"- 牵挂查看: 7天内查看率 {risk_details.get('view_frequency', {}).get('view_rate', 'N/A')}"
        if has_family
        else "- 牵挂查看: 无家属绑定（此维度已跳过）"
    )

    prompt = f"""你是社区老人关怀助手。请根据以下数据分析{elder_name}的近期状况，给出简短评估和建议。

风险分数: {risk_score}/100
家属绑定: {'有' if has_family else '无（独居老人）'}
各维度详情:
{family_line}
- 食堂出勤: {risk_details.get('canteen_attendance', {}).get('present', 0)}/{risk_details.get('canteen_attendance', {}).get('total_meals', 0)} 餐
- 最后活跃: {risk_details.get('last_active', {}).get('hours_inactive', 'N/A')} 小时前
- 30天告警: {risk_details.get('alert_density', {}).get('count_30d', 0)} 次
- 护理等级: {risk_details.get('base_risk', {}).get('care_level', 'C')}

请用 JSON 格式回复：
{{"summary": "一句话总结", "trend": "improving/stable/deteriorating", "concern_points": ["关注点1"], "suggested_action": "建议行动", "confidence": 0.0-1.0}}"""

    from app.utils.llm import get_client, get_model

    client = get_client()
    if not client:
        return {
            "summary": f"{elder_name}的风险分数为{risk_score}分，请关注其日常活动状况。",
            "trend": "stable",
            "concern_points": [],
            "suggested_action": "建议定期走访确认老人状况",
            "confidence": 0.5,
        }

    try:
        import re

        response = await client.chat.completions.create(
            model=get_model(),
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text.strip())
    except Exception as e:
        logger.exception("AI 分析调用失败")
        return {
            "summary": f"{elder_name}的风险分数为{risk_score}分。",
            "trend": "stable",
            "concern_points": [],
            "suggested_action": "AI 分析暂时不可用，建议人工评估",
            "confidence": 0.0,
        }
