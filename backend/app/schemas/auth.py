from pydantic import BaseModel


class WxLoginRequest(BaseModel):
    code: str


class DevLoginRequest(BaseModel):
    openid: str = "dev_test_user"


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict
