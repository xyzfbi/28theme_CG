"""
Базовые модели для конфигураций
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict


class BaseConfig(BaseModel, ABC):
    """Базовая модель конфигурации с общей функциональностью"""

    model_config = ConfigDict(
        extra="forbid",  # Запрет дополнительных полей
        validate_assignment=True,  # Валидация при присваивании
        strict=True,  # Строгие типы
    )

    @abstractmethod
    def validate_config(self) -> bool:
        """Валидация конфигурации"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseConfig":
        """Создание из словаря"""
        return cls(**data)
