from pydantic import BaseModel, Field


class StudentQuery(BaseModel):
    id: int | None = None
    name: str | None = None
    phone: str | None = None
    guardian_phone: str | None = None
    verified: bool | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
