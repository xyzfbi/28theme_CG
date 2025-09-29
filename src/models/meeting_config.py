"""
Конфигурация видеовстречи
"""

from pathlib import Path

from pydantic import Field

from .base import BaseConfig


class MeetingConfig(BaseConfig):
    """Конфигурация видеовстречи с валидацией файлов и имен"""

    background_path: str = Field(..., description="Путь к фоновому изображению")
    speaker1_path: str = Field(..., description="Путь к видео первого спикера")
    speaker2_path: str = Field(..., description="Путь к видео второго спикера")
    speaker1_name: str = Field(..., min_length=1, max_length=100)
    speaker2_name: str = Field(..., min_length=1, max_length=100)
    output_path: str = Field(default="meeting_output.mp4")

    @classmethod
    def validate_file_paths(cls, v: str) -> str:
        """Валидация путей к файлам"""
        if not v or not v.strip():
            raise ValueError("Путь к файлу не может быть пустым")

        path = Path(v.strip())

        # Проверяем расширения
        if path.suffix.lower() not in [
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
            ".wmv",
        ]:
            raise ValueError(f"Неподдерживаемый формат файла: {path.suffix}")

        return str(path)

    @classmethod
    def validate_speaker_names(cls, v: str) -> str:
        """Валидация имен спикеров"""
        if not v or not v.strip():
            raise ValueError("Имя спикера не может быть пустым")

        name = v.strip()
        forbidden_chars = ["<", ">", ":", '"', "|", "?", "*"]
        for char in forbidden_chars:
            if char in name:
                raise ValueError(f"Имя спикера не может содержать символ '{char}'")

        return name

    def validate_config(self) -> bool:
        """Валидация конфигурации встречи"""
        try:
            # Проверяем существование файлов
            if not Path(self.background_path).exists():
                raise FileNotFoundError(
                    f"Фоновое изображение не найдено: {self.background_path}"
                )

            if not Path(self.speaker1_path).exists():
                raise FileNotFoundError(
                    f"Видео первого спикера не найдено: {self.speaker1_path}"
                )

            if not Path(self.speaker2_path).exists():
                raise FileNotFoundError(
                    f"Видео второго спикера не найдено: {self.speaker2_path}"
                )

            return True

        except Exception as e:
            print(f"Ошибка валидации конфигурации встречи: {e}")
            return False
