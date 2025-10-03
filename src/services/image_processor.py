"""
Сервис обработки изображений: предоставляет функции для загрузки, изменения размера
и наложения изображений с использованием OpenCV (cv2) и PIL (Pillow),
а также для создания пользовательских графических плашек с именами.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple
from ..models.speaker_config import SpeakerConfig
import matplotlib.font_manager as fm


def get_text_size(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont
) -> tuple[float, float]:
    """
    Возвращает ширину и высоту текста для плашки.
    Работает с Pillow >= 10.
    """
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    return width, height


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
        self,
        name: str,
        width: int,
        font_size: int = 24,
        font_color: Tuple[int, int, int] = (255, 255, 255),
        bg_color: Tuple[int, int, int, int] = (0, 0, 0, 180),
        border_color: Tuple[int, int, int] = (255, 255, 255),
        border_width: int = 2,
        padding: int = 10,
        font_family: str = "Arial",
    ) -> Image.Image:
        """
        Создает плашку с именем спикера.

        :param name: Текст для плашки
        :param width: Ширина плашки (обычно ширина окна спикера)
        :param font_size: Размер шрифта
        :param font_color: Цвет текста (RGB)
        :param bg_color: Цвет фона плашки (RGBA)
        :param border_color: Цвет рамки (RGB)
        :param border_width: Толщина рамки
        :param padding: Внутренние отступы вокруг текста
        :param font_family: Название шрифта
        :return: PIL.Image с плашкой
        """
        # 1. Загружаем шрифт
        try:
            font_path = fm.findSystemFonts(fontpaths=None, fontext="ttf")
            font_paths = {ImageFont.truetype(f).getname()[0]: f for f in font_path}
            path = font_paths.get(font_family, None)
            if path:
                font = ImageFont.truetype(path, font_size)
            else:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # 2. Вычисляем размер текста
        dummy_img = Image.new("RGBA", (width, 100))
        draw = ImageDraw.Draw(dummy_img)
        text_w, text_h = get_text_size(draw, name, font)

        plate_width = width
        plate_height = text_h + 2 * padding

        # 3. Создаем прозрачное изображение плашки
        plate = Image.new("RGBA", (plate_width, plate_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(plate)

        # 4. Рисуем фон
        draw.rectangle(
            [0, 0, plate_width, plate_height],
            fill=bg_color,
            outline=border_color,
            width=border_width,
        )

        # 5. Рисуем текст по центру
        text_x = (plate_width - text_w) // 2
        text_y = (plate_height - text_h) // 2
        draw.text((text_x, text_y), name, font=font, fill=font_color)

        return plate

    def _load_font(self) -> ImageFont.FreeTypeFont:
        """
        Загрузка шрифта по имени или пути из SpeakerConfig.
        Если не удалось — fallback на стандартный.
        """
        font_path_or_name = getattr(self.speaker_config, "font_family", None)
        font_size = getattr(self.speaker_config, "font_size", 24)

        try:
            if font_path_or_name:
                # Если передан путь к ttf
                return ImageFont.truetype(font_path_or_name, font_size)
            else:
                # Попытка загрузить системный шрифт по имени
                return ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except (OSError, IOError):
            try:
                return ImageFont.truetype("arial.ttf", font_size)
            except (OSError, IOError):
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
