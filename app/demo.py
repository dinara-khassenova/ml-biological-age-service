from models.ml_model import MLModel
from models.assessment import AssessmentTask
from repository import Repository

from services.billing import BillingService
from services.task import TaskService
from services.auth import RegAuthService

# ====== DEMO / quick check ======

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
