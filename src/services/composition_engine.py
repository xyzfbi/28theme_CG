"""
Движок композиции кадров
"""

import numpy as np
import cv2
from typing import Optional, Tuple
from ..models.speaker_config import SpeakerConfig
from ..models.export_config import ExportConfig
from .video_processor import VideoProcessor
from .image_processor import ImageProcessor


class CompositionEngine:
    """Движок для композиции кадров видеовстречи"""

    def __init__(self, speaker_config: SpeakerConfig, export_config: ExportConfig):
        self.speaker_config = speaker_config
        self.export_config = export_config
        self.video_processor = VideoProcessor(export_config)
        self.image_processor = ImageProcessor(speaker_config)

    def compose_frame_with_names(
        self,
        background: np.ndarray,
        speaker1_frame: Optional[np.ndarray],
        speaker2_frame: Optional[np.ndarray],
        speaker1_name: str,
        speaker2_name: str,
    ) -> np.ndarray:
        """Композиция кадра с именами спикеров"""
        return self.compose_frame(
            background, speaker1_frame, speaker2_frame, speaker1_name, speaker2_name
        )

    def compose_frame(
        self,
        background: np.ndarray,
        speaker1_frame: Optional[np.ndarray],
        speaker2_frame: Optional[np.ndarray],
        speaker1_name: str = "",
        speaker2_name: str = "",
    ) -> np.ndarray:
        """Композиция одного кадра"""
        # Изменение размера фона
        background_resized = cv2.resize(
            background,
            (self.export_config.width, self.export_config.height),
            interpolation=cv2.INTER_LANCZOS4,
        )
        result = background_resized.copy()

        # Вычисление позиций спикеров
        speaker1_pos, speaker2_pos = self._calculate_speaker_positions()

        # Обработка первого спикера
        if speaker1_frame is not None:
            result = self._add_speaker_to_frame(
                result, speaker1_frame, speaker1_pos, speaker1_name
            )

        # Обработка второго спикера
        if speaker2_frame is not None:
            result = self._add_speaker_to_frame(
                result, speaker2_frame, speaker2_pos, speaker2_name
            )

        return result

    def _calculate_speaker_positions(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Вычисление позиций спикеров"""
        half_width = self.export_config.width // 2

        if self.speaker_config.position is not None:
            speaker1_pos = self.speaker_config.position.to_tuple()
            speaker2_pos = (half_width + 100, self.speaker_config.position.y)
        else:
            # Автоматическое центрирование
            speaker1_x = (half_width - self.speaker_config.width) // 2
            speaker1_y = (self.export_config.height - self.speaker_config.height) // 2
            speaker1_pos = (speaker1_x, speaker1_y)

            speaker2_x = half_width + (half_width - self.speaker_config.width) // 2
            speaker2_y = (self.export_config.height - self.speaker_config.height) // 2
            speaker2_pos = (speaker2_x, speaker2_y)

        return speaker1_pos, speaker2_pos

    def _add_speaker_to_frame(
        self,
        frame: np.ndarray,
        speaker_frame: np.ndarray,
        position: Tuple[int, int],
        name: str,
    ) -> np.ndarray:
        """Добавление спикера на кадр"""
        x, y = position

        # Изменяем размер кадра спикера
        speaker_resized = self.video_processor.resize_with_aspect_ratio(
            speaker_frame, self.speaker_config.width, self.speaker_config.height
        )

        # Проверяем границы
        if (
            y + self.speaker_config.height <= self.export_config.height
            and x + self.speaker_config.width <= self.export_config.width
        ):
            # Размещаем спикера
            frame[
                y : y + self.speaker_config.height, x : x + self.speaker_config.width
            ] = speaker_resized

            # Добавляем плашку с именем
            if name:
                frame = self._add_name_plate(frame, x, y, name)

        return frame

    def _add_name_plate(
        self, frame: np.ndarray, speaker_x: int, speaker_y: int, name: str
    ) -> np.ndarray:
        """Добавление плашки с именем"""
        # Создаем плашку
        plate = self.image_processor.create_name_plate(name, self.speaker_config.width)
        plate_np = cv2.cvtColor(np.array(plate), cv2.COLOR_RGBA2BGRA)

        # Позиция плашки (под спикером)
        plate_y = speaker_y + self.speaker_config.height + 5
        plate_height = plate_np.shape[0]

        if plate_y + plate_height <= self.export_config.height:
            # Центрируем плашку по ширине окна спикера
            plate_width = plate_np.shape[1]
            plate_x = speaker_x + (self.speaker_config.width - plate_width) // 2

            if plate_x + plate_width <= speaker_x + self.speaker_config.width:
                # Накладываем плашку с альфа-каналом
                if plate_np.shape[2] == 4:  # RGBA
                    alpha = plate_np[:, :, 3] / 255.0
                    for c in range(3):
                        frame[
                            plate_y : plate_y + plate_height,
                            plate_x : plate_x + plate_width,
                            c,
                        ] = (
                            alpha * plate_np[:, :, c]
                            + (1 - alpha)
                            * frame[
                                plate_y : plate_y + plate_height,
                                plate_x : plate_x + plate_width,
                                c,
                            ]
                        )

        return frame

    def create_preview(
        self,
        background_path: str,
        speaker1_path: str,
        speaker2_path: str,
        speaker1_name: str,
        speaker2_name: str,
        output_path: str = "preview.jpg",
    ) -> bool:
        """Создание предпросмотра"""
        try:
            # Загружаем фон
            background = cv2.imread(background_path)
            if background is None:
                print(f"Не удалось загрузить фоновое изображение: {background_path}")
                return False

            # Загружаем видео спикеров
            cap1 = cv2.VideoCapture(speaker1_path)
            cap2 = cv2.VideoCapture(speaker2_path)

            if not cap1.isOpened():
                print(f"Не удалось открыть видео файл: {speaker1_path}")
                return False
            if not cap2.isOpened():
                print(f"Не удалось открыть видео файл: {speaker2_path}")
                cap1.release()
                return False

            # Получаем первый кадр
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()

            if not ret1:
                print(f"Не удалось прочитать кадр из видео: {speaker1_path}")
                cap1.release()
                cap2.release()
                return False
            if not ret2:
                print(f"Не удалось прочитать кадр из видео: {speaker2_path}")
                cap1.release()
                cap2.release()
                return False

            # Создаем композицию с именами спикеров
            composed_frame = self.compose_frame_with_names(
                background, frame1, frame2, speaker1_name, speaker2_name
            )

            # Сохраняем предпросмотр
            cv2.imwrite(output_path, composed_frame)

            # Освобождаем ресурсы
            cap1.release()
            cap2.release()

            return True

        except Exception as e:
            print(f"Ошибка создания предпросмотра: {e}")
            return False
