from pydantic import UUID4, BaseModel, EmailStr


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: UUID4

    # class Config:
    #     orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str
