"""
Менеджер конфигурации
"""

import argparse
import os
from typing import Tuple
from ..models.meeting_config import MeetingConfig
from ..models.speaker_config import SpeakerConfig
from ..models.export_config import (
    ExportConfig,
    VideoCodecConfig,
    AudioCodecConfig,
    GPUConfig,
)


class ConfigManager:
    """Менеджер конфигурации приложения"""

    @staticmethod
    def create_argument_parser() -> argparse.ArgumentParser:
        """Создание парсера аргументов командной строки"""
        parser = argparse.ArgumentParser(description="Создание экрана видеовстречи")

        # Обязательные параметры
        parser.add_argument(
            "--background", required=True, help="Путь к фоновому изображению"
        )
        parser.add_argument(
            "--speaker1", required=True, help="Путь к видео первого спикера"
        )
        parser.add_argument(
            "--speaker2", required=True, help="Путь к видео второго спикера"
        )
        parser.add_argument("--name1", required=True, help="Имя первого спикера")
        parser.add_argument("--name2", required=True, help="Имя второго спикера")

        # Опциональные параметры
        parser.add_argument(
            "--output", default="meeting_output.mp4", help="Путь к выходному файлу"
        )
        parser.add_argument(
            "--preview", action="store_true", help="Создать только предпросмотр"
        )

        # Настройки размеров спикеров
        parser.add_argument(
            "--speaker-width", type=int, default=400, help="Ширина окна спикера"
        )
        parser.add_argument(
            "--speaker-height", type=int, default=300, help="Высота окна спикера"
        )

        # Настройки плашек
        parser.add_argument("--font-size", type=int, default=24, help="Размер шрифта")

        # Настройки экспорта
        parser.add_argument(
            "--output-width", type=int, default=1920, help="Ширина выходного видео"
        )
        parser.add_argument(
            "--output-height", type=int, default=1080, help="Высота выходного видео"
        )
        parser.add_argument("--fps", type=int, default=30, help="FPS выходного видео")

        # Настройки оптимизации ffmpeg
        parser.add_argument(
            "--ffmpeg-preset",
            default="fast",
            choices=[
                "ultrafast",
                "superfast",
                "veryfast",
                "faster",
                "fast",
                "medium",
                "slow",
                "slower",
                "veryslow",
            ],
            help="Пресет ffmpeg для скорости кодирования",
        )
        parser.add_argument(
            "--ffmpeg-crf", type=int, default=23, help="CRF для ffmpeg (0-51)"
        )
        parser.add_argument(
            "--ffmpeg-threads",
            type=int,
            default=0,
            help="Количество потоков ffmpeg (0=все ядра)",
        )
        parser.add_argument(
            "--no-gpu", action="store_true", help="Отключить GPU ускорение"
        )

        return parser

    @staticmethod
    def create_configs_from_args(
        args: argparse.Namespace,
    ) -> Tuple[MeetingConfig, SpeakerConfig, ExportConfig]:
        """Создание конфигурационных объектов из аргументов"""
        # Конфигурация встречи
        meeting_config = MeetingConfig(
            background_path=args.background,
            speaker1_path=args.speaker1,
            speaker2_path=args.speaker2,
            speaker1_name=args.name1,
            speaker2_name=args.name2,
            output_path=args.output,
        )

        # Конфигурация спикеров
        speaker_config = SpeakerConfig(
            width=args.speaker_width,
            height=args.speaker_height,
            font_size=args.font_size,
        )

        # Конфигурация экспорта
        export_config = ExportConfig(
            width=args.output_width,
            height=args.output_height,
            fps=args.fps,
            threads=args.ffmpeg_threads,
            video_codec=VideoCodecConfig(
                preset=args.ffmpeg_preset, crf=args.ffmpeg_crf
            ),
            audio_codec=AudioCodecConfig(),
            gpu_config=GPUConfig(use_gpu=not args.no_gpu),
        )

        return meeting_config, speaker_config, export_config

    @staticmethod
    def validate_configs(
        meeting_config: MeetingConfig,
        speaker_config: SpeakerConfig,
        export_config: ExportConfig,
    ) -> bool:
        """Валидация конфигураций"""
        try:
            # Валидация файлов
            if not os.path.exists(meeting_config.background_path):
                print(f"Файл не найден: {meeting_config.background_path}")
                return False
            if not os.path.exists(meeting_config.speaker1_path):
                print(f"Файл не найден: {meeting_config.speaker1_path}")
                return False
            if not os.path.exists(meeting_config.speaker2_path):
                print(f"Файл не найден: {meeting_config.speaker2_path}")
                return False

            # Валидация размеров
            if speaker_config.width > export_config.width:
                print("Ширина спикера не может быть больше ширины выходного видео")
                return False
            if speaker_config.height > export_config.height:
                print("Высота спикера не может быть больше высоты выходного видео")
                return False

            return True

        except Exception as e:
            print(f"Ошибка валидации: {e}")
            return False
