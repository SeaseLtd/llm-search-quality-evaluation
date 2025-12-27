from pydantic import BaseModel


# Generic message
class Message(BaseModel):
    message: str

