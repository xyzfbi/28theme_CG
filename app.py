import streamlit as st
import sys
from pathlib import Path
import tempfile
import os
from typing import Tuple, Optional
import base64
import matplotlib.font_manager as fm

# Добавляем src в путь для импортов, чтобы модули находились корректно.
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Импорты конфигураций и сервисов
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

# Инициализация логгера
logger = setup_logger()


def get_system_fonts():
    """Возвращает список названий установленных в системе шрифтов."""
    fonts = fm.findSystemFonts(fontpaths=None, fontext="ttf")
    font_names = set()
    for font in fonts:
        try:
            font_prop = fm.FontProperties(fname=font)
            font_names.add(font_prop.get_name())
        except Exception:
            continue
    return sorted(font_names)


def get_font_path(font_name: str) -> str:
    """
    Возвращает путь к TTF файлу для выбранного шрифта.
    Если не найден — возвращает стандартный Arial.
    """
    system_fonts = fm.findSystemFonts(fontpaths=None, fontext="ttf")
    font_paths = {fm.FontProperties(fname=f).get_name(): f for f in system_fonts}

    return font_paths.get(font_name, "arial.ttf")


# Вспомогательные функции (оставляем их вне класса, т.к. они утилитарны)
def hex_to_rgb(hex_color: str) -> Tuple[int, ...]:
    """
    Конвертирует HEX цвет (например, '#FFFFFF') в кортеж RGB (255, 255, 255).

    :param hex_color: Строка с HEX кодом цвета, может начинаться с '#'.
    :return: Кортеж из трех целых чисел (R, G, B) от 0 до 255.
    """
    # Удаляем символ '#' и преобразуем пары символов в десятичные числа.
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color: str, alpha: int = 180) -> Tuple[int, int, int, int]:
    """
    Конвертирует HEX цвет в кортеж RGBA, используя заданное значение альфа-канала.
    Альфа-канал используется для настройки прозрачности фона плашки.

    :param hex_color: Строка с HEX кодом цвета.
    :param alpha: Значение альфа-канала от 0 (прозрачный) до 255 (непрозрачный). По умолчанию 180.
    :return: Кортеж из четырех целых чисел (R, G, B, A).
    """
    # Для целей конфигурации оставляем alpha 0-255.
    rgb = hex_to_rgb(hex_color)
    return rgb[0], rgb[1], rgb[2], alpha


def save_uploaded_file(uploaded_file, temp_dir: str) -> str:
    """
    Сохраняет загруженный через Streamlit файл во временную директорию.

    :param uploaded_file: Объект загруженного файла из st.file_uploader.
    :param temp_dir: Путь к временной директории, куда нужно сохранить файл.
    :return: Полный путь к сохраненному файлу.
    """
    file_path = os.path.join(temp_dir, uploaded_file.name)
    with open(file_path, "wb") as f:
        # getbuffer() возвращает содержимое файла в виде байтов.
        f.write(uploaded_file.getbuffer())
    return file_path


def save_get_files(tmp_dir: str) -> Tuple[str, str, str]:
    """
    Извлекает загруженные файлы из состояния сессии Streamlit, сохраняет их
    во временную директорию и возвращает пути к ним.

    Предполагается, что файлы уже проверены на наличие функцией _validate_inputs.

    :param tmp_dir: Путь к временной директории для сохранения.
    :return: Кортеж из трех путей: (фон, видео спикера 1, видео спикера 2).
    """
    background_file = st.session_state.get("background_file")
    speaker1_file = st.session_state.get("speaker1_file")
    speaker2_file = st.session_state.get("speaker2_file")

    # Сохраняем загруженные файлы
    background_path = save_uploaded_file(background_file, tmp_dir)
    speaker1_path = save_uploaded_file(speaker1_file, tmp_dir)
    speaker2_path = save_uploaded_file(speaker2_file, tmp_dir)

    return background_path, speaker1_path, speaker2_path


def _validate_inputs() -> bool:
    """
    Выполняет валидацию обязательных входных данных в состоянии сессии.

    Проверяет, что загружены все три файла (фон, видео 1, видео 2) и
    введены имена обоих спикеров (не пустые строки).

    :return: True, если все необходимые данные присутствуют, иначе False.
    """
    return all(
        [
            st.session_state.get("background_file"),
            st.session_state.get("speaker1_file"),
            st.session_state.get("speaker2_file"),
            st.session_state.speaker1_name.strip(),  # Проверка на непустое имя
            st.session_state.speaker2_name.strip(),  # Проверка на непустое имя
        ]
    )


