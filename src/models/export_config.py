"""Конфигурация экспорта видео."""

from typing import Optional, Literal
from pydantic import Field
from .base import BaseConfig


class VideoCodecConfig(BaseConfig):
    """
    Конфигурация видео кодека.

    Attributes:
        codec: Название кодека
        preset: Пресет скорости кодирования
        crf: Constant Rate Factor (качество, 0-51)
        bitrate: Целевой битрейт
    """

    codec: Literal["libx264", "libx265", "h264_nvenc", "h264_qsv", "h264_vaapi"] = (
        Field(default="libx264")
    )
    preset: Literal[
        "ultrafast",
        "superfast",
        "veryfast",
        "faster",
        "fast",
        "medium",
        "slow",
        "slower",
        "veryslow",
    ] = Field(default="fast")
    crf: int = Field(default=23, ge=0, le=51)
    bitrate: str = Field(default="5000k")

    def validate_config(self) -> bool:
        """Проверка корректности параметров кодека."""
        return 0 <= self.crf <= 51


class AudioCodecConfig(BaseConfig):
    """
    Конфигурация аудио кодека.

    Attributes:
        codec: Название кодека
        bitrate: Битрейт аудио
        sample_rate: Частота дискретизации (Гц)
        channels: Количество каналов (1-8)
    """

    codec: Literal["aac", "mp3", "ac3"] = Field(default="aac")
    bitrate: str = Field(default="128k")
    sample_rate: int = Field(default=44100)
    channels: int = Field(default=2, ge=1, le=8)

    def validate_config(self) -> bool:
        """Проверка корректности параметров аудио."""
        return self.sample_rate > 0 and 1 <= self.channels <= 8


class GPUConfig(BaseConfig):
    """
    Конфигурация GPU ускорения.

    Attributes:
        use_gpu: Использовать ли GPU для кодирования
        gpu_codec: Конкретный GPU кодек (определяется автоматически)
    """

    use_gpu: bool = Field(default=True)
    gpu_codec: Optional[Literal["h264_nvenc", "h264_qsv", "h264_vaapi"]] = Field(
        default=None
    )

    def validate_config(self) -> bool:
        """GPU конфигурация всегда валидна."""
        return True


class ExportConfig(BaseConfig):
    """
    Главная конфигурация экспорта видео.

    Содержит все параметры для финального рендеринга видео,
    включая разрешение, частоту кадров и настройки кодеков.

    Attributes:
        width: Ширина выходного видео (пиксели)
        height: Высота выходного видео (пиксели)
        fps: Частота кадров (FPS)
        video_codec: Конфигурация видео кодека
        audio_codec: Конфигурация аудио кодека
        gpu_config: Конфигурация GPU ускорения
        threads: Количество потоков для обработки (0 = все доступные)
    """

    width: int = Field(default=1920, gt=0, le=8192)
    height: int = Field(default=1080, gt=0, le=8192)
    fps: int = Field(default=30, gt=0, le=120)
    video_codec: VideoCodecConfig = Field(default_factory=VideoCodecConfig)
    audio_codec: AudioCodecConfig = Field(default_factory=AudioCodecConfig)
    gpu_config: GPUConfig = Field(default_factory=GPUConfig)
    threads: int = Field(default=0, ge=0, le=64)

    def validate_config(self) -> bool:
        """Проверка корректности всех параметров экспорта."""
        try:
            if self.width <= 0 or self.height <= 0 or self.fps <= 0:
                return False

            return (
                self.video_codec.validate_config()
                and self.audio_codec.validate_config()
                and self.gpu_config.validate_config()
            )

        except Exception:
            return False

    # Свойства для обратной совместимости с прямым доступом
    @property
    def bitrate(self) -> str:
        """Битрейт видео."""
        return self.video_codec.bitrate

    @property
    def codec(self) -> str:
        """Видео кодек."""
        return self.video_codec.codec

    @property
    def preset(self) -> str:
        """Пресет кодека."""
        return self.video_codec.preset

    @property
    def crf(self) -> int:
        """CRF значение."""
        return self.video_codec.crf

    @property
    def use_gpu(self) -> bool:
        """Использование GPU."""
        return self.gpu_config.use_gpu

    @property
    def gpu_codec(self) -> Optional[str]:
        """GPU кодек."""
        return self.gpu_config.gpu_codec
