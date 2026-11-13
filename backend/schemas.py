from pydantic import BaseModel, Field

class CustomerInput(BaseModel):
    external_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    phone: str = Field(min_length=1, max_length=40)

class MessageInput(BaseModel):
    customer: CustomerInput
    text: str = Field(min_length=1, max_length=10000)

class LoginInput(BaseModel):
    email: str
    password: str

class ApproveInput(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
