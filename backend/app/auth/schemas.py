from pydantic import UUID4, BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: UUID4
    email: EmailStr

    # class Config:
    #     orm_mode = True
