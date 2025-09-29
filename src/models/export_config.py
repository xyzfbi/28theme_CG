"""
Конфигурация экспорта видео
"""

from typing import Optional, Literal
from pydantic import Field
from .base import BaseConfig


class VideoCodecConfig(BaseConfig):
    """Конфигурация видео кодека"""

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
        """Валидация конфигурации кодека"""
        return 0 <= self.crf <= 51


class AudioCodecConfig(BaseConfig):
    """Конфигурация аудио кодека"""

    codec: Literal["aac", "mp3", "ac3"] = Field(default="aac")
    bitrate: str = Field(default="128k")
    sample_rate: int = Field(default=44100)
    channels: int = Field(default=2, ge=1, le=8)

    def validate_config(self) -> bool:
        """Валидация конфигурации аудио"""
        return self.sample_rate > 0 and 1 <= self.channels <= 8


class GPUConfig(BaseConfig):
    """Конфигурация GPU ускорения"""

    use_gpu: bool = Field(default=True)
    gpu_codec: Optional[Literal["h264_nvenc", "h264_qsv", "h264_vaapi"]] = Field(
        default=None
    )

    def validate_config(self) -> bool:
        """Валидация конфигурации GPU"""
        return True


class ExportConfig(BaseConfig):
    """Главная конфигурация экспорта"""

    width: int = Field(default=1920, gt=0, le=8192)
    height: int = Field(default=1080, gt=0, le=8192)
    fps: int = Field(default=30, gt=0, le=120)
    video_codec: VideoCodecConfig = Field(default_factory=VideoCodecConfig)
    audio_codec: AudioCodecConfig = Field(default_factory=AudioCodecConfig)
    gpu_config: GPUConfig = Field(default_factory=GPUConfig)
    threads: int = Field(default=0, ge=0, le=64)

    def validate_config(self) -> bool:
        """Валидация конфигурации экспорта"""
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

    # Обратная совместимость
    @property
    def bitrate(self) -> str:
        return self.video_codec.bitrate

    @property
    def codec(self) -> str:
        return self.video_codec.codec

    @property
    def preset(self) -> str:
        return self.video_codec.preset

    @property
    def crf(self) -> int:
        return self.video_codec.crf

    @property
    def use_gpu(self) -> bool:
        return self.gpu_config.use_gpu

    @property
    def gpu_codec(self) -> Optional[str]:
        return self.gpu_config.gpu_codec
