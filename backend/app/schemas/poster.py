from pydantic import BaseModel


class PosterGenerateRequest(BaseModel):
    image_url: str
    user_text: str | None = None
    elder_id: str | None = None


class CaptionItem(BaseModel):
    tag: str
    text: str


class PosterVariant(BaseModel):
    template_name: str
    poster_url: str
    caption: str
    label: str
    desc: str


class PosterGenerateResponse(BaseModel):
    variants: list[PosterVariant]
    recommended_index: int
    photo_description: str | None = None


class PosterRenderRequest(BaseModel):
    image_url: str
    template_name: str
    caption: str
    sender_name: str | None = None


class PosterRenderResponse(BaseModel):
    poster_url: str
