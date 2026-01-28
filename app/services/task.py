from __future__ import annotations

from sqlmodel import Session

from models.ml_model import MLModel
from models.assessment import AssessmentTask
from ml.runtime_model import RuntimeMLModel

from services.billing import BillingService
import services.crud.task as task_crud
import services.crud.ml_model as ml_model_crud
from models.enum import TaskStatus


class TaskService:
    """
    Главный use-case: validate -> predict -> charge -> history.

    Бизнес-правила:
    1) Проверка баланса ДО запуска
    2) Если невалидно — не предсказываем и не списываем
    3) Списание только после успешного predict()
    4) История: task + transaction сохраняются в БД
    """

    def __init__(self, session: Session, billing: BillingService):
        self.session = session
        self.billing = billing

    def _load_runtime_model(self, model_id: int) -> RuntimeMLModel:
        meta = ml_model_crud.get_model_by_id(model_id, self.session)
        if meta is None:
            raise ValueError("ML модель не найдена")

        if hasattr(meta, "validate_meta"):
            meta.validate_meta()

        return RuntimeMLModel(meta=meta)
    
    def create_draft(self, task: AssessmentTask) -> AssessmentTask:
        '''
        Просто создание задачи (черновик),
        Например, пользователь не до конца заполнил анкету и хочет сохранить драфт.
        '''
        return task_crud.create_task(task, self.session)
    

    def run_task_by_id(self, task_id: int) -> AssessmentTask:
        '''
        Запустить уже существующую задачу по id
        '''
        task = task_crud.get_task_by_id(task_id, self.session)
        if task is None:
            raise ValueError("Задача не найдена")

        
        if task.status in {TaskStatus.DONE, TaskStatus.FAILED}:
            raise ValueError(f"Нельзя запускать задачу в статусе {task.status.value}")
        
        return self._process(task)
        

    def _process(self, task: AssessmentTask) -> AssessmentTask:
        '''
        Общая логика обработки (раньше это было в run_task)
        '''
        model = self._load_runtime_model(task.model_id)

        # 2) проверка баланса ДО запуска
        if not self.billing.can_pay(task.user_id, model.price_per_task):
            task.set_error("Недостаточно средств")
            return task_crud.update_task(task, self.session)

        # 3) валидация
        # ! Примечание: Далее, возможно, будет смысл выделить отдельно валидация, при выполнении следующего ДЗ
        ok, errors = model.validate(task.answers)
        task.set_validation_result(ok, errors)
        task = task_crud.update_task(task, self.session)

        if not ok:
            return task

        # 4) предсказание
        try:
            task.start_processing()
            task = task_crud.update_task(task, self.session)
            result = model.predict(task.answers)
        except Exception as ex:
            task.set_error(f"Ошибка предсказания: {ex}")
            return task_crud.update_task(task, self.session)

        # 5) успех -> списание + транзакция + фиксация charged_amount
        try:
            self.billing.charge_after_success(task.user_id, model.price_per_task, task.id)
        except Exception as ex:
            task.set_error(f"Не удалось списать кредиты: {ex}")
            return task_crud.update_task(task, self.session)

        task.set_result(result, charged_amount=model.price_per_task)
        return task_crud.update_task(task, self.session)


    def run_task(self, task: AssessmentTask) -> AssessmentTask:
        '''
        Run task оставили как shortcut (create + run)
        '''
        task = task_crud.create_task(task, self.session)
        return self._process(task)



'''
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
'''