"""
Конфигурация спикеров и их визуального представления.

Этот модуль определяет структуры данных (модели Pydantic) для:
1. Позиции спикера (PositionConfig).
2. Общей конфигурации отображения окна спикера и плашки с именем (SpeakerConfig).
"""

from typing import Optional, Tuple
from pydantic import Field
from .base import BaseConfig


class PositionConfig(BaseConfig):
    """
    Модель для определения позиции (координат) элемента на экране.

    Inherits:
        BaseConfig: Базовый класс для конфигураций Pydantic.

    Attributes:
        x (int): X координата (от левого края), должна быть >= 0.
        y (int): Y координата (от верхнего края), должна быть >= 0.
    """

    # X координата. Используется Field для добавления метаданных (описание, валидация ge=0).
    x: int = Field(..., ge=0, description="X координата (от левого края)")
    # Y координата.
    y: int = Field(..., ge=0, description="Y координата (от верхнего края)")

    def validate_config(self) -> bool:
        """
        Проверка корректности координат.

        Хотя Pydantic выполняет валидацию Field(ge=0) при инициализации,
        этот метод добавляет явную проверку.
        :return: True, если обе координаты >= 0.
        """
        # Проверка, что координаты не отрицательны
        return self.x >= 0 and self.y >= 0

    def to_tuple(self) -> Tuple[int, int]:
        """
        Получение позиции в виде кортежа Python (x, y).

        :return: Кортеж (x, y).
        """
        return self.x, self.y


class SpeakerConfig(BaseConfig):
    """
    Конфигурация отображения спикеров и стилизации их плашек с именами.

    Inherits:
        BaseConfig: Базовый класс для конфигураций Pydantic.

    Attributes:
        width (int): Ширина окна спикера в пикселях.
        height (int): Высота окна спикера в пикселях.
        position (Optional[PositionConfig]): Фиксированная позиция окна.
                                             Если None, используется автоматическое центрирование.
        font_size (int): Размер шрифта на плашке с именем.
        font_color (Tuple[int, ...]): Цвет текста (R, G, B).
        plate_bg_color (Tuple[int, ...]): Цвет фона плашки (R, G, B, A).
        plate_border_color (Tuple[int, ...]): Цвет рамки плашки (R, G, B).
        plate_border_width (int): Толщина рамки плашки в пикселях.
        plate_padding (int): Внутренние отступы плашки вокруг текста.
    """

    # Размеры окна спикера (используется для ресайза видео). Должны быть > 0.
    width: int = Field(
        default=400, gt=0, le=4096, description="Ширина окна спикера (пиксели)"
    )
    height: int = Field(
        default=300, gt=0, le=4096, description="Высота окна спикера (пиксели)"
    )
    # Позиция: Optional, так как может быть автоматической
    position: Optional[PositionConfig] = Field(
        default=None, description="Позиция окна (None = автоматическое центрирование)"
    )

    # Параметры текста и плашки
    font_size: int = Field(
        default=24, gt=0, le=200, description="Размер шрифта на плашке с именем"
    )
    font_color: Tuple[int, ...] = Field(
        default=(255, 255, 255), description="Цвет текста (R, G, B)"
    )

    # Параметры фона плашки (RGBA). 180 - это значение альфа-канала для полупрозрачности.
    plate_bg_color: Tuple[int, ...] = Field(
        default=(0, 0, 0, 180), description="Цвет фона плашки (R, G, B, A)"
    )

    # Параметры рамки
    plate_border_color: Tuple[int, ...] = Field(
        default=(255, 255, 255), description="Цвет рамки плашки (R, G, B)"
    )
    plate_border_width: int = Field(
        default=2, ge=0, le=20, description="Толщина рамки плашки (пиксели)"
    )

    # Отступы
    plate_padding: int = Field(
        default=10, ge=0, le=50, description="Внутренние отступы плашки (пиксели)"
    )

    # Путь к пользовательскому TTF-шрифту для рендера плашек
    font_path: Optional[str] = Field(
        default=None, description="Полный путь к TTF-файлу шрифта для плашек"
    )

    def validate_config(self) -> bool:
        """
        Проверка корректности всех параметров конфигурации спикера.

        Выполняет проверку размеров, позиции и параметров стилизации.
        :return: True, если все параметры корректны, иначе False.
        """
        try:
            # 1. Проверка размеров окна
            if self.width <= 0 or self.height <= 0:
                return False

            # 2. Проверка позиции (если указана)
            if self.position is not None and not self.position.validate_config():
                return False

            # 3. Проверка параметров плашки
            if (
                self.font_size <= 0
                or self.plate_padding < 0
                or self.plate_border_width < 0
            ):
                return False

            return True

        except Exception:
            # Возвращаем False, если Pydantic или другие проверки выбросили исключение
            return False
