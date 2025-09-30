"""Базовые модели для конфигураций."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict


class BaseConfig(BaseModel, ABC):
    """
    Базовая модель конфигурации с общей функциональностью.

    Все конфигурационные модели наследуются от этого класса
    для обеспечения единообразия валидации и сериализации.
    """

    model_config = ConfigDict(
        extra="forbid",  # Запрет дополнительных полей
        validate_assignment=True,  # Валидация при присваивании
        strict=True,  # Строгие типы
    )

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Валидация конфигурации.

        Returns:
            True если конфигурация валидна, False иначе
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование конфигурации в словарь.

        Returns:
            Словарь с данными конфигурации
        """
        return self.model_dump()
