from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ====== Константы/допустимые значения ======
TASK_STATUSES = {"CREATED", "VALIDATED", "PROCESSING", "DONE", "FAILED"}
TX_TYPES = {"TOPUP", "CHARGE"}
USER_ROLES = {"USER", "ADMIN"}
FACTOR_GROUPS = {"NEGATIVE", "NEUTRAL", "POSITIVE"}

# ====== Доменные (бизнесовые) сущности (Domain Entities) ======
@dataclass
class User:
    """
    Пользователь ML сервиса.

    Attributes:
        id (int): уникальный идентификатор пользователя
        email (str): email пользователя
        password (str): пароль пользователя (упрощенно для задания)
        role (str): USER / ADMIN
        wallet (Optional[Wallet]): кошелек пользователя ML сервиса
    """
    id: int
    email: str
    password: str
    role: str = "USER"
    wallet: Optional["Wallet"] = None

    def __post_init__(self) -> None:
        self._validate_email()
        
        if self.role not in USER_ROLES:
            raise ValueError("Некорректная роль") 
        
        if self.wallet is not None and self.wallet.user_id != self.id:
            raise ValueError("wallet.user_id должен совпадать с user.id") 
        
    def _validate_email(self) -> None:
        """Минимальная валидация email (упрощённо, без regex как в лекции)."""
        if "@" not in self.email or "." not in self.email:
            raise ValueError("Некорректный email")
      
@dataclass
class Wallet:
    """
    Кошелек пользователя (баланс в кредитах).

    Attributes:
        user_id (int): идентификатор пользователя
        balance (int): текущий баланс
    """
    user_id: int
    balance: int = 0

    def __post_init__(self) -> None:
        if self.balance < 0:
            raise ValueError("Баланс не может быть отрицательным")

    def topup(self, amount: int) -> None:
        """Пополнение баланса на amount кредитов."""
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть > 0")
        self.balance += amount

    def can_pay(self, amount: int) -> bool:
        """Проверка достаточности средств."""
        if amount < 0:
            raise ValueError("Цена не может быть отрицательной")
        return self.balance >= amount

    def charge(self, amount: int) -> None:
        """
        Списание средств.

        Требование по ТЗ:
        списание должно происходить только после успешного выполнения запроса.
        Это правило реализуется на уровне сервиса,
        а Wallet отвечает только за корректное списание.
        """
        if amount <= 0:
            raise ValueError("Сумма списания должна быть > 0")
        if not self.can_pay(amount):
            raise ValueError("Недостаточно средств")
        self.balance -= amount


@dataclass(frozen=True)
class Transaction:
    """
    Транзакция - запись истории операций по балансу.

    Attributes:
        id (int): идентификатор транзакции
        user_id (int): идентификатор пользователя
        tx_type (str): тип операции (TOPUP / CHARGE)
        amount (int): сумма в кредитах
        task_id (Optional[int]): ссылка на задачу (для CHARGE)
        created_at (datetime): дата/время транзакции (UTC)
    """
    id: int
    user_id: int
    tx_type: str
    amount: int
    task_id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.tx_type not in TX_TYPES:
            raise ValueError(f"Некорректный тип транзакции: {self.tx_type}")
        if self.amount <= 0:
            raise ValueError("Сумма транзакции должна быть > 0")


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


@dataclass
class AssessmentResult:
    """
    Результат ML расчёта.

    Attributes:
        biological_age (float): рассчитанный биологический возраст
        factors (List[Factor]): список факторов
        validation_errors (List[ValidationError]): ошибки валидации (если были)
    """
    biological_age: float
    factors: List[Factor]
    validation_errors: List[ValidationError] = field(default_factory=list)


