"""
Сервис обработки изображений
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from typing import Optional
from ..models.speaker_config import SpeakerConfig


class ImageProcessor:
    """Сервис для обработки изображений и создания плашек"""

    def __init__(self, speaker_config: SpeakerConfig):
        self.speaker_config = speaker_config

    def load_image(self, image_path: str) -> Optional[np.ndarray]:
        """Загрузка изображения"""
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(f"Не удалось загрузить изображение: {image_path}")
            return image
        except Exception as e:
            print(f"Ошибка загрузки изображения {image_path}: {e}")
            return None

    def resize_image(self, image: np.ndarray, width: int, height: int) -> np.ndarray:
        """Изменение размера изображения"""
        return cv2.resize(image, (width, height), interpolation=cv2.INTER_LANCZOS4)

    def create_name_plate(
        self, name: str, min_width: Optional[int] = None
    ) -> Image.Image:
        """Создание плашки с именем"""
        font = self._load_font()

        # Создаем временное изображение для измерения текста
        temp_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(temp_img)

        bbox = draw.textbbox((0, 0), name, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Вычисляем размеры плашки
        plate_width = max(
            text_width + self.speaker_config.plate_padding * 2, min_width or 0
        )
        plate_height = max(text_height + self.speaker_config.plate_padding * 2, 50)

        # Создаем плашку
        plate = Image.new(
            "RGBA", (plate_width, plate_height), self.speaker_config.plate_bg_color
        )
        draw = ImageDraw.Draw(plate)

        # Центрируем текст
        text_x = (plate_width - text_width) // 2
        text_y = (plate_height - text_height) // 2

        # Рисуем рамку
        draw.rectangle(
            [0, 0, plate_width - 1, plate_height - 1],
            outline=self.speaker_config.plate_border_color,
            width=self.speaker_config.plate_border_width,
        )

        # Рисуем текст
        draw.text(
            (text_x, text_y), name, font=font, fill=self.speaker_config.font_color
        )

        return plate

    def _load_font(self) -> ImageFont.FreeTypeFont:
        """Загрузка шрифта"""
        try:
            return ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                self.speaker_config.font_size,
            )
        except (OSError, IOError):
            try:
                return ImageFont.truetype("arial.ttf", self.speaker_config.font_size)
            except (OSError, IOError):
                return ImageFont.load_default()

    def overlay_image(
        self,
        background: np.ndarray,
        overlay: np.ndarray,
        x: int,
        y: int,
        alpha: float = 1.0,
    ) -> np.ndarray:
        """Наложение изображения на фон"""
        result = background.copy()

        h, w = overlay.shape[:2]
        if y + h > background.shape[0] or x + w > background.shape[1]:
            return result

        if overlay.shape[2] == 4:  # RGBA
            overlay_bgr = cv2.cvtColor(overlay, cv2.COLOR_RGBA2BGRA)
            overlay_alpha = overlay_bgr[:, :, 3] / 255.0 * alpha

            for c in range(3):
                result[y : y + h, x : x + w, c] = (
                    overlay_alpha * overlay_bgr[:, :, c]
                    + (1 - overlay_alpha) * result[y : y + h, x : x + w, c]
                )
        else:  # BGR
            result[y : y + h, x : x + w] = cv2.addWeighted(
                result[y : y + h, x : x + w], 1 - alpha, overlay, alpha, 0
            )

        return result

    def convert_pil_to_cv2(self, pil_image: Image.Image) -> np.ndarray:
        """Конвертация PIL изображения в OpenCV формат"""
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGBA2BGRA)
