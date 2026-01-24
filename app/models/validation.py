from dataclasses import dataclass

@dataclass(frozen=True)
class ValidationError:
    """
    Ошибка валидации входных в сервис данных по задаче.

    Attributes:
        field_name (str): название поля с ошибкой
        message (str): описание ошибки
    """
    field_name: str
    message: str

    def __str__(self) -> str:
        return f"Поле '{self.field_name}': {self.message}"