@dataclass
class AssessmentTask:
    """
    Заявка пользователя на расчёт биологического возраста.

    Правила:
    - ответы можно добавлять только до начала обработки
    - обработка начинается только после успешной валидации
    - оплата происходит только после успешного завершения (по ТЗ)

    Attributes:
        id (int): идентификатор задачи
        user_id (int): идентификатор пользователя
        model_id (int): идентификатор ML модели (по начинаем с одной модели)
        answers (Dict[str, Any]): входные данные анкеты
        validation_errors (List[ValidationError]): ошибки валидации
        charged_amount (Optional[int]): сколько списали (фиксируем факт списания)
        status (str): CREATED -> VALIDATED -> PROCESSING -> DONE / FAILED
        result (Optional[AssessmentResult]): результат
        error_message (Optional[str]): текст ошибки выполнения (если FAILED)
        created_at (datetime): дата создания (UTC)
    """
    id: int
    user_id: int
    model_id: int 
    answers: Dict[str, Any] = field(default_factory=dict)
    validation_errors: List[ValidationError] = field(default_factory=list)
    charged_amount: Optional[int] = None
    status: str = "CREATED"    # CREATED -> VALIDATED -> PROCESSING -> DONE/FAILED
    result: Optional[AssessmentResult] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.status not in TASK_STATUSES:
            raise ValueError("Некорректный статус задачи")

    def add_answer(self, field_name: str, value: Any) -> None:
        """Добавляет/обновляет одно поле анкеты."""
        if self.status != "CREATED":
            raise ValueError("Нельзя изменять ответы после начала обработки")
        self.answers[field_name] = value

    def set_validation_result(self, is_valid: bool, errors: List["ValidationError"]) -> None:
        """Если валидацию данные не прошли, пока оставляем статус CREATED для возможной корректировки данных"""
        if self.status != "CREATED":
            raise ValueError("Валидацию можно сохранить только в статусе CREATED")
        self.validation_errors = list(errors)
        self.status = "VALIDATED" if is_valid else "CREATED"

    def start_processing(self) -> None:
        if self.status != "VALIDATED":
            raise ValueError("start_processing() возможен только после успешной валидации")
        self.status = "PROCESSING"

    def set_result(self, result: "AssessmentResult", charged_amount: int) -> None:
        if self.status != "PROCESSING":
            raise ValueError("set_result() только из PROCESSING")
        self.result = result
        self.charged_amount = charged_amount
        self.status = "DONE"

    def set_error(self, message: str) -> None:
        if self.status not in {"CREATED", "VALIDATED", "PROCESSING"}:
            raise ValueError("set_error() допускается только из CREATED/VALIDATED/PROCESSING")
        self.error_message = message
        self.status = "FAILED"
  
# ====== MLModel как доменный объект с контрактами и реализациями валидатора и предиктора ======
# ====== Позднее будет разбито на отдельные файлы  ====

class Validator(ABC):
    """Абстрактный базовый класс для валидаторов данных."""

    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """Валидация одной записи."""
        raise NotImplementedError


class Predictor(ABC):
    """Абстрактный базовый класс для предикторов (ML моделей)."""

    @abstractmethod
    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        """Предсказание по одной анкете."""
        raise NotImplementedError


class BioAgeDataValidator(Validator):
    """
    Валидатор входных данных для расчёта биологического возраста.

    Примечание: Несколько признаков для примера.
    """

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        errors: List[ValidationError] = []

        # age
        if "age" in data:
            age = data["age"]
            if not isinstance(age, (int, float)) or age < 0 or age > 120:
                errors.append(ValidationError("age", "Возраст должен быть в диапазоне от 0 до 120"))
        else:
            errors.append(ValidationError("age", "Поле 'age' обязательно"))

        # bmi
        if "bmi" in data:
            bmi = data["bmi"]
            if not isinstance(bmi, (int, float)) or bmi < 10 or bmi > 60:
                errors.append(ValidationError("bmi", "BMI должен быть в диапазоне от 10 до 60"))

        # glucose
        if "glucose" in data:
            glucose = data["glucose"]
            if not isinstance(glucose, (int, float)) or glucose < 0:
                errors.append(ValidationError("glucose", "Уровень глюкозы в крови должен быть неотрицательным числом"))

        return (len(errors) == 0, errors)


class BioAgePredictorStub(Predictor):
    """Заглушка предиктора (вместо реальной ML модели)."""

    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        factors = [
            Factor(
                name="bmi",
                value=answers.get("bmi"),
                group="NEUTRAL",
                description="Индекс массы тела - в пределах нормы",
            ),
            Factor(
                name="glucose",
                value=answers.get("glucose"),
                group="POSITIVE",
                description="Уровень глюкозы - оптимальный",
            ),
        ]

        age = answers.get("age", 40)
        biological_age = age + (answers.get("bmi", 25) - 22) * 0.5

        return AssessmentResult(
            biological_age=round(float(biological_age), 1),
            factors=factors,
        )


