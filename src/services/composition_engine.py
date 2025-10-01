"""
Движок композиции кадров: объединяет видео- и графические сервисы для создания
единого кадра или последовательности кадров, формирующих финальное видео.
"""

import numpy as np
import cv2
from typing import Optional, Tuple
from ..models.speaker_config import SpeakerConfig
from ..models.export_config import ExportConfig
from .video_processor import VideoProcessor
from .image_processor import ImageProcessor


class CompositionEngine:
    """
    Движок для композиции кадров видеовстречи.

    Отвечает за расположение элементов (спикеры, плашки, фон) в кадре,
    обработку видеопотоков и создание итогового изображения.
    """

    def __init__(self, speaker_config: SpeakerConfig, export_config: ExportConfig):
        """
        Инициализация движка композиции.

        :param speaker_config: Конфигурация внешнего вида окон спикеров и плашек.
        :param export_config: Конфигурация выходного видео (разрешение, FPS).
        """
        self.speaker_config = speaker_config
        self.export_config = export_config
        # Инициализация дочерних сервисов, которые будут выполнять основную работу
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
        """
        Вспомогательный метод для композиции кадра с обязательным указанием имен спикеров.
        Просто вызывает основной метод `compose_frame`.

        :param background: Кадр фонового изображения.
        :param speaker1_frame: Текущий кадр первого спикера (может быть None).
        :param speaker2_frame: Текущий кадр второго спикера (может быть None).
        :param speaker1_name: Имя первого спикера.
        :param speaker2_name: Имя второго спикера.
        :return: Композиционный кадр.
        """
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
        """
        Композиция одного кадра: наложение кадров спикеров и их плашек на фон.

        :param background: Кадр фонового изображения.
        :param speaker1_frame: Текущий кадр первого спикера (может быть None).
        :param speaker2_frame: Текущий кадр второго спикера (может быть None).
        :param speaker1_name: Имя первого спикера.
        :param speaker2_name: Имя второго спикера.
        :return: Итоговый композиционный кадр в формате np.ndarray.
        """
        # 1. Изменение размера фона до целевого разрешения экспорта (например, 1920x1080)
        background_resized = cv2.resize(
            background,
            (self.export_config.width, self.export_config.height),
            interpolation=cv2.INTER_LANCZOS4,
        )
        result = background_resized.copy()

        # 2. Вычисление позиций окон спикеров
        speaker1_pos, speaker2_pos = self._calculate_speaker_positions()

        # 3. Обработка первого спикера
        if speaker1_frame is not None:
            result = self._add_speaker_to_frame(
                result, speaker1_frame, speaker1_pos, speaker1_name
            )

        # 4. Обработка второго спикера
        if speaker2_frame is not None:
            result = self._add_speaker_to_frame(
                result, speaker2_frame, speaker2_pos, speaker2_name
            )

        return result

    def _calculate_speaker_positions(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """
        Вычисляет координаты (x, y) верхнего левого угла для окон двух спикеров.

        В текущей реализации:
        - Если position не задан, спикеры центрируются по вертикали и
          размещаются симметрично в левой и правой половине кадра.
        - Если position задан, используется фиксированная позиция для спикера 1,
          а спикер 2 смещается вправо (логика требует наличия PositionConfig в моделях).

        :return: Кортеж из двух кортежей: (позиция_спикера_1, позиция_спикера_2).
        """
        output_w = self.export_config.width
        output_h = self.export_config.height
        speaker_w = self.speaker_config.width
        speaker_h = self.speaker_config.height
        half_width = output_w // 2

        if self.speaker_config.position is not None:
            # Логика для фиксированной позиции (требует, чтобы PositionConfig был определен)
            speaker1_pos = self.speaker_config.position.to_tuple()
            speaker2_pos = (half_width + 100, self.speaker_config.position.y)
        else:
            # Автоматическое центрирование (размещение в двух половинах кадра)
            # Y-координата (центрирование по вертикали)
            center_y = (output_h - speaker_h) // 2

            # X-координата для Спикера 1 (центрирование в левой половине)
            speaker1_x = (half_width - speaker_w) // 2
            speaker1_pos = (speaker1_x, center_y)

            # X-координата для Спикера 2 (центрирование в правой половине)
            speaker2_x = half_width + (half_width - speaker_w) // 2
            speaker2_pos = (speaker2_x, center_y)

        return speaker1_pos, speaker2_pos

    def _add_speaker_to_frame(
        self,
        frame: np.ndarray,
        speaker_frame: np.ndarray,
        position: Tuple[int, int],
        name: str,
    ) -> np.ndarray:
        """
        Добавляет кадр спикера и его плашку на основной кадр.

        :param frame: Текущий композиционный кадр (фон).
        :param speaker_frame: Кадр спикера, который нужно добавить.
        :param position: Координаты (x, y) верхнего левого угла для размещения спикера.
        :param name: Имя спикера для плашки.
        :return: Обновленный кадр.
        """
        x, y = position

        # 1. Изменяем размер кадра спикера с сохранением пропорций (letterboxing)
        speaker_resized = self.video_processor.resize_with_aspect_ratio(
            speaker_frame, self.speaker_config.width, self.speaker_config.height
        )

        # 2. Проверяем, что окно спикера полностью помещается в кадр
        if (
            y + self.speaker_config.height <= self.export_config.height
            and x + self.speaker_config.width <= self.export_config.width
        ):
            # Размещаем масштабированный кадр спикера в ROI (области интереса)
            frame[
                y : y + self.speaker_config.height, x : x + self.speaker_config.width
            ] = speaker_resized

            # 3. Добавляем плашку с именем, если имя задано
            if name:
                frame = self._add_name_plate(frame, x, y, name)

        return frame

    def _add_name_plate(
        self, frame: np.ndarray, speaker_x: int, speaker_y: int, name: str
    ) -> np.ndarray:
        """
        Создает и накладывает плашку с именем под окном спикера.

        :param frame: Кадр для наложения.
        :param speaker_x: X-координата окна спикера.
        :param speaker_y: Y-координата окна спикера.
        :param name: Имя, которое будет отображено на плашке.
        :return: Обновленный кадр.
        """
        # 1. Создаем плашку в формате PIL и конвертируем в BGRA numpy array
        plate_pil = self.image_processor.create_name_plate(
            name, self.speaker_config.width
        )
        # Используем сервис конвертации для получения BGRA массива с альфа-каналом
        plate_np = self.image_processor.convert_pil_to_cv2(plate_pil)

        # 2. Вычисляем позицию плашки (смещение на 5px ниже окна спикера)
        plate_height = plate_np.shape[0]
        plate_y = speaker_y + self.speaker_config.height + 5

        # 3. Проверка границ: плашка должна помещаться по высоте
        if plate_y + plate_height <= self.export_config.height:
            # 4. Центрируем плашку по ширине окна спикера
            plate_width = plate_np.shape[1]
            plate_x = speaker_x + (self.speaker_config.width - plate_width) // 2

            # 5. Накладываем плашку с альфа-каналом, используя ImageProcessor.overlay_image
            # Это обеспечивает чистое наложение с учетом прозрачности фона плашки.
            if plate_x >= 0 and plate_y >= 0:
                frame = self.image_processor.overlay_image(
                    frame,
                    plate_np,
                    plate_x,
                    plate_y,
                    alpha=1.0,  # Плашка накладывается полностью
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
        """
        Создает один кадр предпросмотра, используя первый кадр каждого видеопотока.
        Это синхронная операция, предназначенная для быстрого отображения в UI.

        :param background_path: Путь к фоновому изображению.
        :param speaker1_path: Путь к видео первого спикера.
        :param speaker2_path: Путь к видео второго спикера.
        :param speaker1_name: Имя первого спикера.
        :param speaker2_name: Имя второго спикера.
        :param output_path: Путь для сохранения итогового JPG-файла предпросмотра.
        :return: True, если предпросмотр успешно создан, иначе False.
        """
        try:
            # 1. Загружаем фон, используя ImageProcessor
            background = self.image_processor.load_image(background_path)
            if background is None:
                return False

            # 2. Загружаем видео спикеров, используя VideoProcessor
            cap1 = self.video_processor.load_video(speaker1_path)
            cap2 = self.video_processor.load_video(speaker2_path)

            if not cap1.isOpened() or not cap2.isOpened():
                # Проверки уже выполнены внутри load_video, но лучше убедиться
                print("Не удалось открыть один или оба видео файла.")
                if cap1.isOpened():
                    cap1.release()
                if cap2.isOpened():
                    cap2.release()
                return False

            # 3. Получаем первый кадр
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()

            if not ret1 or not ret2:
                print("Не удалось прочитать кадры из видео.")
                cap1.release()
                cap2.release()
                return False

            # 4. Создаем композицию
            composed_frame = self.compose_frame_with_names(
                background, frame1, frame2, speaker1_name, speaker2_name
            )

            # 5. Сохраняем предпросмотр
            cv2.imwrite(output_path, composed_frame)

            # 6. Освобождаем ресурсы
            cap1.release()
            cap2.release()

            return True

        except Exception as e:
            # Общий обработчик ошибок
            print(f"Ошибка создания предпросмотра: {e}")
            return False
