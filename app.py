"""
🌐 Streamlit веб-приложение для создания видеовстреч
Интерактивный интерфейс для композиции видео с фоновым изображением и спикерами
"""

import streamlit as st
import sys
from pathlib import Path
import tempfile
import os
from typing import Tuple

# Добавляем src в путь для импортов
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services.composition_engine import CompositionEngine
from src.services.export_service import ExportService
from src.utils.logger import setup_logger
from src.models.meeting_config import MeetingConfig
from src.models.speaker_config import SpeakerConfig
from src.models.export_config import (
    ExportConfig,
    VideoCodecConfig,
    AudioCodecConfig,
    GPUConfig,
)

# Настройка страницы
st.set_page_config(
    page_title="Video Meeting Composer",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Инициализация логгера
logger = setup_logger()


def main():
    """Главная функция веб-приложения."""

    # Заголовок приложения
    st.title("🎥 Video Meeting Composer")
    st.markdown(
        "Создайте профессиональные видеовстречи из фонового изображения и видео спикеров"
    )

    # Создаем вкладки для разных разделов
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📁 Загрузка файлов",
            "⚙️ Настройки спикеров",
            "🎨 Настройки плашек",
            "📤 Экспорт",
            "🔍 Предпросмотр",
        ]
    )

    with tab1:
        st.header("📁 Загрузка файлов")

        # Загрузка фонового изображения
        st.subheader("🖼️ Фоновое изображение")
        background_file = st.file_uploader(
            "Выберите фоновое изображение",
            type=["jpg", "jpeg", "png", "bmp"],
            help="Поддерживаемые форматы: JPG, PNG, BMP",
        )

        # Загрузка видео спикеров
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🎤 Видео спикера 1")
            speaker1_file = st.file_uploader(
                "Выберите видео первого спикера",
                type=["mp4", "avi", "mov", "mkv"],
                key="speaker1",
                help="Поддерживаемые форматы: MP4, AVI, MOV, MKV",
            )
            speaker1_name = st.text_input(
                "Имя первого спикера",
                value="Спикер 1",
                key="name1",
                help="Имя, которое будет отображаться на плашке",
            )

        with col2:
            st.subheader("🎤 Видео спикера 2")
            speaker2_file = st.file_uploader(
                "Выберите видео второго спикера",
                type=["mp4", "avi", "mov", "mkv"],
                key="speaker2",
                help="Поддерживаемые форматы: MP4, AVI, MOV, MKV",
            )
            speaker2_name = st.text_input(
                "Имя второго спикера",
                value="Спикер 2",
                key="name2",
                help="Имя, которое будет отображаться на плашке",
            )

    with tab2:
        st.header("⚙️ Настройки спикеров")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📏 Размеры окон спикеров")
            speaker_width = st.slider(
                "Ширина окна спикера",
                min_value=200,
                max_value=800,
                value=400,
                step=50,
                help="Ширина окна для каждого спикера в пикселях",
            )
            speaker_height = st.slider(
                "Высота окна спикера",
                min_value=150,
                max_value=600,
                value=300,
                step=50,
                help="Высота окна для каждого спикера в пикселях",
            )

        with col2:
            st.subheader("📍 Позиционирование")
            auto_position = st.checkbox(
                "Автоматическое центрирование",
                value=True,
                help="Автоматически центрировать спикеров в своих половинах экрана",
            )

            if not auto_position:
                st.warning(
                    "⚠️ Ручное позиционирование будет добавлено в следующих версиях"
                )

    with tab3:
        st.header("🎨 Настройки плашек с именами")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🔤 Текст")
            font_size = st.slider(
                "Размер шрифта",
                min_value=12,
                max_value=48,
                value=24,
                step=2,
                help="Размер шрифта для текста на плашках",
            )

            # Цвет текста
            font_color = st.color_picker(
                "Цвет текста", value="#FFFFFF", help="Цвет текста на плашках"
            )

        with col2:
            st.subheader("🎨 Фон плашки")
            plate_bg_color = st.color_picker(
                "Цвет фона плашки",
                value="#000000",
                help="Цвет фона плашки (с прозрачностью)",
            )

            plate_border_color = st.color_picker(
                "Цвет рамки", value="#FFFFFF", help="Цвет рамки вокруг плашки"
            )

            plate_border_width = st.slider(
                "Толщина рамки",
                min_value=0,
                max_value=10,
                value=2,
                step=1,
                help="Толщина рамки в пикселях",
            )

            plate_padding = st.slider(
                "Отступы в плашке",
                min_value=5,
                max_value=30,
                value=10,
                step=5,
                help="Внутренние отступы в плашке",
            )

    with tab4:
        st.header("📤 Настройки экспорта")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📐 Разрешение видео")
            output_width = st.selectbox(
                "Ширина выходного видео",
                options=[1280, 1920, 2560, 3840],
                index=1,
                help="Ширина итогового видео в пикселях",
            )
            output_height = st.selectbox(
                "Высота выходного видео",
                options=[720, 1080, 1440, 2160],
                index=1,
                help="Высота итогового видео в пикселях",
            )

            fps = st.slider(
                "FPS (кадров в секунду)",
                min_value=24,
                max_value=60,
                value=30,
                step=6,
                help="Частота кадров выходного видео",
            )

        with col2:
            st.subheader("⚡ Оптимизация")
            ffmpeg_preset = st.selectbox(
                "Пресет FFmpeg",
                options=[
                    "ultrafast",
                    "superfast",
                    "veryfast",
                    "faster",
                    "fast",
                    "medium",
                ],
                index=4,
                help="Скорость кодирования (быстрее = больше размер файла)",
            )

            ffmpeg_crf = st.slider(
                "CRF (качество)",
                min_value=18,
                max_value=35,
                value=23,
                step=1,
                help="Качество видео (меньше = лучше качество, больше размер)",
            )

            use_gpu = st.checkbox(
                "Использовать GPU ускорение",
                value=True,
                help="Использовать аппаратное ускорение для кодирования",
            )

    with tab5:
        st.header("🔍 Предпросмотр")

        # Автоматический предпросмотр при изменении параметров
        if validate_inputs(
            background_file, speaker1_file, speaker2_file, speaker1_name, speaker2_name
        ):
            # Создаем предпросмотр автоматически
            create_preview(
                background_file,
                speaker1_file,
                speaker2_file,
                speaker1_name,
                speaker2_name,
                speaker_width,
                speaker_height,
                font_size,
                font_color,
                plate_bg_color,
                plate_border_color,
                plate_border_width,
                plate_padding,
                output_width,
                output_height,
                fps,
                ffmpeg_preset,
                ffmpeg_crf,
                use_gpu,
            )
        else:
            st.warning(
                "⚠️ Загрузите все необходимые файлы и введите имена спикеров для предпросмотра"
            )

    # Кнопка создания видео
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button("🎬 Создать видео", type="primary", use_container_width=True):
            if validate_inputs(
                background_file,
                speaker1_file,
                speaker2_file,
                speaker1_name,
                speaker2_name,
            ):
                create_video(
                    background_file,
                    speaker1_file,
                    speaker2_file,
                    speaker1_name,
                    speaker2_name,
                    speaker_width,
                    speaker_height,
                    font_size,
                    font_color,
                    plate_bg_color,
                    plate_border_color,
                    plate_border_width,
                    plate_padding,
                    output_width,
                    output_height,
                    fps,
                    ffmpeg_preset,
                    ffmpeg_crf,
                    use_gpu,
                )
            else:
                st.error(
                    "❌ Пожалуйста, загрузите все необходимые файлы и введите имена спикеров"
                )


