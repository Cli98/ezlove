# 公益志愿同学名单：人数少、变动低频，直接内置维护（列表顺序即展示顺序）
_CONTRIBUTORS: list[dict] = [
    {"name": "何宪琳", "wechat_id": "likeVisitor", "note": None},
    {"name": "郭昱希", "wechat_id": "hhh98051422", "note": None},
    {"name": "李长霖", "wechat_id": "hichanglin", "note": None},
    {"name": "黄祈安", "wechat_id": "18107126654", "note": None},
]


def list_active_contributors() -> list[dict]:
    """贡献页名单：内置常量，顺序即展示顺序"""
    return list(_CONTRIBUTORS)
