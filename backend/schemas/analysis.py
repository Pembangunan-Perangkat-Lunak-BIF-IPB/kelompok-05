from pydantic import BaseModel

class VisibilityUpdateRequest(BaseModel):
    visibility: str  # "PUBLIC" atau "PRIVATE"
    