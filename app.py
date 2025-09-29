"""
🌐 Streamlit веб-приложение для создания видеовстреч
Интерактивный интерфейс с живым предпросмотром и настройками справа
"""

import streamlit as st
import sys
from pathlib import Path
import tempfile
import os
from typing import Tuple
import base64

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
    GPUConfig
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

    init_session_state()

    col_preview, col_settings = st.columns([2, 1])

    with col_preview:
        render_preview_section()

    with col_settings:
        render_settings_section()  # tabs теперь включают "Загрузка файлов"

    render_export_section()


def init_session_state():
    """Инициализация состояния сессии с параметрами по умолчанию."""

    # Файлы
    if "background_file" not in st.session_state:
        st.session_state.background_file = None
    if "speaker1_file" not in st.session_state:
        st.session_state.speaker1_file = None
    if "speaker2_file" not in st.session_state:
        st.session_state.speaker2_file = None
    if "speaker1_name" not in st.session_state:
        st.session_state.speaker1_name = "Спикер 1"
    if "speaker2_name" not in st.session_state:
        st.session_state.speaker2_name = "Спикер 2"

    # Настройки спикеров
    if "speaker_width" not in st.session_state:
        st.session_state.speaker_width = 400
    if "speaker_height" not in st.session_state:
        st.session_state.speaker_height = 300

    # Настройки плашек
    if "font_size" not in st.session_state:
        st.session_state.font_size = 24
    if "font_color" not in st.session_state:
        st.session_state.font_color = "#FFFFFF"
    if "plate_bg_color" not in st.session_state:
        st.session_state.plate_bg_color = "#000000"
    if "plate_border_color" not in st.session_state:
        st.session_state.plate_border_color = "#FFFFFF"
    if "plate_border_width" not in st.session_state:
        st.session_state.plate_border_width = 2
    if "plate_padding" not in st.session_state:
        st.session_state.plate_padding = 10

    # Настройки экспорта
    if "output_width" not in st.session_state:
        st.session_state.output_width = 1920
    if "output_height" not in st.session_state:
        st.session_state.output_height = 1080
    if "fps" not in st.session_state:
        st.session_state.fps = 30
    if "ffmpeg_preset" not in st.session_state:
        st.session_state.ffmpeg_preset = "fast"
    if "ffmpeg_crf" not in st.session_state:
        st.session_state.ffmpeg_crf = 23
    if "use_gpu" not in st.session_state:
        st.session_state.use_gpu = True


def render_preview_section():
    """Отображение секции предпросмотра."""
    st.header("🔍 Предпросмотр")
    st.markdown("---")

    preview_placeholder = st.empty()
    # Показываем предпросмотр
    if validate_inputs(
        st.session_state.background_file,
        st.session_state.speaker1_file,
        st.session_state.speaker2_file,
        st.session_state.speaker1_name,
        st.session_state.speaker2_name,
    ):
        # Создаем и показываем предпросмотр
        with st.spinner("🔄 Генерация предпросмотра..."):
            # Передаем все параметры для корректного кэширования
            preview_image = create_preview(
                st.session_state.speaker1_name,
                st.session_state.speaker2_name,
                st.session_state.speaker_width,
                st.session_state.speaker_height,
                st.session_state.font_size,
                st.session_state.font_color,
                st.session_state.plate_bg_color,
                st.session_state.plate_border_color,
                st.session_state.plate_border_width,
                st.session_state.plate_padding,
                st.session_state.output_width,
                st.session_state.output_height,
            )

            if preview_image:
                preview_placeholder.image(
                    preview_image,
                    caption="Предпросмотр композиции",
                    use_container_width=True,
                )

                # Кнопка скачивания предпросмотра
                st.download_button(
                    label="📥 Скачать предпросмотр",
                    data=preview_image,
                    file_name="preview.jpg",
                    mime="image/jpeg",
                    use_container_width=True,
                )
            else:
                st.error("❌ Ошибка создания предпросмотра")
    else:
        # Показываем заглушку
        st.info("📋 Загрузите все файлы для отображения предпросмотра")
        create_placeholder_preview()


def render_settings_section():
    """Отображение секции настроек."""

    st.header("⚙️ Настройки")

    # Создаем вкладки для настроек
    tab_upload, tab1, tab2, tab3 = st.tabs(
        ["⬆️ Загрузка файлов", "🎤 Спикеры", "🎨 Плашки", "📤 Экспорт"]
    )
    with tab_upload:
        render_upload_tab()
    with tab1:
        render_speaker_settings()
    with tab2:
        render_plate_settings()
    with tab3:
        render_export_settings()


