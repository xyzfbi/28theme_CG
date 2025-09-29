"""
Сервис обработки аудио
"""

import os
import tempfile
import subprocess
import numpy as np
import librosa
import soundfile as sf
from typing import Optional, Tuple


class AudioProcessor:
    """Сервис для обработки аудио файлов"""

    def __init__(self):
        self.sample_rate = 44100
        self.channels = 2

    def extract_audio(
        self, video_path: str
    ) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """Извлечение аудио из видео файла"""
        try:
            temp_audio = tempfile.mktemp(suffix=".wav")

            cmd = [
                "ffmpeg",
                "-i",
                video_path,
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(self.sample_rate),
                "-ac",
                str(self.channels),
                "-threads",
                "0",
                "-y",
                temp_audio,
            ]

            subprocess.run(cmd, check=True, capture_output=True)

            audio, sr = librosa.load(temp_audio, sr=self.sample_rate)
            os.remove(temp_audio)

            return audio, sr

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Не удалось извлечь аудио из {video_path}: {e}")
            return None, None

    def mix_audio(
        self,
        audio1: Optional[np.ndarray],
        audio2: Optional[np.ndarray],
        sr: int,
        max_duration: float,
    ) -> Optional[np.ndarray]:
        """Смешивание двух аудиодорожек"""
        if audio1 is None and audio2 is None:
            return None

        target_length = int(max_duration * sr)
        mixed_audio = np.zeros(target_length)

        if audio1 is not None:
            audio1_padded = np.pad(
                audio1, (0, max(0, target_length - len(audio1))), "constant"
            )
            mixed_audio += audio1_padded[:target_length]

        if audio2 is not None:
            audio2_padded = np.pad(
                audio2, (0, max(0, target_length - len(audio2))), "constant"
            )
            mixed_audio += audio2_padded[:target_length]

        # Нормализация
        if np.max(np.abs(mixed_audio)) > 0:
            mixed_audio = mixed_audio / np.max(np.abs(mixed_audio)) * 0.8

        return mixed_audio

    def save_audio(self, audio: np.ndarray, output_path: str) -> bool:
        """Сохранение аудио в файл"""
        try:
            sf.write(output_path, audio, self.sample_rate)
            return True
        except Exception as e:
            print(f"Ошибка сохранения аудио: {e}")
            return False
