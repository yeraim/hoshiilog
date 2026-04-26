from pydantic import UUID4, BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserChangePassword(BaseModel):
    old_password: str
    new_password: str


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID4


class Token(BaseModel):
    access_token: str
    token_type: str