def render_upload_tab():
    st.subheader("📁 Загрузка файлов")
    background_file = st.file_uploader(
        "Выберите фоновое изображение",
        type=["jpg", "jpeg", "png", "bmp"],
        help="Поддерживаемые форматы: JPG, PNG, BMP",
        key="background_uploader",
    )
    speaker1_file = st.file_uploader(
        "Выберите видео первого спикера",
        type=["mp4", "avi", "mov", "mkv"],
        key="speaker1_uploader",
        help="Поддерживаемые форматы: MP4, AVI, MOV, MKV",
    )
    speaker1_name = st.text_input(
        "Имя первого спикера", value=st.session_state.speaker1_name, key="name1_input"
    )
    speaker2_file = st.file_uploader(
        "Выберите видео второго спикера",
        type=["mp4", "avi", "mov", "mkv"],
        key="speaker2_uploader",
        help="Поддерживаемые форматы: MP4, AVI, MOV, MKV",
    )
    speaker2_name = st.text_input(
        "Имя второго спикера", value=st.session_state.speaker2_name, key="name2_input"
    )
    # session_state updates and rerun logic
    changed = False
    for name, val in [
        ("background_file", background_file),
        ("speaker1_file", speaker1_file),
        ("speaker2_file", speaker2_file),
        ("speaker1_name", speaker1_name),
        ("speaker2_name", speaker2_name),
    ]:
        if getattr(st.session_state, name) != val:
            setattr(st.session_state, name, val)
            changed = True
    if changed:
        st.rerun()


def render_speaker_settings():
    """Настройки спикеров."""

    st.subheader("📏 Размеры окон спикеров")

    speaker_width = st.slider(
        "Ширина окна",
        min_value=200,
        max_value=800,
        value=st.session_state.speaker_width,
        step=50,
        help="Ширина окна для каждого спикера в пикселях",
        key="speaker_width_slider",
    )

    speaker_height = st.slider(
        "Высота окна",
        min_value=150,
        max_value=600,
        value=st.session_state.speaker_height,
        step=50,
        help="Высота окна для каждого спикера в пикселях",
        key="speaker_height_slider",
    )

    # Обновляем session_state и перерисовываем при изменении
    if (
        speaker_width != st.session_state.speaker_width
        or speaker_height != st.session_state.speaker_height
    ):
        st.session_state.speaker_width = speaker_width
        st.session_state.speaker_height = speaker_height
        st.rerun()


def render_plate_settings():
    """Настройки плашек."""

    st.subheader("🔤 Текст")

    font_size = st.slider(
        "Размер шрифта",
        min_value=12,
        max_value=48,
        value=st.session_state.font_size,
        step=2,
        help="Размер шрифта для текста на плашках",
        key="font_size_slider",
    )

    font_color = st.color_picker(
        "Цвет текста",
        value=st.session_state.font_color,
        help="Цвет текста на плашках",
        key="font_color_picker",
    )

    st.subheader("🎨 Фон плашки")

    plate_bg_color = st.color_picker(
        "Цвет фона",
        value=st.session_state.plate_bg_color,
        help="Цвет фона плашки",
        key="plate_bg_color_picker",
    )

    plate_border_color = st.color_picker(
        "Цвет рамки",
        value=st.session_state.plate_border_color,
        help="Цвет рамки вокруг плашки",
        key="plate_border_color_picker",
    )

    plate_border_width = st.slider(
        "Толщина рамки",
        min_value=0,
        max_value=10,
        value=st.session_state.plate_border_width,
        step=1,
        help="Толщина рамки в пикселях",
        key="plate_border_width_slider",
    )

    plate_padding = st.slider(
        "Отступы в плашке",
        min_value=5,
        max_value=30,
        value=st.session_state.plate_padding,
        step=5,
        help="Внутренние отступы в плашке",
        key="plate_padding_slider",
    )

    # Обновляем session_state и перерисовываем при изменении
    changed = False
    if font_size != st.session_state.font_size:
        st.session_state.font_size = font_size
        changed = True
    if font_color != st.session_state.font_color:
        st.session_state.font_color = font_color
        changed = True
    if plate_bg_color != st.session_state.plate_bg_color:
        st.session_state.plate_bg_color = plate_bg_color
        changed = True
    if plate_border_color != st.session_state.plate_border_color:
        st.session_state.plate_border_color = plate_border_color
        changed = True
    if plate_border_width != st.session_state.plate_border_width:
        st.session_state.plate_border_width = plate_border_width
        changed = True
    if plate_padding != st.session_state.plate_padding:
        st.session_state.plate_padding = plate_padding
        changed = True

    if changed:
        st.rerun()


