from dataclasses import dataclass
from typing import Any

from models.enum import FactorGroup


@dataclass(frozen=True)
class Factor:
    """
    Фактор (биомаркер), влияющий на биологический возраст.

    Attributes:
        name (str): название фактора
        value (Any): значение
        group (Enum): NEGATIVE / NEUTRAL / POSITIVE
        description (str): пояснение
    """
    name: str
    value: Any
    group: FactorGroup  
    description: str

