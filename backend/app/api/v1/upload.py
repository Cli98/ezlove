import uuid
from pathlib import Path
from asyncio import get_event_loop
from functools import partial

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["upload"])

UPLOAD_DIR = Path(__file__).resolve().parents[3] / "static" / "uploads"

# ── 图片 ──
IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
IMAGE_MAGIC = {
    b"\xff\xd8\xff": "jpg",
    b"\x89PNG": "png",
    b"GIF": "gif",
    b"RIFF": "webp",       # WebP (RIFF....WEBP)
}
MAX_IMAGE_SIZE = 5 * 1024 * 1024     # 5 MB

# ── 视频 ──
VIDEO_TYPES = {"video/mp4", "video/webm"}
VIDEO_MAGIC = {
    b"\x00\x00\x00": "mp4",           # ftyp box（ftyp 在第 4-7 字节）
    b"\x1a\x45\xdf\xa3": "webm",      # EBML header（WebM/MKV）
}
MAX_VIDEO_SIZE = 20 * 1024 * 1024    # 20 MB

# 合并
ALLOWED_TYPES = IMAGE_TYPES | VIDEO_TYPES
CHUNK_SIZE = 1024 * 1024  # 1MB


def _detect_type(header: bytes) -> tuple[str, str] | None:
    """根据魔数检测文件类型，返回 (扩展名, 类别 'image'|'video')。"""
    # 图片
    for magic, ext in IMAGE_MAGIC.items():
        if header.startswith(magic):
            return ext, "image"
    # 视频 — MP4 的 ftyp 在第 4 字节
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "mp4", "video"
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm", "video"
    return None


def _write_file(filepath: Path, content: bytes) -> None:
    with open(filepath, "wb") as f:
        f.write(content)


@router.post("")
async def upload_file(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    is_video = file.content_type in VIDEO_TYPES
    is_image = file.content_type in IMAGE_TYPES

    if not is_image and not is_video:
        raise HTTPException(status_code=400, detail="仅支持 jpg/png/gif/webp 图片或 mp4/webm 视频")

    max_size = MAX_VIDEO_SIZE if is_video else MAX_IMAGE_SIZE
    label = "视频" if is_video else "图片"

    # 分块读取并校验大小
    chunks: list[bytes] = []
    total_size = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_size:
            raise HTTPException(status_code=400, detail=f"{label}不能超过 {max_size // (1024*1024)}MB")
        chunks.append(chunk)
    content = b"".join(chunks)

    # 魔数校验
    if len(content) < 12:
        raise HTTPException(status_code=400, detail="文件内容无效")
    detected = _detect_type(content)
    if detected is None:
        raise HTTPException(status_code=400, detail="文件内容与声明的类型不匹配")
    detected_ext, detected_cat = detected
    if (is_video and detected_cat != "video") or (is_image and detected_cat != "image"):
        raise HTTPException(status_code=400, detail="文件内容与声明的类型不匹配")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{detected_ext}"
    filepath = UPLOAD_DIR / filename

    loop = get_event_loop()
    await loop.run_in_executor(None, partial(_write_file, filepath, content))

    return {"url": f"/static/uploads/{filename}", "type": detected_cat}
