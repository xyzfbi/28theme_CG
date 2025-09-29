"""
Конфигурация спикеров
"""

from typing import Optional, Tuple

from pydantic import Field

from .base import BaseConfig


class PositionConfig(BaseConfig):
    """Позиция спикера"""

    x: int = Field(..., ge=0, description="X координата")
    y: int = Field(..., ge=0, description="Y координата")

    def validate_config(self) -> bool:
        """Валидация позиции"""
        return self.x >= 0 and self.y >= 0

    def to_tuple(self) -> Tuple[int, int]:
        """Преобразование в кортеж"""
        return self.x, self.y

    @classmethod
    def from_tuple(cls, pos: Tuple[int, int]) -> "PositionConfig":
        """Создание из кортежа"""
        return cls(x=pos[0], y=pos[1])


class SpeakerConfig(BaseConfig):
    """Конфигурация спикеров с настройками плашек"""

    width: int = Field(default=400, gt=0, le=4096)
    height: int = Field(default=300, gt=0, le=4096)
    position: Optional[PositionConfig] = Field(default=None)
    font_size: int = Field(default=24, gt=0, le=200)
    font_color: Tuple[int, ...] = Field(default=(255, 255, 255))
    plate_bg_color: Tuple[int, int, int, int] = Field(default=(0, 0, 0, 180))
    plate_border_color: Tuple[int, ...] = Field(default=(255, 255, 255))
    plate_border_width: int = Field(default=2, ge=0, le=20)
    plate_padding: int = Field(default=10, ge=0, le=50)

    @classmethod
    def validate_position(cls, v) -> Optional[PositionConfig]:
        """Валидация позиции спикера"""
        if v is None:
            return None

        if isinstance(v, tuple) and len(v) == 2:
            return PositionConfig(x=v[0], y=v[1])

        if isinstance(v, dict):
            return PositionConfig(**v)

        if isinstance(v, PositionConfig):
            return v

        raise ValueError(
            "Позиция должна быть кортежем (x, y), словарем или PositionConfig"
        )

    def validate_config(self) -> bool:
        """Валидация конфигурации спикеров"""
        try:
            if self.width <= 0 or self.height <= 0:
                return False

            if self.position is not None and not self.position.validate_config():
                return False

            if self.font_size <= 0 or self.plate_padding < 0:
                return False

            return True

        except Exception:
            return False

    def get_position_tuple(self) -> Optional[Tuple[int, int]]:
        """Получение позиции в виде кортежа"""
        return self.position.to_tuple() if self.position else None