class VideoMeetingComposerApp:
    """
    Класс Streamlit приложения для композиции видеоконференций.
    Управляет пользовательским интерфейсом, настройками и логикой вызова
    сервисов композиции и экспорта видео.
    """

    def __init__(self):
        """
        Инициализация приложения: настройка страницы и состояния сессии.
        """
        st.set_page_config(
            page_title="Video Meeting Composer",
            page_icon="🎥",
            layout="wide",
            initial_sidebar_state="expanded",
        )
        self._init_session_state()

    @staticmethod
    def _init_session_state():
        default_state = {
            "speaker1_name": "Спикер 1",
            "speaker2_name": "Спикер 2",
            "speaker_width": 400,
            "speaker_height": 300,
            "manual_font_size": 24,
            "font_color": "#FFFFFF",
            "plate_bg_color": "#000000",
            "plate_border_color": "#FFFFFF",
            "plate_border_width": 2,
            "plate_padding": 30,
            "output_width": 1920,
            "output_height": 1080,
            "fps": 30,
            "ffmpeg_preset": "fast",
            "ffmpeg_crf": 23,
            "use_gpu": True,
            "font_family": "Arial",
        }
        for key, value in default_state.items():
            if key not in st.session_state:
                st.session_state[key] = value

    def _get_config_objects(self) -> Tuple[SpeakerConfig, ExportConfig]:
        output_height = st.session_state.output_height
        speaker_height = st.session_state.speaker_height
        FONT_SIZE_MIN = max(12, int(speaker_height * 0.04))
        FONT_SIZE_MAX = max(FONT_SIZE_MIN + 1, int(speaker_height * 0.15))
        user_font_size = st.session_state.manual_font_size
        dynamic_font_size = max(FONT_SIZE_MIN, min(FONT_SIZE_MAX, user_font_size))
        user_font_name = st.session_state.font_family
        # user_font_path = get_font_path(user_font_name)
        PADDING_MIN = max(2, int(output_height * 0.01))
        PYDANTIC_PADDING_LIMIT = 50
        user_plate_padding = st.session_state.plate_padding
        dynamic_plate_padding = max(
            PADDING_MIN, min(PYDANTIC_PADDING_LIMIT, user_plate_padding)
        )
        speaker_config = SpeakerConfig(
            width=st.session_state.speaker_width,
            height=st.session_state.speaker_height,
            position=None,
            font_size=dynamic_font_size,
            font_color=hex_to_rgb(st.session_state.font_color),
            plate_bg_color=hex_to_rgba(st.session_state.plate_bg_color),
            plate_border_color=hex_to_rgb(st.session_state.plate_border_color),
            plate_border_width=st.session_state.plate_border_width,
            plate_padding=dynamic_plate_padding,
            font_family=user_font_name,
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
        return speaker_config, export_config

    # --- Секции Рендеринга ---

    @staticmethod
    def _render_upload_tab():
        """Отображает вкладку для загрузки файлов (фон и видео спикеров) и ввода имен."""
        st.subheader("📁 Загрузка файлов")

        st.file_uploader(
            "Выберите фоновое изображение",
            type=["jpg", "jpeg", "png", "bmp"],
            key="background_file",
            help="JPG, PNG, BMP",
        )
        st.file_uploader(
            "Выберите видео первого спикера",
            type=["mp4", "avi", "mov", "mkv"],
            key="speaker1_file",
            help="MP4, AVI, MOV, MKV",
        )
        st.text_input("Имя первого спикера", key="speaker1_name")
        st.file_uploader(
            "Выберите видео второго спикера",
            type=["mp4", "avi", "mov", "mkv"],
            key="speaker2_file",
            help="MP4, AVI, MOV, MKV",
        )
        st.text_input("Имя второго спикера", key="speaker2_name")

    @staticmethod
    def _render_speaker_settings():
        """
        Отображает настройки размеров окон спикеров.
        Границы ползунков динамически рассчитываются на основе разрешения экспорта.
        """
        st.subheader("📏 Размеры окон спикеров")

        output_width = st.session_state.output_width
        output_height = st.session_state.output_height

        # Динамические границы для ширины (от 10% до ~47% кадра)
        WIDTH_MIN = max(150, int(output_width * 0.1))
        WIDTH_MAX = int(output_width * 0.46875)

        # Динамические границы для высоты (от 10% до 60% кадра)
        HEIGHT_MIN = max(100, int(output_height * 0.1))
        HEIGHT_MAX = int(output_height * 0.6)

        st.info(f"""
            Границы размеров окон динамически масштабируются относительно разрешения экспорта ({output_width}x{output_height}):
            - **Ширина:** от **{WIDTH_MIN}** до **{WIDTH_MAX}**px.
            - **Высота:** от **{HEIGHT_MIN}** до **{HEIGHT_MAX}**px.
        """)

        st.slider(
            "Ширина окна",
            min_value=WIDTH_MIN,
            max_value=WIDTH_MAX,
            step=1,
            key="speaker_width",
            help="Ширина окна для каждого спикера в пикселях. Границы зависят от общей ширины видео.",
        )
        st.slider(
            "Высота окна",
            min_value=HEIGHT_MIN,
            max_value=HEIGHT_MAX,
            step=1,
            key="speaker_height",
            help="Высота окна для каждого спикера в пикселях. Границы зависят от общей высоты видео.",
        )

    @staticmethod
    def _render_plate_settings():
        """
        Отображает настройки плашек (текст, фон, рамка, отступы).
        Размер шрифта и отступы (padding) имеют динамические ограничения.
        """
        st.subheader("🔤 Текст")

        output_height = st.session_state.output_height
        speaker_height = st.session_state.speaker_height

        # Динамические границы размера шрифта (от 4% до 15% высоты окна спикера)
        FONT_SIZE_MIN = max(12, int(speaker_height * 0.04))
        FONT_SIZE_MAX = max(FONT_SIZE_MIN + 1, int(speaker_height * 0.15))

        # Ползунок для размера шрифта
        st.slider(
            "Размер шрифта",
            min_value=FONT_SIZE_MIN,
            max_value=FONT_SIZE_MAX,
            step=1,
            key="manual_font_size",
            help=f"Размер шрифта на плашках. Диапазон: {FONT_SIZE_MIN}-{FONT_SIZE_MAX}px",
        )

        st.info(
            f"""
            **Текущий размер шрифта:** {st.session_state.manual_font_size}px.
            **Динамические границы:** от **{FONT_SIZE_MIN}** до **{FONT_SIZE_MAX}**px, зависят от **высоты окна спикера** ({speaker_height}px).
            """
        )

        system_fonts = get_system_fonts()

        st.selectbox(
            "Шрифт текста",
            options=system_fonts,
            key="font_family",
            help="Выберите шрифт из установленных в системе",
        )

        st.color_picker("Цвет текста", key="font_color", help="Цвет текста на плашках")

        st.subheader("🎨 Фон плашки")
        st.color_picker("Цвет фона", key="plate_bg_color", help="Цвет фона плашки")
        st.color_picker(
            "Цвет рамки", key="plate_border_color", help="Цвет рамки вокруг плашки"
        )
        st.slider(
            "Толщина рамки",
            min_value=0,
            max_value=10,
            step=1,
            key="plate_border_width",
            help="Толщина рамки в пикселях",
        )

        # ---------------------------------------------------------------------
        # ЖЕСТКИЙ ЛИМИТ ДЛЯ PADDING (PYDANTIC)
        PYDANTIC_PADDING_LIMIT = 50
        PADDING_MIN = max(2, int(output_height * 0.01))

        # Максимальное значение, доступное в UI, ограничено 50px (для Pydantic)
        SLIDER_PADDING_MAX = min(
            PYDANTIC_PADDING_LIMIT, max(PADDING_MIN + 1, int(output_height * 0.08))
        )

        # Новый ползунок для padding
        st.slider(
            "Отступы в плашке (padding)",
            min_value=PADDING_MIN,
            max_value=SLIDER_PADDING_MAX,
            step=1,
            key="plate_padding",
            help=f"Внутренние отступы в плашке. Диапазон: {PADDING_MIN}-{SLIDER_PADDING_MAX}px. Максимум ограничен {PYDANTIC_PADDING_LIMIT}px для совместимости с моделью.",
        )

        st.info(
            f"""
            **Текущий padding:** {st.session_state.plate_padding}px.
            **Динамические границы:** от **{PADDING_MIN}** до **{SLIDER_PADDING_MAX}**px. Максимальный отступ ограничен **{PYDANTIC_PADDING_LIMIT}px**, чтобы избежать ошибок валидации.
            """
        )
        # -------------------------------------------------------------

    @staticmethod
    def _render_export_settings():
        """Отображает настройки разрешения видео и параметров FFmpeg."""
        st.subheader("📐 Разрешение видео")
        st.selectbox(
            "Ширина",
            options=[1280, 1920, 2560, 3840],
            key="output_width",
            help="Ширина итогового видео в пикселях",
        )
        st.selectbox(
            "Высота",
            options=[720, 1080, 1440, 2160],
            key="output_height",
            help="Высота итогового видео в пикселях",
        )
        st.slider(
            "FPS",
            min_value=24,
            max_value=120,
            step=6,
            key="fps",
            help="Частота кадров выходного видео",
        )

        st.subheader("⚡ Оптимизация")
        st.selectbox(
            "Пресет FFmpeg",
            options=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium"],
            key="ffmpeg_preset",
            help="Скорость кодирования (быстрее = больше размер файла)",
        )
        st.slider(
            "CRF (качество)",
            min_value=18,
            max_value=35,
            step=1,
            key="ffmpeg_crf",
            help="Качество видео (меньше = лучше качество, больше размер)",
        )

    def _render_settings_section(self):
        """Рендерит секцию настроек с вкладками."""
        st.header("⚙️ Настройки")
        tab_upload, tab1, tab2, tab3 = st.tabs(
            ["⬆️ Загрузка файлов", "🎤 Спикеры", "🎨 Плашки", "📤 Экспорт"]
        )
        with tab_upload:
            self._render_upload_tab()
        with tab1:
            self._render_speaker_settings()
        with tab2:
            self._render_plate_settings()
        with tab3:
            self._render_export_settings()

    def _render_preview_section(self):
        """Рендерит секцию предпросмотра, включая вызов кэшированной функции для генерации."""
        st.header("🔍 Предпросмотр")
        st.markdown("---")

        preview_placeholder = st.empty()

        if _validate_inputs():
            with st.spinner("🔄 Генерация предпросмотра..."):
                # Передаем хеш состояния, чтобы Streamlit знал, когда нужно пересчитать кэш
                state_hash = self._get_state_hash_for_caching()
                preview_image = self._create_preview_cached(state_hash)

                if preview_image:
                    preview_placeholder.image(
                        preview_image,
                        caption="Предпросмотр композиции",
                        width="stretch",
                    )
                    st.download_button(
                        label="📥 Скачать предпросмотр",
                        data=preview_image,
                        file_name="preview.jpg",
                        mime="image/jpeg",
                        width="stretch",
                    )
                else:
                    st.error("❌ Ошибка создания предпросмотра")
        else:
            # Если входные данные не полны, показываем заглушку
            self._create_placeholder_preview()

    @staticmethod
    def _create_placeholder_preview():
        """
        Отображает информационное сообщение и стилизованную заглушку
        на месте предпросмотра, если файлы еще не загружены.
        Использует base64 кодирование для встраивания изображения заглушки.
        """
        st.info("📋 Загрузите все файлы для отображения предпросмотра")
        # Использование заглушки из файла (предполагается, что plug.png существует)
        try:
            # Динамическое определение пути к заглушке
            base_dir = Path(__file__).parent
            plug_path = base_dir / "public" / "plug.png"

            # Проверка наличия файла
            if not plug_path.exists():
                st.warning(
                    f"Файл '{plug_path}' не найден. Невозможно отобразить заглушку."
                )
                return

            with open(plug_path, "rb") as image_file:
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
        except Exception as e:
            # Логирование ошибки при чтении или встраивании заглушки
            st.warning(f"Ошибка при отображении заглушки: {e}")

    @st.cache_data
    def _create_preview_cached(_self, state_hash: int) -> Optional[bytes]:
        """
        Создает предпросмотр композиции в виде изображения (JPEG).
        Функция кэшируется Streamlit: она выполнится только при изменении state_hash.

        :param _self: Ссылка на экземпляр класса (требуется для доступа к методам _self).
        :param state_hash: Хеш, представляющий все настройки, влияющие на предпросмотр.
        :return: Байтовое представление изображения JPEG, или None в случае ошибки.
        """
        # Получаем конфигурацию из сессии, используя _self
        speaker_config, export_config = _self._get_config_objects()

        try:
            # Используем временную директорию для сохранения файлов и предпросмотра
            with tempfile.TemporaryDirectory() as temp_dir:
                # Сохраняем загруженные файлы в temp_dir
                background_path, speaker1_path, speaker2_path = save_get_files(temp_dir)

                composition_engine = CompositionEngine(speaker_config, export_config)

                preview_path = os.path.join(temp_dir, "preview.jpg")
                # Вызываем движок композиции для создания превью
                success = composition_engine.create_preview(
                    background_path,
                    speaker1_path,
                    speaker2_path,
                    st.session_state.speaker1_name,
                    st.session_state.speaker2_name,
                    preview_path,
                )

                if success:
                    # Читаем байты созданного превью
                    with open(preview_path, "rb") as f:
                        return f.read()
                else:
                    return None

        except Exception as e:
            logger.error(f"Ошибка создания предпросмотра: {e}")
            return None

    @staticmethod
    def _get_state_hash_for_caching() -> int:
        """
        Генерирует хеш для всех параметров, влияющих на предпросмотр.
        Этот хеш используется декоратором @st.cache_data для определения,
        нужно ли пересчитывать кэш.

        :return: Целочисленный хеш.
        """
        background_file = st.session_state.get("background_file")
        speaker1_file = st.session_state.get("speaker1_file")
        speaker2_file = st.session_state.get("speaker2_file")

        hash_data = (
            # Файлы: используем file_id для уникальности (если файл перезагружается),
            # иначе None.
            background_file.file_id if background_file else None,
            speaker1_file.file_id if speaker1_file else None,
            speaker2_file.file_id if speaker2_file else None,
            # Настройки, влияющие на внешний вид
            st.session_state.speaker1_name,
            st.session_state.speaker2_name,
            st.session_state.speaker_width,
            st.session_state.speaker_height,
            st.session_state.manual_font_size,
            st.session_state.font_color,
            st.session_state.plate_bg_color,
            st.session_state.plate_border_color,
            st.session_state.plate_border_width,
            st.session_state.plate_padding,
            st.session_state.output_width,
            st.session_state.output_height,
            st.session_state.font_family,
        )
        return hash(hash_data)

    def _render_export_section(self):
        """Рендерит кнопку запуска экспорта видео."""
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🎬 Создать видео", type="primary", width="stretch"):
                if _validate_inputs():
                    self._create_video()
                else:
                    st.error(
                        "❌ Пожалуйста, загрузите все необходимые файлы и введите имена спикеров"
                    )

    def _create_video(self):
        """
        Основная логика создания и экспорта итогового видеофайла.
        Использует временную директорию для работы с файлами.
        """
        with st.spinner("🎬 Создание видео... Это может занять несколько минут"):
            try:
                # 1. Используем временную директорию
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Сохраняем загруженные файлы из Streamlit
                    background_path, speaker1_path, speaker2_path = save_get_files(
                        temp_dir
                    )

                    # 2. Создание конфигураций
                    speaker_config, export_config = self._get_config_objects()

                    output_file_path = os.path.join(temp_dir, "meeting_output.mp4")
                    meeting_config = MeetingConfig(
                        background_path=background_path,
                        speaker1_path=speaker1_path,
                        speaker2_path=speaker2_path,
                        speaker1_name=st.session_state.speaker1_name,
                        speaker2_name=st.session_state.speaker2_name,
                        output_path=output_file_path,
                    )

                    # 3. Создание и запуск сервисов
                    composition_engine = CompositionEngine(
                        speaker_config, export_config
                    )
                    export_service = ExportService(export_config)

                    # 4. Запуск процесса экспорта
                    success = export_service.export_video(
                        meeting_config, composition_engine
                    )

                    if success:
                        st.success("✅ Видео создано успешно!")
                        # Предлагаем пользователю скачать созданный файл
                        with open(meeting_config.output_path, "rb") as f:
                            st.download_button(
                                label="📥 Скачать видео",
                                data=f.read(),
                                file_name="meeting_output.mp4",
                                mime="video/mp4",
                                width="stretch",
                            )
                    else:
                        st.error("❌ Ошибка создания видео")

            except Exception as e:
                # Обработка и логирование любых исключений в процессе создания видео
                st.error(f"❌ Ошибка: {str(e)}")
                logger.error(f"Ошибка создания видео: {e}")

    def run(self):
        """
        Главный метод для запуска и отображения интерфейса приложения.
        Разделяет экран на секции предпросмотра и настроек.
        """
        # Создаем две колонки: 2/3 для предпросмотра, 1/3 для настроек
        col_preview, col_settings = st.columns([2, 1])

        with col_preview:
            self._render_preview_section()

        with col_settings:
            self._render_settings_section()

        # Кнопка экспорта выводится на всю ширину под колонками
        self._render_export_section()


# --- Точка Входа ---
if __name__ == "__main__":
    app = VideoMeetingComposerApp()
    app.run()
