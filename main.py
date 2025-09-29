#!/usr/bin/env python3
"""
Главное приложение Video Meeting Composer
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config.config_manager import ConfigManager
from src.models.meeting_config import MeetingConfig
from src.models.speaker_config import SpeakerConfig
from src.models.export_config import ExportConfig
from src.services.composition_engine import CompositionEngine
from src.services.export_service import ExportService
from src.utils.logger import setup_logger


class VideoMeetingComposerApp:
    """Главное приложение для создания видеовстреч"""

    def __init__(self):
        """Инициализация приложения"""
        self.logger = setup_logger()
        self.meeting_config: MeetingConfig = None
        self.speaker_config: SpeakerConfig = None
        self.export_config: ExportConfig = None
        self.composition_engine: CompositionEngine = None
        self.export_service: ExportService = None

    def initialize(
        self,
        meeting_config: MeetingConfig,
        speaker_config: SpeakerConfig,
        export_config: ExportConfig,
    ) -> bool:
        """Инициализация приложения с конфигурациями"""
        try:
            self.logger.info("Инициализация приложения...")

            # Сохраняем конфигурации
            self.meeting_config = meeting_config
            self.speaker_config = speaker_config
            self.export_config = export_config

            # Валидация конфигураций
            if not ConfigManager.validate_configs(
                meeting_config, speaker_config, export_config
            ):
                self.logger.error("Ошибка валидации конфигураций")
                return False

            # Инициализация сервисов
            self.composition_engine = CompositionEngine(speaker_config, export_config)
            self.export_service = ExportService(export_config)

            self.logger.info("Приложение успешно инициализировано")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка инициализации: {e}")
            return False

    def create_preview(self) -> bool:
        """Создание предпросмотра"""
        try:
            self.logger.info("Создание предпросмотра...")

            success = self.composition_engine.create_preview(
                self.meeting_config.background_path,
                self.meeting_config.speaker1_path,
                self.meeting_config.speaker2_path,
                self.meeting_config.speaker1_name,
                self.meeting_config.speaker2_name,
                "preview.jpg",
            )

            if success:
                self.logger.info("Предпросмотр создан: preview.jpg")
            else:
                self.logger.error("Ошибка создания предпросмотра")

            return success

        except Exception as e:
            self.logger.error(f"Ошибка создания предпросмотра: {e}")
            return False

    def create_video(self) -> bool:
        """Создание итогового видео"""
        try:
            self.logger.info("Создание видео...")

            success = self.export_service.export_video(
                self.meeting_config, self.composition_engine
            )

            if success:
                self.logger.info(f"Видео создано: {self.meeting_config.output_path}")
            else:
                self.logger.error("Ошибка создания видео")

            return success

        except Exception as e:
            self.logger.error(f"Ошибка создания видео: {e}")
            return False

    def run(self, create_preview_only: bool = False) -> bool:
        """Запуск приложения"""
        try:
            if create_preview_only:
                return self.create_preview()
            else:
                return self.create_video()

        except Exception as e:
            self.logger.error(f"Критическая ошибка: {e}")
            return False


def main():
    """Главная функция приложения"""
    try:
        # Создание парсера аргументов
        parser = ConfigManager.create_argument_parser()
        args = parser.parse_args()

        # Создание конфигураций
        meeting_config, speaker_config, export_config = (
            ConfigManager.create_configs_from_args(args)
        )

        # Создание и инициализация приложения
        app = VideoMeetingComposerApp()

        if not app.initialize(meeting_config, speaker_config, export_config):
            print("Ошибка инициализации приложения")
            sys.exit(1)

        # Запуск приложения
        success = app.run(create_preview_only=args.preview)

        if success:
            print("Операция завершена успешно")
            sys.exit(0)
        else:
            print("Ошибка выполнения операции")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nОперация прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
