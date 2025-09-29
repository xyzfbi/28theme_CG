"""
Сервис обработки видео
"""

import cv2
import numpy as np
from typing import Optional
from ..models.export_config import ExportConfig


class VideoProcessor:
    """Сервис для обработки видео файлов"""

    def __init__(self, export_config: ExportConfig):
        self.export_config = export_config

    def load_video(self, video_path: str) -> cv2.VideoCapture:
        """Загрузка видео файла"""
        if not video_path:
            raise ValueError("Путь к видео не может быть пустым")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видео файл: {video_path}")

        return cap

    def get_video_info(self, cap: cv2.VideoCapture) -> dict:
        """Получение информации о видео"""
        return {
            "fps": cap.get(cv2.CAP_PROP_FPS),
            "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "duration": cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS),
        }

    def read_frame(self, cap: cv2.VideoCapture) -> Optional[np.ndarray]:
        """Чтение кадра из видео"""
        ret, frame = cap.read()
        return frame if ret else None

    def resize_with_aspect_ratio(
        self, image: np.ndarray, target_width: int, target_height: int
    ) -> np.ndarray:
        """Изменение размера изображения с сохранением пропорций"""
        h, w = image.shape[:2]
        aspect_ratio = w / h

        if target_width / target_height > aspect_ratio:
            new_height = target_height
            new_width = int(target_height * aspect_ratio)
        else:
            new_width = target_width
            new_height = int(target_width / aspect_ratio)

        resized = cv2.resize(
            image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4
        )

        # Создание изображения нужного размера с черным фоном
        result = np.zeros((target_height, target_width, 3), dtype=np.uint8)

        # Центрирование изображения
        y_offset = (target_height - new_height) // 2
        x_offset = (target_width - new_width) // 2
        result[y_offset : y_offset + new_height, x_offset : x_offset + new_width] = (
            resized
        )

        return result

    def calculate_output_fps(self, fps1: float, fps2: float) -> float:
        """Вычисление выходного FPS"""
        return min(fps1, fps2, self.export_config.fps)

    def calculate_max_frames(self, frame_count1: int, frame_count2: int) -> int:
        """Вычисление максимального количества кадров"""
        return max(frame_count1, frame_count2)
