from pydantic import BaseModel
from typing import Literal, Optional

class Analysis(BaseModel):
    kind: Literal["greeting", "question", "off_topic", "overview"]
    relation: Literal["single", "independent", "connected"] = "single" # listed before sub_queries so the model decides it first
    technical: bool = False
    sub_queries: list[str] = []


class Filters(BaseModel):
    project: Optional[str] = None
    domain: Optional[str] = None
    tech_tags: list[str] = []
    status: Optional[str] = None