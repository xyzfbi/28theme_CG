"""Сервисы для Video Meeting Composer"""

# ВАЖНО: Порядок импортов критичен!

# Шаг 1: Импортируем модели из models (они не зависят от сервисов)
from ..models import (
    ExportConfig,
    SpeakerConfig,
    MeetingConfig,
)

# Шаг 2: Импортируем базовые сервисы (без зависимостей от других сервисов)
from .audio_processor import AudioProcessor
from .video_processor import VideoProcessor
from .image_processor import ImageProcessor

# Шаг 3: Импортируем сложные сервисы (зависят от базовых)
from .composition_engine import CompositionEngine
from .export_service import ExportService

__all__ = [
    # Сервисы
    "CompositionEngine",
    "ExportService",
    "VideoProcessor",
    "AudioProcessor",
    "ImageProcessor",
    # Модели (реэкспорт для удобства)
    "ExportConfig",
    "SpeakerConfig",
    "MeetingConfig",
]