def render_export_settings():
    """Настройки экспорта."""

    st.subheader("📐 Разрешение видео")

    output_width = st.selectbox(
        "Ширина",
        options=[1280, 1920, 2560, 3840],
        index=[1280, 1920, 2560, 3840].index(st.session_state.output_width),
        help="Ширина итогового видео в пикселях",
        key="output_width_select",
    )

    output_height = st.selectbox(
        "Высота",
        options=[720, 1080, 1440, 2160],
        index=[720, 1080, 1440, 2160].index(st.session_state.output_height),
        help="Высота итогового видео в пикселях",
        key="output_height_select",
    )

    fps = st.slider(
        "FPS",
        min_value=24,
        max_value=120,
        value=st.session_state.fps,
        step=6,
        help="Частота кадров выходного видео",
        key="fps_slider",
    )

    st.subheader("⚡ Оптимизация")

    ffmpeg_preset = st.selectbox(
        "Пресет FFmpeg",
        options=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium"],
        index=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium"].index(
            st.session_state.ffmpeg_preset
        ),
        help="Скорость кодирования (быстрее = больше размер файла)",
        key="ffmpeg_preset_select",
    )

    ffmpeg_crf = st.slider(
        "CRF (качество)",
        min_value=18,
        max_value=35,
        value=st.session_state.ffmpeg_crf,
        step=1,
        help="Качество видео (меньше = лучше качество, больше размер)",
        key="ffmpeg_crf_slider",
    )


    # Обновляем session_state и перерисовываем при изменении разрешения
    resolution_changed = False
    if output_width != st.session_state.output_width:
        st.session_state.output_width = output_width
        resolution_changed = True
    if output_height != st.session_state.output_height:
        st.session_state.output_height = output_height
        resolution_changed = True

    # Остальные параметры не влияют на предпросмотр
    st.session_state.fps = fps
    st.session_state.ffmpeg_preset = ffmpeg_preset
    st.session_state.ffmpeg_crf = ffmpeg_crf

    if resolution_changed:
        st.rerun()


def render_export_section():
    """Секция экспорта видео."""

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button("🎬 Создать видео", type="primary", use_container_width=True):
            if validate_inputs(
                st.session_state.background_file,
                st.session_state.speaker1_file,
                st.session_state.speaker2_file,
                st.session_state.speaker1_name,
                st.session_state.speaker2_name,
            ):
                create_video()
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


def hex_to_rgb(hex_color: str) -> Tuple[int, ...]:
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


def create_placeholder_preview():
    with open("public/plug.png", "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 450px; background: rgba(0,0,0,0);">
            <img src="data:image/png;base64,{encoded}" alt="Preview" style="height: 120px;" />
            <div style="margin-top: 16px; color: #888; font-size: 1.1rem;">Предпросмотр будет здесь</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def create_preview(
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
):
    """Создание предпросмотра с кэшированием по всем параметрам."""
    try:
        # Создаем временную директорию
        with tempfile.TemporaryDirectory() as temp_dir:
            # Сохраняем загруженные файлы
            background_path = save_uploaded_file(
                st.session_state.background_file, temp_dir
            )
            speaker1_path = save_uploaded_file(st.session_state.speaker1_file, temp_dir)
            speaker2_path = save_uploaded_file(st.session_state.speaker2_file, temp_dir)

            # Создаем конфигурации
            MeetingConfig(
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
                fps=30,  # Для предпросмотра FPS не важен
                video_codec=VideoCodecConfig(),
                audio_codec=AudioCodecConfig(),
                gpu_config=GPUConfig(use_gpu=False),  # Для предпросмотра GPU не нужен
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


def get_file_hash(uploaded_file):
    """Получение хеша файла для кэширования."""
    if uploaded_file is None:
        return None
    return hash(uploaded_file.getvalue())


def create_video():
    """Создание итогового видео."""

    with st.spinner("🎬 Создание видео... Это может занять несколько минут"):
        try:
            # Создаем временную директорию
            with tempfile.TemporaryDirectory() as temp_dir:
                # Сохраняем загруженные файлы
                background_path = save_uploaded_file(
                    st.session_state.background_file, temp_dir
                )
                speaker1_path = save_uploaded_file(
                    st.session_state.speaker1_file, temp_dir
                )
                speaker2_path = save_uploaded_file(
                    st.session_state.speaker2_file, temp_dir
                )

                # Создаем конфигурации
                meeting_config = MeetingConfig(
                    background_path=background_path,
                    speaker1_path=speaker1_path,
                    speaker2_path=speaker2_path,
                    speaker1_name=st.session_state.speaker1_name,
                    speaker2_name=st.session_state.speaker2_name,
                    output_path=os.path.join(temp_dir, "meeting_output.mp4"),
                )

                speaker_config = SpeakerConfig(
                    width=st.session_state.speaker_width,
                    height=st.session_state.speaker_height,
                    position=None,  # Автоматическое центрирование
                    font_size=st.session_state.font_size,
                    font_color=hex_to_rgb(st.session_state.font_color),
                    plate_bg_color=hex_to_rgba(st.session_state.plate_bg_color),
                    plate_border_color=hex_to_rgb(st.session_state.plate_border_color),
                    plate_border_width=st.session_state.plate_border_width,
                    plate_padding=st.session_state.plate_padding,
                )

                export_config = ExportConfig(
                    width=st.session_state.output_width,
                    height=st.session_state.output_height,
                    fps=st.session_state.fps,
                    video_codec=VideoCodecConfig(
                        preset=st.session_state.ffmpeg_preset,
                        crf=st.session_state.ffmpeg_crf,
                    ),
                    audio_codec=AudioCodecConfig(),
                    gpu_config=GPUConfig(use_gpu=st.session_state.use_gpu),
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
