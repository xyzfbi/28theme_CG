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
    """
    Сервис для обработки аудио файлов.

    Отвечает за извлечение аудио из видеопотоков (с использованием FFmpeg),
    смешивание нескольких дорожек и сохранение результата в аудиофайл.
    Обработка выполняется в моно-режиме для упрощения микширования.
    """

    def __init__(self):
        """
        Инициализация AudioProcessor.
        Устанавливает стандартную частоту дискретизации для обработки аудио.
        """
        # Стандартная частота дискретизации для высокого качества
        self.sample_rate = 44100
        # Обработка в моно (один канал)
        self.channels = 1

    def extract_audio(
        self, video_path: str
    ) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """
        Извлекает аудиодорожку из видео файла с помощью FFmpeg.

        Аудио принудительно конвертируется в моно (один канал) и загружается
        в массив NumPy с заданной частотой дискретизации (44100 Гц).

        :param video_path: Путь к исходному видео файлу.
        :return: Кортеж (аудиоданные в np.ndarray, частота дискретизации в int)
                 или (None, None) в случае ошибки.
        """
        try:
            # Создаем временный WAV-файл для извлеченного аудио
            temp_audio = tempfile.mktemp(suffix=".wav")

            # Команда FFmpeg для извлечения аудио:
            # -vn (отключить видео)
            # -acodec pcm_s16le (кодек: PCM 16-bit little-endian)
            # -ar <sample_rate> (установка частоты дискретизации)
            # -ac 1 (принудительно моно)
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
                "1",  # Принудительно моно
                "-threads",
                "0",
                "-y",
                temp_audio,
            ]

            # Запускаем FFmpeg. check=True вызовет исключение при неудаче
            subprocess.run(cmd, check=True, capture_output=True)

            # Загружаем аудио из временного файла. librosa.load по умолчанию mono=True.
            audio, sr = librosa.load(temp_audio, sr=self.sample_rate)

            # Удаляем временный файл
            os.remove(temp_audio)

            return audio, sr

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            # Обработка ошибок, связанных с FFmpeg или отсутствием файла
            print(f"Не удалось извлечь аудио из {video_path}: {e}")
            return None, None

    @staticmethod
    def mix_audio(
            audio1: Optional[np.ndarray],
        audio2: Optional[np.ndarray],
        sr: int,
        max_duration: float,
    ) -> Optional[np.ndarray]:
        """
        Смешивает две моно аудиодорожки, выравнивая их по максимальной длительности.
        Если аудио короче, оно дополняется тишиной (нулями).

        :param audio1: Данные первой аудиодорожки (np.ndarray, 1D), или None.
        :param audio2: Данные второй аудиодорожки (np.ndarray, 1D), или None.
        :param sr: Частота дискретизации (Sample Rate).
        :param max_duration: Максимальная длительность композиции в секундах.
        :return: Смешанный аудиомассив (np.ndarray) или None, если оба входа None.
        """
        if audio1 is None and audio2 is None:
            return None

        # 1. Вычисляем целевую длину в сэмплах
        target_length = int(max_duration * sr)
        # Инициализируем массив для смешанного аудио нужной длины
        mixed_audio = np.zeros(target_length)

        # 2. Обработка первого аудио
        if audio1 is not None:
            # Определяем длину, которую нужно добавить нулями (padding)
            padding_needed = max(0, target_length - len(audio1))

            # Дополняем нулями и обрезаем до target_length (если вдруг длиннее)
            audio1_padded = np.pad(
                audio1, (0, padding_needed), "constant"
            )[:target_length]

            # Смешивание (простое сложение амплитуд)
            mixed_audio += audio1_padded

        # 3. Обработка второго аудио
        if audio2 is not None:
            # Определяем длину, которую нужно добавить нулями (padding)
            padding_needed = max(0, target_length - len(audio2))

            # Дополняем нулями и обрезаем до target_length
            audio2_padded = np.pad(
                audio2, (0, padding_needed), "constant"
            )[:target_length]

            # Смешивание (сложение амплитуд)
            mixed_audio += audio2_padded

        # 4. Нормализация
        # Находим максимальное абсолютное значение для предотвращения клиппинга
        max_amplitude = np.max(np.abs(mixed_audio))
        if max_amplitude > 0:
            # Нормализация с понижением громкости до 80% от максимума (0.8)
            mixed_audio = mixed_audio / max_amplitude * 0.8

        return mixed_audio

    def save_audio(self, audio: np.ndarray, output_path: str) -> bool:
        """
        Сохраняет обработанный моно аудиомассив NumPy в файл WAV.

        :param audio: Аудиоданные в np.ndarray (1D).
        :param output_path: Путь для сохранения аудио файла (рекомендуется .wav).
        :return: True, если сохранение прошло успешно, иначе False.
        """
        try:
            # Используем soundfile.write для сохранения аудио с заданной частотой дискретизации
            sf.write(output_path, audio, self.sample_rate)
            return True
        except Exception as e:
            print(f"Ошибка сохранения аудио: {e}")
            return False
