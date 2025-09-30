"""
Сервис обработки видео: предоставляет утилиты и методы для работы с видеофайлами
с использованием библиотеки OpenCV (cv2), включая загрузку, получение информации,
чтение кадров и изменение размеров с сохранением пропорций.
"""

import cv2
import numpy as np
from ..models.export_config import ExportConfig


class VideoProcessor:
    """
    Сервис для обработки видео файлов.

    Отвечает за низкоуровневые операции с видеопотоками,
    такие как загрузка, чтение и трансформация кадров.
    """

    def __init__(self, export_config: ExportConfig):
        """
        Инициализация VideoProcessor.

        :param export_config: Конфигурация экспорта, содержащая, в частности,
                              желаемый FPS выходного видео.
        """
        self.export_config = export_config

    @staticmethod
    def load_video(video_path: str) -> cv2.VideoCapture:
        """
        Загружает видео файл и возвращает объект cv2.VideoCapture.

        :param video_path: Полный путь к видео файлу.
        :return: Объект cv2.VideoCapture.
        :raises ValueError: Если путь пуст или файл не удалось открыть.
        """
        if not video_path:
            raise ValueError("Путь к видео не может быть пустым")

        # Пытаемся открыть видео с помощью OpenCV
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Не удалось открыть видео файл: {video_path}")

        return cap

    @staticmethod
    def get_video_info(cap: cv2.VideoCapture) -> dict:
        """
        Получает ключевую информацию о видео из объекта cv2.VideoCapture.

        :param cap: Открытый объект cv2.VideoCapture.
        :return: Словарь с информацией: 'fps', 'frame_count', 'width', 'height', 'duration'.
        """
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Расчет длительности, избегая деления на ноль, если FPS не определен
        duration = frame_count / fps if fps else 0

        return {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "duration": duration,
        }

    @staticmethod
    def resize_with_aspect_ratio(
        image: np.ndarray, target_width: int, target_height: int
    ) -> np.ndarray:
        """
        Изменяет размер изображения с сохранением пропорций (letterboxing).

        Изображение масштабируется так, чтобы оно полностью вписалось в целевые
        размеры (target_width, target_height), а пустые области заполняются черным
        цветом (черные полосы).

        :param image: Исходное изображение (кадр) в виде np.ndarray.
        :param target_width: Желаемая ширина выходного кадра.
        :param target_height: Желаемая высота выходного кадра.
        :return: Измененное изображение с черными полосами, если необходимо.
        """
        h, w = image.shape[:2]
        aspect_ratio = w / h

        # 1. Определение новых размеров с сохранением пропорций
        if target_width / target_height > aspect_ratio:
            # Целевой контейнер шире, чем изображение -> масштабируем по высоте
            new_height = target_height
            new_width = int(target_height * aspect_ratio)
        else:
            # Целевой контейнер выше, чем изображение -> масштабируем по ширине
            new_width = target_width
            new_height = int(target_width / aspect_ratio)

        # Выполняем масштабирование. INTER_LANCZOS4 обеспечивает высокое качество.
        resized = cv2.resize(
            image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4
        )

        # 2. Создание черного "холста" (background)
        result = np.zeros((target_height, target_width, 3), dtype=np.uint8)

        # 3. Центрирование масштабированного изображения на холсте
        y_offset = (target_height - new_height) // 2
        x_offset = (target_width - new_width) // 2

        # Вставляем масштабированный кадр в центр
        result[y_offset : y_offset + new_height, x_offset : x_offset + new_width] = (
            resized
        )

        return result

    def calculate_output_fps(self, fps1: float, fps2: float) -> float:
        """
        Вычисляет окончательный FPS для композиции.

        Выбирается наименьшее значение из:
        1. FPS первого видео.
        2. FPS второго видео.
        3. Заданный FPS экспорта (из self.export_config).

        Это гарантирует, что мы не превысим частоту кадров самого медленного источника
        и желаемую частоту экспорта.

        :param fps1: FPS первого видео.
        :param fps2: FPS второго видео.
        :return: Окончательный FPS композиции.
        """
        return min(fps1, fps2, self.export_config.fps)

    @staticmethod
    def calculate_max_frames(frame_count1: int, frame_count2: int) -> int:
        """
        Вычисляет максимальное количество кадров (длину) из двух видеопотоков.
        Это необходимо для определения общей длительности итогового видео,
        которое должно быть не короче самого длинного исходного материала.

        :param frame_count1: Количество кадров первого видео.
        :param frame_count2: Количество кадров второго видео.
        :return: Максимальное количество кадров.
        """
        return max(frame_count1, frame_count2)