def validate_inputs(
    background_file, speaker1_file, speaker2_file, speaker1_name, speaker2_name
) -> bool:
    """Валидация входных данных."""
    if not background_file:
        return False
    if not speaker1_file:
        return False
    if not speaker2_file:
        return False
    if not speaker1_name.strip():
        return False
    if not speaker2_name.strip():
        return False
    return True


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Конвертация HEX цвета в RGB."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str, alpha: int = 180) -> Tuple[int, int, int, int]:
    """Конвертация HEX цвета в RGBA."""
    rgb = hex_to_rgb(hex_color)
    return rgb[0], rgb[1], rgb[2], alpha


def save_uploaded_file(uploaded_file, temp_dir: str) -> str:
    """Сохранение загруженного файла во временную директорию."""
    file_path = os.path.join(temp_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def create_preview(
    background_file,
    speaker1_file,
    speaker2_file,
    speaker1_name,
    speaker2_name,
    speaker_width,
    speaker_height,
    font_size,
    font_color,
    plate_bg_color,
    plate_border_color,
    plate_border_width,
    plate_padding,
    output_width,
    output_height,
    fps,
    ffmpeg_preset,
    ffmpeg_crf,
    use_gpu,
):
    """Создание предпросмотра первого кадра."""

    # Используем кэширование для ускорения
    @st.cache_data
    def generate_preview_cached(
        bg_file,
        sp1_file,
        sp2_file,
        name1,
        name2,
        width,
        height,
        f_size,
        f_color,
        bg_color,
        border_color,
        border_width,
        padding,
        out_width,
        out_height,
        fps_val,
        preset,
        crf,
        gpu,
    ):
        return _create_preview_internal(
            bg_file,
            sp1_file,
            sp2_file,
            name1,
            name2,
            width,
            height,
            f_size,
            f_color,
            bg_color,
            border_color,
            border_width,
            padding,
            out_width,
            out_height,
            fps_val,
            preset,
            crf,
            gpu,
        )

    # Создаем предпросмотр
    image_data = generate_preview_cached(
        background_file,
        speaker1_file,
        speaker2_file,
        speaker1_name,
        speaker2_name,
        speaker_width,
        speaker_height,
        font_size,
        font_color,
        plate_bg_color,
        plate_border_color,
        plate_border_width,
        plate_padding,
        output_width,
        output_height,
        fps,
        ffmpeg_preset,
        ffmpeg_crf,
        use_gpu,
    )

    if image_data:
        # Показываем предпросмотр
        st.markdown("### 🔍 Предпросмотр композиции")

        st.image(image_data, caption="Предпросмотр композиции", width=800)

        # Кнопка скачивания
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.download_button(
                label="📥 Скачать предпросмотр",
                data=image_data,
                file_name="preview.jpg",
                mime="image/jpeg",
                use_container_width=True,
            )


def _create_preview_internal(
    background_file,
    speaker1_file,
    speaker2_file,
    speaker1_name,
    speaker2_name,
    speaker_width,
    speaker_height,
    font_size,
    font_color,
    plate_bg_color,
    plate_border_color,
    plate_border_width,
    plate_padding,
    output_width,
    output_height,
    fps,
    ffmpeg_preset,
    ffmpeg_crf,
    use_gpu,
):
    """Внутренняя функция создания предпросмотра."""

    try:
        # Создаем временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            # Сохраняем загруженные файлы
            background_path = save_uploaded_file(background_file, temp_dir)
            speaker1_path = save_uploaded_file(speaker1_file, temp_dir)
            speaker2_path = save_uploaded_file(speaker2_file, temp_dir)

            # Создаем конфигурации
            meeting_config = MeetingConfig(
                background_path=background_path,
                speaker1_path=speaker1_path,
                speaker2_path=speaker2_path,
                speaker1_name=speaker1_name,
                speaker2_name=speaker2_name,
                output_path="preview.jpg",
            )

            speaker_config = SpeakerConfig(
                width=speaker_width,
                height=speaker_height,
                position=None,  # Автоматическое центрирование
                font_size=font_size,
                font_color=hex_to_rgb(font_color),
                plate_bg_color=hex_to_rgba(plate_bg_color),
                plate_border_color=hex_to_rgb(plate_border_color),
                plate_border_width=plate_border_width,
                plate_padding=plate_padding,
            )

            export_config = ExportConfig(
                width=output_width,
                height=output_height,
                fps=fps,
                video_codec=VideoCodecConfig(preset=ffmpeg_preset, crf=ffmpeg_crf),
                audio_codec=AudioCodecConfig(),
                gpu_config=GPUConfig(use_gpu=use_gpu),
            )

            # Создаем движок композиции
            composition_engine = CompositionEngine(speaker_config, export_config)

            # Создаем предпросмотр
            preview_path = os.path.join(temp_dir, "preview.jpg")
            success = composition_engine.create_preview(
                background_path,
                speaker1_path,
                speaker2_path,
                speaker1_name,
                speaker2_name,
                preview_path,
            )

            if success:
                # Читаем изображение в память и возвращаем данные
                with open(preview_path, "rb") as f:
                    return f.read()
            else:
                return None

    except Exception as e:
        logger.error(f"Ошибка создания предпросмотра: {e}")
        return None


def create_video(
    background_file,
    speaker1_file,
    speaker2_file,
    speaker1_name,
    speaker2_name,
    speaker_width,
    speaker_height,
    font_size,
    font_color,
    plate_bg_color,
    plate_border_color,
    plate_border_width,
    plate_padding,
    output_width,
    output_height,
    fps,
    ffmpeg_preset,
    ffmpeg_crf,
    use_gpu,
):
    """Создание итогового видео."""

    with st.spinner("🎬 Создание видео... Это может занять несколько минут"):
        try:
            # Создаем временную директорию
            with tempfile.TemporaryDirectory() as temp_dir:
                # Сохраняем загруженные файлы
                background_path = save_uploaded_file(background_file, temp_dir)
                speaker1_path = save_uploaded_file(speaker1_file, temp_dir)
                speaker2_path = save_uploaded_file(speaker2_file, temp_dir)

                # Создаем конфигурации
                meeting_config = MeetingConfig(
                    background_path=background_path,
                    speaker1_path=speaker1_path,
                    speaker2_path=speaker2_path,
                    speaker1_name=speaker1_name,
                    speaker2_name=speaker2_name,
                    output_path=os.path.join(temp_dir, "meeting_output.mp4"),
                )

                speaker_config = SpeakerConfig(
                    width=speaker_width,
                    height=speaker_height,
                    position=None,  # Автоматическое центрирование
                    font_size=font_size,
                    font_color=hex_to_rgb(font_color),
                    plate_bg_color=hex_to_rgba(plate_bg_color),
                    plate_border_color=hex_to_rgb(plate_border_color),
                    plate_border_width=plate_border_width,
                    plate_padding=plate_padding,
                )

                export_config = ExportConfig(
                    width=output_width,
                    height=output_height,
                    fps=fps,
                    video_codec=VideoCodecConfig(preset=ffmpeg_preset, crf=ffmpeg_crf),
                    audio_codec=AudioCodecConfig(),
                    gpu_config=GPUConfig(use_gpu=use_gpu),
                )

                # Создаем сервисы
                composition_engine = CompositionEngine(speaker_config, export_config)
                export_service = ExportService(export_config)

                # Создаем видео
                success = export_service.export_video(
                    meeting_config, composition_engine
                )

                if success:
                    st.success("✅ Видео создано успешно!")

                    # Кнопка скачивания
                    with open(meeting_config.output_path, "rb") as f:
                        st.download_button(
                            label="📥 Скачать видео",
                            data=f.read(),
                            file_name="meeting_output.mp4",
                            mime="video/mp4",
                        )
                else:
                    st.error("❌ Ошибка создания видео")

        except Exception as e:
            st.error(f"❌ Ошибка: {str(e)}")
            logger.error(f"Ошибка создания видео: {e}")


if __name__ == "__main__":
    main()
