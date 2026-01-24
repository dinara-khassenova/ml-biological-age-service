from dataclasses import dataclass
from typing import Any

from constants import FACTOR_GROUPS


@dataclass(frozen=True)
class Factor:
    """
    Фактор (биомаркер), влияющий на биологический возраст.

    Attributes:
        name (str): название фактора
        value (Any): значение
        group (str): NEGATIVE / NEUTRAL / POSITIVE
        description (str): пояснение
    """
    name: str
    value: Any
    group: str
    description: str

    def __post_init__(self) -> None:
        if self.group not in FACTOR_GROUPS:
            raise ValueError("group должен быть 'NEGATIVE', 'NEUTRAL' или 'POSITIVE'")
