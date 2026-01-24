from models.ml_model import MLModel
from models.assessment import AssessmentTask
from repository import Repository

from app.services.billing import BillingService

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
