"""
Модели данных для Video Meeting Composer
"""

from .base import BaseConfig
from .meeting_config import MeetingConfig
from .speaker_config import SpeakerConfig, PositionConfig
from .export_config import ExportConfig, VideoCodecConfig, AudioCodecConfig, GPUConfig

__all__ = [
    "BaseConfig",
    "MeetingConfig",
    "SpeakerConfig",
    "PositionConfig",
    "ExportConfig",
    "VideoCodecConfig",
    "AudioCodecConfig",
    "GPUConfig",
]