class BioAgePredictorML(Predictor):
    """
    Реальный ML предиктор (пример расширения через наследование).
    В будущем здесь будет загрузка модели и предсказание.
    """

    def __init__(self, model_path: str):
        self.model_path = model_path
        # self.model = load_model(model_path)

    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        # features = self._prepare_features(answers)
        # prediction = self.model.predict(features)
        # return ...
        return BioAgePredictorStub().predict(answers)
    
@dataclass
class MLModel:
    """
    ML модель, доступная в сервисе.

    Attributes:
        id (int): идентификатор модели
        name (str): название модели
        price_per_task (int): стоимость одного расчёта в кредитах
        feature_names (List[str]): список признаков, ожидаемых моделью
        validator (Validator): валидатор входных данных
        predictor (Predictor): предиктор (заглушка / реальная модель)
    """
    id: int
    name: str
    feature_names: List[str]
    price_per_task: int = 25
    validator: Validator = field(default_factory=BioAgeDataValidator)
    predictor: Predictor = field(default_factory=BioAgePredictorStub)

    def __post_init__(self) -> None:
        if not self.feature_names:
            raise ValueError("feature_names не должен быть пустым")
        if self.price_per_task <= 0:
            raise ValueError("price_per_task должен быть > 0")

    def validate(self, answers: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
        """Делегирует валидацию валидатору модели."""
        return self.validator.validate(answers)

    def predict(self, answers: Dict[str, Any]) -> AssessmentResult:
        """Делегирует предсказание предиктору модели."""
        return self.predictor.predict(answers)

    
# ===================== Repository (in-memory для пункта 1 задания) =====================

class Repository:
    """
    In-memory репозиторий для этапа 1.
    На этапе 2 будет разбиение на отдельные репозитории и/или БД/ORM.
    """
    
    def __init__(self) -> None:
        self._users: Dict[int, User] = {}
        self._tasks: Dict[int, AssessmentTask] = {}
        self._transactions: List[Transaction] = []
        self._tx_id: int = 1

    # --- users ---
    def add_user(self, user: User) -> None:
        if user.id in self._users:
            raise ValueError("User с таким id уже существует")
        if any(u.email == user.email for u in self._users.values()):
            raise ValueError("Email уже используется")
        self._users[user.id] = user

    def get_user(self, user_id: int) -> User:
        user = self._users.get(user_id)
        if user is None:
            raise ValueError("Пользователь не найден")
        return user

    def find_user_by_email(self, email: str) -> Optional[User]:
        for u in self._users.values():
            if u.email == email:
                return u
        return None

    # --- tasks ---
    def add_task(self, task: AssessmentTask) -> None:
        if task.id in self._tasks:
            raise ValueError("Task с таким id уже существует")
        self._tasks[task.id] = task

    def update_task(self, task: AssessmentTask) -> None:
        if task.id not in self._tasks:
            raise ValueError("Task не найден")
        self._tasks[task.id] = task

    def user_tasks(self, user_id: int) -> List[AssessmentTask]:
        return [t for t in self._tasks.values() if t.user_id == user_id]

    # --- transactions ---
    def create_transaction(
        self,
        user_id: int,
        tx_type: str,
        amount: int,
        task_id: Optional[int] = None,
    ) -> Transaction:
        tx = Transaction(
            id=self._tx_id,
            user_id=user_id,
            tx_type=tx_type,
            amount=amount,
            task_id=task_id,
        )
        self._tx_id += 1
        self._transactions.append(tx)
        return tx

    def user_transactions(self, user_id: int) -> List[Transaction]:
        return [t for t in self._transactions if t.user_id == user_id]

    def all_transactions(self) -> List[Transaction]:
        return list(self._transactions)


# ====== Use-case сервисы (ключевые бизнес-правила) ======

class RegAuthService:
    """
    Упрощенно регистрация/авторизация. 
    """

    def __init__(self, repo: Repository):
        self.repo = repo

    def register(self, user_id: int, email: str, password: str, role: str = "USER") -> User:
        email_norm = email.strip().lower()

        if len(password) < 8:
            raise ValueError("Пароль должен быть не короче 8 символов")
        if role not in USER_ROLES:
            raise ValueError("Некорректная роль")
        
        wallet = Wallet(user_id=user_id) if role == "USER" else None
        user = User(id=user_id, email=email_norm, password=password, role=role, wallet=wallet)

        self.repo.add_user(user)
        return user

    def login(self, email: str, password: str) -> User:
        email_norm = email.strip().lower()
        user = self.repo.find_user_by_email(email_norm)
        if user is None or user.password != password:
            raise ValueError("Неверный email или пароль")
        return user


class BillingService:
    """
    Баланс + транзакции (история).
    Правило: любые изменения баланса сопровождаются Transaction.
    """
    def __init__(self, repo: Repository):
        self.repo = repo

    def _require_wallet(self, user_id: int) -> Wallet:
        user = self.repo.get_user(user_id)
        if user.wallet is None:
            raise ValueError("У пользователя нет кошелька")
        if user.wallet.user_id != user.id:
            raise ValueError("Несогласованность: wallet.user_id != user.id")
        return user.wallet

    def balance(self, user_id: int) -> int:
        return self._require_wallet(user_id).balance

    def can_pay(self, user_id: int, amount: int) -> bool:
        return self._require_wallet(user_id).can_pay(amount)

    def topup(self, user_id: int, amount: int) -> Transaction:
        wallet = self._require_wallet(user_id)
        wallet.topup(amount)
        return self.repo.create_transaction(user_id=user_id, tx_type="TOPUP", amount=amount)

    def charge_after_success(self, user_id: int, amount: int, task_id: int) -> Transaction:
        """
        Ключевое бизнес-правило:
        списание вызывается сервисом только ПОСЛЕ успешного predict().
        """
        wallet = self._require_wallet(user_id)
        wallet.charge(amount)
        return self.repo.create_transaction(user_id=user_id, tx_type="CHARGE", amount=amount, task_id=task_id)


class TaskService:
    """
    Главный use-case: validate -> predict -> charge -> history.

    Бизнес-правила:
    1) Проверка баланса ДО запуска
    2) Если невалидно — не предсказываем и не списываем
    3) Списание только после успешного predict()
    4) История: task + transaction сохраняются в Repository
    """
    def __init__(self, repo: Repository, model: MLModel, billing: BillingService):
        self.repo = repo
        self.model = model
        self.billing = billing

    def run_task(self, task: AssessmentTask) -> AssessmentTask:
        # История входных данных: сохраняем задачу сразу
        self.repo.add_task(task)

        # 1) Проверка баланса до запуска
        if not self.billing.can_pay(task.user_id, self.model.price_per_task):
            task.set_error("Недостаточно средств")
            self.repo.update_task(task)
            return task

        # 2) Валидация: если не прошла — сохраняем ошибки и возвращаем.
        ok, errors = self.model.validate(task.answers)
        task.set_validation_result(ok, errors)
        self.repo.update_task(task)

        if not ok:
            return task
        
        # 3) Предсказание
        try:
            task.start_processing()
            self.repo.update_task(task)

            result = self.model.predict(task.answers)
        except Exception as ex:
            task.set_error(f"Ошибка предсказания: {ex}")
            self.repo.update_task(task)
            return task

        # 4) Успех -> списание + транзакция + фиксация charged_amount
        try:
            self.billing.charge_after_success(task.user_id, self.model.price_per_task, task.id)
        except Exception as ex:
            # предсказание есть, но списать не удалось => считаем задачу FAILED
            task.set_error(f"Не удалось списать кредиты: {ex}")
            self.repo.update_task(task)
            return task

        task.set_result(result, charged_amount=self.model.price_per_task)
        self.repo.update_task(task)
        return task


class AdminService:
    """
    Админ — это роль пользователя (не отдельный класс).
    """
    def __init__(self, repo: Repository, billing: BillingService):
        self.repo = repo
        self.billing = billing

    def _require_admin(self, admin_user_id: int) -> User:
        admin = self.repo.get_user(admin_user_id)
        if admin.role != "ADMIN":
            raise PermissionError("Нужен ADMIN")
        return admin

    def topup_user(self, admin_user_id: int, target_user_id: int, amount: int) -> Transaction:
        self._require_admin(admin_user_id)
        return self.billing.topup(target_user_id, amount)

    def all_transactions(self, admin_user_id: int) -> List[Transaction]:
        self._require_admin(admin_user_id)
        return self.repo.all_transactions()
    

# ====== DEMO / quick check ======
# Этот код можно вставить в самый низ файла и запустить:
# python your_file.py

def demo() -> None:
    repo = Repository()

    # 1) Регистрация (кошелек создаётся внуptтри register())
    auth = RegAuthService(repo)
    user = auth.register(user_id=1, email="user@test.com", password="password1")
    print("User created:", user)
    print("Initial balance:", user.wallet.balance if user.wallet else None)  # ожидаем 0

    # 2) Создаём модель и сервисы
    model = MLModel(
        id=1,
        name="BioAge v1",
        feature_names=["age", "bmi", "glucose"],
        price_per_task=25,
    )
    billing = BillingService(repo)
    task_service = TaskService(repo, model, billing)

    # 3) Попытка запуска без денег (FAILED с 'Недостаточно средств')
    task1 = AssessmentTask(id=101, user_id=user.id, model_id=model.id)
    task1.add_answer("age", 35)
    task1.add_answer("bmi", 23)
    task1.add_answer("glucose", 4.8)

    task1 = task_service.run_task(task1)
    print("\nTask1 status:", task1.status)
    print("Task1 error:", task1.error_message)
    print("Balance after task1:", billing.balance(user.id))
    print("Transactions after task1:", repo.user_transactions(user.id))  # ожидаем пусто

    # 4) Пополняем баланс
    tx_topup = billing.topup(user.id, 50)
    print("\nTopup tx:", tx_topup)
    print("Balance after topup:", billing.balance(user.id))  # ожидаем 50

    # 5) Запуск с невалидными данными (age отсутствует) -> статус останется CREATED, списания нет
    task2 = AssessmentTask(id=102, user_id=user.id, model_id=model.id)
    task2.add_answer("bmi", 23)
    task2.add_answer("glucose", 4.8)

    task2 = task_service.run_task(task2)
    print("\nTask2 status:", task2.status)  # ожидаем CREATED
    print("Task2 validation errors:", [str(e) for e in task2.validation_errors])
    print("Balance after task2:", billing.balance(user.id))  # ожидаем 50
    print("Transactions after task2:", repo.user_transactions(user.id))  # ожидаем только TOPUP

    # 6) Успешный запуск -> DONE + списание 25 + CHARGE транзакция
    task3 = AssessmentTask(id=103, user_id=user.id, model_id=model.id)
    task3.add_answer("age", 40)
    task3.add_answer("bmi", 26)
    task3.add_answer("glucose", 5.1)

    task3 = task_service.run_task(task3)
    print("\nTask3 status:", task3.status)  # ожидаем DONE
    print("Task3 charged_amount:", task3.charged_amount)  # ожидаем 25
    print("Task3 result biological_age:", task3.result.biological_age if task3.result else None)
    print("Task3 factors:", [(f.name, f.group, f.value) for f in (task3.result.factors if task3.result else [])])
    print("Balance after task3:", billing.balance(user.id))  # ожидаем 25

    txs = repo.user_transactions(user.id)
    print("Transactions after task3:")
    for t in txs:
        print(" ", t)

    # 7) История задач пользователя
    tasks = repo.user_tasks(user.id)
    print("\nUser tasks:")
    for t in tasks:
        print(" ", t.id, t.status, "charged:", t.charged_amount, "errors:", len(t.validation_errors))

    # 8) Просмотр истории пользователя
    print("\nHistory:")
    for t in repo.user_tasks(user.id):
        print(t.id, t.status, "answers:", t.answers, "charged:", 
              t.charged_amount, "pred:", t.result.biological_age if t.result else None)

if __name__ == "__main__":
    demo()
