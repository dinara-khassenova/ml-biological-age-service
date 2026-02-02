from __future__ import annotations

from datetime import datetime

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from models.enum import TaskStatus

class PredictIn(BaseModel):
    model_id: int = Field(default=1, gt=0)
    answers: Dict[str, Any] = Field(default_factory=dict)


class TaskDraftIn(BaseModel):
    '''
    Черновик ответов, можно создавать даже с пустыми answers
    '''
    model_id: int = Field(default=1, gt=0)
    answers: Dict[str, Any] = Field(default_factory=dict)


# по заданию /predict возвращает только task_id (uuid)
class PredictOut(BaseModel):
    task_id: str


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    external_id: str
    
    user_id: int
    model_id: int
    status: TaskStatus
    charged_amount: Optional[int] = None
    validation_errors: List[Dict[str, Any]] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    worker_id: Optional[str] = None


TaskHistoryOut = TaskOut
