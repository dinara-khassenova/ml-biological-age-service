from typing import List
from pydantic import BaseModel, ConfigDict

class MLModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price_per_task: int
    feature_names: List[str]
