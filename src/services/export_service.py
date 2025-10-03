"""
Сервис экспорта видео
"""

import os
import tempfile
import subprocess
import cv2
import numpy as np
from typing import Optional, Callable
from ..models.export_config import ExportConfig
from ..models.meeting_config import MeetingConfig
from .composition_engine import CompositionEngine
from .audio_processor import AudioProcessor


class ExportService:
    """Сервис для экспорта готового видео"""

    def __init__(self, export_config: ExportConfig):
        self.export_config = export_config
        self.audio_processor = AudioProcessor()
        self._detect_gpu_codec()

    def _detect_gpu_codec(self):
        """Автоматическое определение доступного GPU кодека"""
        if not self.export_config.gpu_config.use_gpu:
            self.export_config.gpu_config.gpu_codec = "libx264"
            return

        try:
            result = subprocess.run(
                ["ffmpeg", "-encoders"], capture_output=True, text=True
            )
            encoders = result.stdout

            if "h264_nvenc" in encoders:
                print("Обнаружен NVIDIA GPU - используем NVENC")
                self.export_config.gpu_config.gpu_codec = "h264_nvenc"
            elif "h264_qsv" in encoders:
                print("Обнаружен Intel GPU - используем QSV")
                self.export_config.gpu_config.gpu_codec = "h264_qsv"
            elif "h264_vaapi" in encoders:
                print("Обнаружен VAAPI - используем аппаратное ускорение")
                self.export_config.gpu_config.gpu_codec = "h264_vaapi"
            else:
                print("GPU кодеки не найдены - используем CPU")
                self.export_config.gpu_config.gpu_codec = "libx264"
        except Exception as e:
            print("Ошибка определения GPU - используем CPU", e)
            self.export_config.gpu_config.gpu_codec = "libx264"

    def export_video(
        self,
        meeting_config: MeetingConfig,
        composition_engine: CompositionEngine,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> bool:
        """Экспорт готового видео"""
        try:
            if progress_cb:
                progress_cb(2.0)
            # Загружаем фон
            background = composition_engine.image_processor.load_image(
                meeting_config.background_path
            )
            if background is None:
                return False

            # Загружаем видео спикеров
            cap1 = composition_engine.video_processor.load_video(
                meeting_config.speaker1_path
            )
            cap2 = composition_engine.video_processor.load_video(
                meeting_config.speaker2_path
            )

            # Получаем информацию о видео
            info1 = composition_engine.video_processor.get_video_info(cap1)
            info2 = composition_engine.video_processor.get_video_info(cap2)

            # Вычисляем параметры
            output_fps = composition_engine.video_processor.calculate_output_fps(
                info1["fps"], info2["fps"]
            )
            max_frames = composition_engine.video_processor.calculate_max_frames(
                info1["frame_count"], info2["frame_count"]
            )
            max_duration = max_frames / output_fps

            print(
                f"Создание видео: {max_frames} кадров, {output_fps} FPS, {max_duration:.2f} сек"
            )

            # Извлекаем аудио
            print("Извлечение аудио...")
            audio1, _ = self.audio_processor.extract_audio(meeting_config.speaker1_path)
            audio2, _ = self.audio_processor.extract_audio(meeting_config.speaker2_path)
            if progress_cb:
                progress_cb(10.0)

            # Смешиваем аудио
            mixed_audio = None
            if audio1 is not None or audio2 is not None:
                print("Смешивание аудио...")
                mixed_audio = self.audio_processor.mix_audio(
                    audio1, audio2, 44100, max_duration
                )

            # Создаем временное видео
            temp_video = tempfile.mktemp(suffix=".mp4")
            success = self._create_video_frames(
                composition_engine,
                background,
                cap1,
                cap2,
                max_frames,
                output_fps,
                temp_video,
                meeting_config,
                progress_cb,
            )

            if not success:
                return False

            # Объединяем видео и аудио
            print("Объединение видео и аудио...")
            if progress_cb:
                progress_cb(92.0)
            success = self._combine_video_audio(
                temp_video, mixed_audio, meeting_config.output_path
            )

            # Освобождаем ресурсы
            cap1.release()
            cap2.release()

            # Удаляем временный файл
            if os.path.exists(temp_video):
                os.remove(temp_video)

            if success:
                print(f"Готово: {meeting_config.output_path}")
                if progress_cb:
                    progress_cb(100.0)
                return True
            else:
                return False

        except Exception as e:
            print(f"Ошибка экспорта видео: {e}")
            return False

    def _create_video_frames(
        self,
        composition_engine: CompositionEngine,
        background: np.ndarray,
        cap1: cv2.VideoCapture,
        cap2: cv2.VideoCapture,
        max_frames: int,
        output_fps: float,
        temp_video: str,
        meeting_config: MeetingConfig,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> bool:
        """Создание кадров видео"""
        try:
            # Настройка видеописателя
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(
                temp_video,
                fourcc,
                output_fps,
                (self.export_config.width, self.export_config.height),
            )

            # Имена спикеров передаются через параметры метода

            frame_idx = 0
            while frame_idx < max_frames:
                # Чтение кадров
                ret1, frame1 = cap1.read()
                ret2, frame2 = cap2.read()

                if not ret1 or frame1 is None:
                    frame1_used = None
                else:
                    frame1_used = frame1

                if not ret2 or frame2 is None:
                    frame2_used = None
                else:
                    frame2_used = frame2

                    # Создание композиции и запись кадра
                composed_frame = composition_engine.compose_frame(
                    background,
                    frame1_used,
                    frame2_used,
                    meeting_config.speaker1_name,
                    meeting_config.speaker2_name,
                )
                out.write(composed_frame)
                frame_idx += 1

                # Прогресс
                if progress_cb and max_frames > 0:
                    # Отдаём прогресс этапа кадров в диапазоне 10..90%
                    frames_part = 10.0 + (frame_idx / max_frames) * 80.0
                    progress_cb(min(frames_part, 90.0))

            # Имена спикеров больше не хранятся в конфигурации

            out.release()
            return True

        except Exception as e:
            print(f"Ошибка создания кадров: {e}")
            return False

    def _combine_video_audio(
        self, temp_video: str, mixed_audio: Optional[np.ndarray], output_path: str
    ) -> bool:
        """Объединение видео и аудио с GPU→CPU фолбэком и расширенным логированием."""

        def run_ffmpeg(command: list, label: str) -> bool:
            try:
                completed = subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if completed.stdout:
                    print(completed.stdout)
                return True
            except subprocess.CalledProcessError as ex:
                print(f"FFmpeg ошибка на этапе {label}: code={ex.returncode}")
                if ex.stderr:
                    print(ex.stderr)
                return False

        # Подготовка команд для варианта с аудио и без аудио
        if mixed_audio is not None:
            temp_audio = tempfile.mktemp(suffix=".wav")
            self.audio_processor.save_audio(mixed_audio, temp_audio)

            # Текущие (возможно GPU) параметры
            gpu_cmd = ["ffmpeg", "-i", temp_video, "-i", temp_audio]
            gpu_cmd.extend(self._get_video_codec_params())
            gpu_cmd.extend(
                [
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-shortest",
                    "-movflags",
                    "+faststart",
                    "-y",
                    output_path,
                ]
            )

            if run_ffmpeg(gpu_cmd, "GPU/текущий кодек (с аудио)"):
                os.remove(temp_audio)
                print("Видео с аудио создано успешно")
                return True

            # Фолбэк на CPU libx264
            cpu_cmd = ["ffmpeg", "-i", temp_video, "-i", temp_audio]
            cpu_cmd.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    self.export_config.video_codec.preset,
                    "-crf",
                    str(self.export_config.video_codec.crf),
                    "-b:v",
                    self.export_config.video_codec.bitrate,
                ]
            )
            cpu_cmd.extend(
                [
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-shortest",
                    "-movflags",
                    "+faststart",
                    "-y",
                    output_path,
                ]
            )

            if run_ffmpeg(cpu_cmd, "CPU libx264 (с аудио)"):
                os.remove(temp_audio)
                print(
                    "GPU-кодирование не удалось, использован CPU libx264. Видео с аудио создано"
                )
                return True

            # Как крайний случай — попытка выдать видео без аудио
            try:
                os.remove(temp_audio)
            except OSError:
                pass
            try:
                os.rename(temp_video, output_path)
                print("FFmpeg не смог объединить аудио. Видео сохранено без аудио")
                return True
            except OSError:
                return False

        else:
            # Только видео: сначала пробуем текущий (возможно GPU) кодек
            gpu_cmd = ["ffmpeg", "-i", temp_video]
            gpu_cmd.extend(self._get_video_codec_params())
            gpu_cmd.extend(["-movflags", "+faststart", "-y", output_path])

            if run_ffmpeg(gpu_cmd, "GPU/текущий кодек (без аудио)"):
                print("Видео без аудио создано")
                return True

            # Фолбэк на CPU libx264
            cpu_cmd = [
                "ffmpeg",
                "-i",
                temp_video,
                "-c:v",
                "libx264",
                "-preset",
                self.export_config.video_codec.preset,
                "-crf",
                str(self.export_config.video_codec.crf),
                "-b:v",
                self.export_config.video_codec.bitrate,
                "-movflags",
                "+faststart",
                "-y",
                output_path,
            ]

            if run_ffmpeg(cpu_cmd, "CPU libx264 (без аудио)"):
                print(
                    "GPU-кодирование не удалось, использован CPU libx264. Видео без аудио создано"
                )
                return True

            # Абсолютный фолбэк: просто переименовать временное видео
            try:
                os.rename(temp_video, output_path)
                print("FFmpeg не выполнился. Видео сохранено как есть (без аудио)")
                return True
            except OSError:
                return False

    def _get_video_codec_params(self) -> list:
        """Получение параметров видео кодека"""
        gpu_codec = self.export_config.gpu_config.gpu_codec

        if gpu_codec == "h264_nvenc":
            return [
                "-c:v",
                "h264_nvenc",
                "-preset",
                "fast",
                "-rc",
                "vbr",
                "-cq",
                str(self.export_config.video_codec.crf),
                "-b:v",
                self.export_config.video_codec.bitrate,
                "-maxrate",
                self.export_config.video_codec.bitrate,
                "-bufsize",
                str(int(self.export_config.video_codec.bitrate.replace("k", "")) * 2)
                + "k",
            ]
        elif gpu_codec == "h264_qsv":
            return [
                "-c:v",
                "h264_qsv",
                "-preset",
                "fast",
                "-global_quality",
                str(self.export_config.video_codec.crf),
                "-b:v",
                self.export_config.video_codec.bitrate,
            ]
        elif gpu_codec == "h264_vaapi":
            return [
                "-c:v",
                "h264_vaapi",
                "-qp",
                str(self.export_config.video_codec.crf),
                "-b:v",
                self.export_config.video_codec.bitrate,
            ]
        else:
            # CPU кодирование
            return [
                "-c:v",
                self.export_config.video_codec.codec,
                "-preset",
                self.export_config.video_codec.preset,
                "-crf",
                str(self.export_config.video_codec.crf),
                "-b:v",
                self.export_config.video_codec.bitrate,
            ]
