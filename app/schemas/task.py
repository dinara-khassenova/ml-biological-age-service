from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from models.enum import TaskStatus

class PredictIn(BaseModel):
    user_id: int = Field(gt=0)
    model_id: int = Field(default=1, gt=0)
    answers: Dict[str, Any]


class TaskDraftIn(BaseModel):
    '''
    Черновик ответов, можно создавать даже с пустыми answers
    '''
    user_id: int = Field(gt=0)
    model_id: int = Field(default=1, gt=0)
    answers: Dict[str, Any] = Field(default_factory=dict)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    model_id: int
    status: TaskStatus
    charged_amount: Optional[int] = None
    validation_errors: List[Dict[str, Any]] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


TaskHistoryOut = TaskOut
