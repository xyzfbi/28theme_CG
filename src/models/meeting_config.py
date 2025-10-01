"""
Модель конфигурации видеовстречи.

Определяет пути ко всем исходным и выходным файлам,
а также имена спикеров.
"""

from pathlib import Path
from pydantic import Field
from .base import BaseConfig


class MeetingConfig(BaseConfig):
    """
    Конфигурация видеовстречи с путями к файлам и именами спикеров.

    Inherits:
        BaseConfig: Базовый класс для конфигураций Pydantic.

    Attributes:
        background_path (str): Абсолютный или относительный путь к фоновому изображению (JPEG, PNG).
        speaker1_path (str): Путь к видеофайлу первого спикера.
        speaker2_path (str): Путь к видеофайлу второго спикера.
        speaker1_name (str): Имя первого спикера (используется для плашки).
        speaker2_name (str): Имя второго спикера (используется для плашки).
        output_path (str): Путь для сохранения итогового видеофайла (MP4).
    """

    background_path: str = Field(..., description="Путь к фоновому изображению")
    speaker1_path: str = Field(..., description="Путь к видео первого спикера")
    speaker2_path: str = Field(..., description="Путь к видео второго спикера")

    # Имена спикеров с ограничениями по длине (min=1, max=100)
    speaker1_name: str = Field(
        ..., min_length=1, max_length=100, description="Имя первого спикера"
    )
    speaker2_name: str = Field(
        ..., min_length=1, max_length=100, description="Имя второго спикера"
    )

    # Путь для выходного файла с дефолтным значением
    output_path: str = Field(
        default="meeting_output.mp4", description="Путь для сохранения результата"
    )

    def validate_config(self) -> bool:
        """
        Проверка существования файлов, указанных в конфигурации.

        Выполняет проверку наличия фонового изображения и видеофайлов спикеров,
        используя модуль `pathlib.Path`.
        :return: True, если все необходимые файлы найдены, иначе False (с выводом ошибки в консоль).
        """
        try:
            # 1. Проверяем существование фонового изображения
            if not Path(self.background_path).exists():
                raise FileNotFoundError(
                    f"Фоновое изображение не найдено: {self.background_path}"
                )

            # 2. Проверяем существование видео первого спикера
            if not Path(self.speaker1_path).exists():
                raise FileNotFoundError(
                    f"Видео первого спикера не найдено: {self.speaker1_path}"
                )

            # 3. Проверяем существование видео второго спикера
            if not Path(self.speaker2_path).exists():
                raise FileNotFoundError(
                    f"Видео второго спикера не найдено: {self.speaker2_path}"
                )

            return True

        except Exception as e:
            # Логирование ошибки и возврат False при любой проблеме с файлами
            print(f"Ошибка валидации конфигурации встречи: {e}")
            return False
