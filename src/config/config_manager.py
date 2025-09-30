"""
Менеджер конфигурации для консольного запуска.

Отвечает за парсинг аргументов командной строки (CLI),
преобразование их в строго типизированные конфигурационные объекты (Pydantic models)
и базовую валидацию входных данных.
"""

import argparse
import os
from typing import Tuple

# Обратите внимание: импорты моделей должны быть относительными
from ..models.meeting_config import MeetingConfig
from ..models.speaker_config import SpeakerConfig
from ..models.export_config import (
    ExportConfig,
    VideoCodecConfig,
    AudioCodecConfig,
    GPUConfig,
)


class ConfigManager:
    """
    Управляет созданием, парсингом и валидацией конфигурационных объектов
    для запуска процесса композиции видео из командной строки.
    """

    @staticmethod
    def create_argument_parser() -> argparse.ArgumentParser:
        """
        Создает и конфигурирует парсер аргументов командной строки (argparse).

        Это центральная точка определения всех параметров, доступных пользователю
        при запуске скрипта через CLI.

        :return: Настроенный экземпляр argparse.ArgumentParser.
        """
        parser = argparse.ArgumentParser(
            description="Утилита для создания экрана видеовстречи из CLI."
        )

        # --- Обязательные параметры (INPUTS) ---
        input_group = parser.add_argument_group("Входные и обязательные параметры")
        input_group.add_argument(
            "--background",
            required=True,
            help="[REQUIRED] Полный путь к фоновому изображению (JPG/PNG).",
        )
        input_group.add_argument(
            "--speaker1",
            required=True,
            help="[REQUIRED] Полный путь к видеофайлу первого спикера.",
        )
        input_group.add_argument(
            "--speaker2",
            required=True,
            help="[REQUIRED] Полный путь к видеофайлу второго спикера.",
        )
        input_group.add_argument(
            "--name1",
            required=True,
            help="[REQUIRED] Имя или заголовок для плашки первого спикера.",
        )
        input_group.add_argument(
            "--name2",
            required=True,
            help="[REQUIRED] Имя или заголовок для плашки второго спикера.",
        )

        # --- Общие опции ---
        general_group = parser.add_argument_group("Общие опции и режимы работы")
        general_group.add_argument(
            "--output",
            default="meeting_output.mp4",
            help="Путь для сохранения итогового видеофайла (по умолчанию: meeting_output.mp4).",
        )
        general_group.add_argument(
            "--preview",
            action="store_true",
            help="Если указан, будет сгенерирован только JPEG-предпросмотр первого кадра, без кодирования всего видео.",
        )

        # --- Настройки композиции (SpeakerConfig) ---
        speaker_group = parser.add_argument_group(
            "Настройки композиции и размеров окон"
        )
        speaker_group.add_argument(
            "--speaker-width",
            type=int,
            default=400,
            help="Ширина окна (вида) спикера в пикселях.",
        )
        speaker_group.add_argument(
            "--speaker-height",
            type=int,
            default=300,
            help="Высота окна (вида) спикера в пикселях.",
        )
        # Параметры плашек (Plates)
        speaker_group.add_argument(
            "--font-size",
            type=int,
            default=24,
            help="Размер шрифта для имени спикера на плашке.",
        )
        # Примечание: остальные параметры SpeakerConfig (цвета, отступы) будут взяты из значений по умолчанию в модели SpeakerConfig.

        # --- Настройки экспорта (ExportConfig) ---
        export_group = parser.add_argument_group("Настройки экспорта видео (FFmpeg)")
        export_group.add_argument(
            "--output-width",
            type=int,
            default=1920,
            help="Ширина итогового видео (например, 1920 для FullHD).",
        )
        export_group.add_argument(
            "--output-height",
            type=int,
            default=1080,
            help="Высота итогового видео (например, 1080 для FullHD).",
        )
        export_group.add_argument(
            "--fps",
            type=int,
            default=30,
            help="Частота кадров (Frames Per Second) выходного видео.",
        )

        # --- Параметры кодирования ---
        codec_group = parser.add_argument_group("Параметры кодирования FFmpeg")
        codec_group.add_argument(
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
            help="Пресет кодирования (скорость/качество). 'fast' - хороший баланс.",
        )
        codec_group.add_argument(
            "--ffmpeg-crf",
            type=int,
            default=23,
            help="Constant Rate Factor (CRF) для кодирования H.264 (18-28 - стандартный диапазон качества).",
        )
        codec_group.add_argument(
            "--ffmpeg-threads",
            type=int,
            default=0,
            help="Количество потоков для кодирования (0 означает использование всех доступных ядер).",
        )
        codec_group.add_argument(
            "--no-gpu",
            action="store_true",
            help="Отключить автоматическое определение и использование GPU ускорения (например, NVENC или QSV).",
        )

        return parser

    @staticmethod
    def create_configs_from_args(
        args: argparse.Namespace,
    ) -> Tuple[MeetingConfig, SpeakerConfig, ExportConfig]:
        """
        Преобразует спарсенные аргументы командной строки (argparse.Namespace)
        в строго типизированные конфигурационные объекты.

        Это обеспечивает валидацию данных на основе моделей Pydantic перед запуском
        основного процесса композиции.

        :param args: Объект, содержащий аргументы, спарсенные с помощью argparse.
        :return: Кортеж из трех настроенных конфигурационных объектов.
        """
        # 1. Конфигурация встречи (MeetingConfig) - описывает входные/выходные пути и имена
        meeting_config = MeetingConfig(
            background_path=args.background,
            speaker1_path=args.speaker1,
            speaker2_path=args.speaker2,
            speaker1_name=args.name1,
            speaker2_name=args.name2,
            output_path=args.output,
        )

        # 2. Конфигурация спикеров (SpeakerConfig) - описывает размеры и внешний вид
        speaker_config = SpeakerConfig(
            width=args.speaker_width,
            height=args.speaker_height,
            font_size=args.font_size,
        )

        # 3. Конфигурация экспорта (ExportConfig) - описывает параметры FFmpeg
        export_config = ExportConfig(
            width=args.output_width,
            height=args.output_height,
            fps=args.fps,
            threads=args.ffmpeg_threads,  # Количество потоков для FFmpeg
            video_codec=VideoCodecConfig(
                preset=args.ffmpeg_preset, crf=args.ffmpeg_crf
            ),
            audio_codec=AudioCodecConfig(),
            # use_gpu: True, если флаг --no-gpu НЕ указан (т.е., not args.no_gpu)
            gpu_config=GPUConfig(use_gpu=not args.no_gpu),
        )

        return meeting_config, speaker_config, export_config

    @staticmethod
    def validate_configs(
        meeting_config: MeetingConfig,
        speaker_config: SpeakerConfig,
        export_config: ExportConfig,
    ) -> bool:
        """
        Выполняет базовую валидацию конфигурационных объектов перед запуском композиции.

        Проверяет существование входных файлов и логическую корректность размеров
        (размеры окон спикеров не должны превышать размер выходного кадра).

        :param meeting_config: Настройки входных/выходных файлов.
        :param speaker_config: Настройки размеров окон спикеров.
        :param export_config: Настройки выходного кадра.
        :return: True, если валидация прошла успешно, иначе False.
        """
        try:
            # --- Валидация существования файлов ---
            if not os.path.exists(meeting_config.background_path):
                print(
                    f"Ошибка валидации: Файл фона не найден по пути: {meeting_config.background_path}"
                )
                return False
            if not os.path.exists(meeting_config.speaker1_path):
                print(
                    f"Ошибка валидации: Видео первого спикера не найдено по пути: {meeting_config.speaker1_path}"
                )
                return False
            if not os.path.exists(meeting_config.speaker2_path):
                print(
                    f"Ошибка валидации: Видео второго спикера не найдено по пути: {meeting_config.speaker2_path}"
                )
                return False

            # --- Валидация логики размеров ---
            # Ширина спикера не должна превышать общую ширину кадра
            if speaker_config.width > export_config.width:
                print(
                    f"Ошибка валидации: Ширина спикера ({speaker_config.width}px) "
                    f"не может быть больше ширины выходного видео ({export_config.width}px)."
                )
                return False
            # Высота спикера не должна превышать общую высоту кадра
            if speaker_config.height > export_config.height:
                print(
                    f"Ошибка валидации: Высота спикера ({speaker_config.height}px) "
                    f"не может быть больше высоты выходного видео ({export_config.height}px)."
                )
                return False

            return True

        except Exception as e:
            # Ловим любые неожиданные ошибки при проверке (например, ошибки I/O или проблемы с атрибутами)
            print(f"Критическая ошибка при валидации конфигурации: {e}")
            return False
