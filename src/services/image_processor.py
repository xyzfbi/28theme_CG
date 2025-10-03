"""
Сервис обработки изображений: предоставляет функции для загрузки, изменения размера
и наложения изображений с использованием OpenCV (cv2) и PIL (Pillow),
а также для создания пользовательских графических плашек с именами.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Optional
from ..models.speaker_config import SpeakerConfig


class ImageProcessor:
    """
    Сервис для обработки изображений и создания плашек (name plates).

    Использует библиотеку PIL (Pillow) для работы с текстом и графикой,
    а OpenCV (cv2) для загрузки, изменения размера и наложения массивов NumPy.
    """

    def __init__(self, speaker_config: SpeakerConfig):
        """
        Инициализация ImageProcessor.

        :param speaker_config: Конфигурация внешнего вида спикера, содержащая
                              настройки плашек (размеры, шрифты, цвета).
        """
        self.speaker_config = speaker_config

    @staticmethod
    def load_image(image_path: str) -> Optional[np.ndarray]:
        """
        Загружает изображение с диска в формате OpenCV (BGR numpy array).

        :param image_path: Полный путь к файлу изображения.
        :return: Изображение в виде массива numpy (BGR), или None в случае ошибки.
        :raises ValueError: Если изображение не удалось загрузить или оно пусто.
        """
        try:
            # Чтение изображения с помощью OpenCV
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Не удалось загрузить изображение: {image_path}")
            return image
        except Exception as e:
            # Вывод ошибки в консоль при возникновении проблем с файлом
            print(f"Ошибка загрузки изображения {image_path}: {e}")
            return None

    def create_name_plate(
        self, name: str, min_width: Optional[int] = None
    ) -> Image.Image:
        """
        Создает графическую плашку (name plate) с заданным именем, используя PIL.
        Размер плашки автоматически подстраивается под текст, с учетом минимальной ширины.

        :param name: Текст, который должен быть отображен на плашке (имя спикера).
        :param min_width: Минимальная ширина плашки. Если текст шире, используется его ширина.
        :return: Объект PIL.Image с готовой плашкой в формате RGBA.
        """
        # 1. Загрузка шрифта
        font = self._load_font()

        # 2. Измерение текста (требуется временный холст для получения размеров)
        temp_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(temp_img)

        # Получаем ограничивающую рамку текста
        bbox = draw.textbbox((0, 0), name, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 3. Вычисляем размеры плашки
        padding = self.speaker_config.plate_padding

        # Ширина: текст + отступы, но не меньше минимальной ширины
        plate_width = max(text_width + padding * 2, min_width or 0)
        # Высота: текст + отступы, но не меньше минимальной высоты
        plate_height = max(text_height + padding * 2, 50)

        # Приведение к целому типу для PIL
        plate_width = int(plate_width)
        plate_height = int(plate_height)

        # 4. Создание плашки (RGBA для поддержки прозрачности)
        plate = Image.new(
            "RGBA",
            (plate_width, plate_height),
            self.speaker_config.plate_bg_color,  # Цвет фона из конфига
        )
        draw = ImageDraw.Draw(plate)

        # 5. Центрирование текста
        # Вычисляем смещение текста, чтобы он был по центру плашки
        text_x = (plate_width - text_width) // 2
        text_y = (plate_height - text_height) // 2

        # 6. Рисуем рамку
        draw.rectangle(
            [0, 0, plate_width - 1, plate_height - 1],
            outline=self.speaker_config.plate_border_color,
            width=self.speaker_config.plate_border_width,
        )

        # 7. Рисуем сам текст
        draw.text(
            (text_x, text_y), name, font=font, fill=self.speaker_config.font_color
        )

        return plate

    def _load_font(self) -> ImageFont.FreeTypeFont:
        """
        Загрузка шрифта с диска по указанным путям.
        Предусмотрены несколько fallback-путей для повышения совместимости между ОС.

        :return: Объект ImageFont.FreeTypeFont. В случае неудачи загружается стандартный шрифт.
        """
        # 0) Пользовательский путь к шрифту, если задан в конфиге
        if self.speaker_config.font_path:
            try:
                return ImageFont.truetype(
                    self.speaker_config.font_path, self.speaker_config.font_size
                )
            except (OSError, IOError):
                # Переходим к фолбэкам ниже
                pass

        # 1) Попытка загрузить системный шрифт Linux (DejaVuSans-Bold)
        try:
            return ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                self.speaker_config.font_size,
            )
        except (OSError, IOError):
            # 2) Попытка загрузить шрифт Arial (часто используется в Windows)
            try:
                return ImageFont.truetype("arial.ttf", self.speaker_config.font_size)
            except (OSError, IOError):
                # 3) Полный фолбэк: стандартный шрифт PIL
                return ImageFont.load_default()

    @staticmethod
    def overlay_image(
        background: np.ndarray,
        overlay: np.ndarray,
        x: int,
        y: int,
        alpha: float = 1.0,
    ) -> np.ndarray:
        """
        Наложение изображения (overlay) на фоновое изображение (background)
        с поддержкой прозрачности (альфа-канал).

        :param background: Фон (OpenCV BGR/BGRA numpy array).
        :param overlay: Изображение для наложения (может быть BGR или BGRA numpy array).
        :param x: Координата X левого верхнего угла наложения.
        :param y: Координата Y левого верхнего угла наложения.
        :param alpha: Общий коэффициент прозрачности для наложения (от 0.0 до 1.0).
        :return: Фоновое изображение с наложенным объектом.
        """
        # Создаем копию фона, чтобы не изменять его напрямую
        result = background.copy()

        h, w = overlay.shape[:2]

        # Проверка границ: если наложение выходит за пределы фона, возвращаем оригинал
        if y + h > background.shape[0] or x + w > background.shape[1]:
            return result

        # Определяем область интереса (ROI) на фоновом изображении, куда будет накладываться объект
        bg_roi = result[y : y + h, x : x + w]

        if (
            overlay.shape[2] == 4
        ):  # Если наложение имеет 4 канала (BGRA) - работаем с прозрачностью
            # BGR часть и альфа-канал, нормализованный и умноженный на общий коэффициент alpha
            overlay_bgr = overlay[:, :, :3]
            overlay_alpha = overlay[:, :, 3] / 255.0 * alpha

            # Выполняем альфа-смешивание (alpha blending) по каждому из трех цветовых каналов
            for c in range(3):
                # Формула: (новое значение) = (альфа * наложение) + ((1 - альфа) * фон)
                bg_roi[:, :, c] = (
                    overlay_alpha * overlay_bgr[:, :, c]
                    + (1 - overlay_alpha) * bg_roi[:, :, c]
                ).astype(np.uint8)  # Преобразуем обратно в np.uint8
        else:  # Если наложение имеет 3 канала (BGR) - простое смешивание
            # Используем cv2.addWeighted для смешивания с заданным весом alpha
            bg_roi[:] = cv2.addWeighted(bg_roi, 1 - alpha, overlay, alpha, 0)

        return result

    @staticmethod
    def convert_pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
        """
        Конвертирует изображение из формата PIL.Image (RGBA) в формат OpenCV
        (BGRA numpy array).

        Это необходимо для корректного наложения с сохранением альфа-канала.

        :param pil_image: Изображение в формате PIL.Image.
        :return: Изображение в формате BGRA numpy array для OpenCV.
        """
        # Преобразуем PIL Image в numpy array (RGBA)
        np_array = np.array(pil_image)
        # Конвертируем из RGBA (формат PIL) в BGRA (предпочтительный 4-канальный формат OpenCV)
        return cv2.cvtColor(np_array, cv2.COLOR_RGBA2BGRA)
