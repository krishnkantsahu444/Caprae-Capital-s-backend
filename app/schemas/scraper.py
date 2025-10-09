from pydantic import BaseModel


class LeadRequest(BaseModel):
    query: str


class LeadResult(BaseModel):
    title: str
    url: str
    source: str
