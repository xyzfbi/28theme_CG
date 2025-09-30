# Video Meeting Composer

Интерактивное приложение на Streamlit для композиции видеовстреч: объединяет фоновое изображение и два видео со спикерами, добавляет плашки с именами, смешивает аудио и экспортирует финальный ролик с использованием FFmpeg (с автоопределением GPU-ускорения).

## Возможности

- Сборка сцены: фон + 2 окна спикеров
- Автоматическое расположение окон по половинам кадра, центрирование по вертикали
- Плашки с именами: цвет текста, фон RGBA, рамка, отступы, размер шрифта
- Предпросмотр первого кадра (JPEG) прямо в UI с возможностью скачивания
- Экспорт MP4, смешивание аудио дорожек спикеров, faststart для web
- Автоопределение кодека GPU (NVENC/QSV/VAAPI) или CPU (libx264)

## Требования

- Python 3.8+
- FFmpeg установлен и доступен в PATH
- Системные шрифты (на Linux используется DejaVuSans-Bold)

## Установка:
### 1.Docker

Сборка образа:
```bash
docker build -t video-meeting-composer:latest .
```

Запуск (CPU):
```bash
docker run --rm -p 8501:8501 \
  -v "$PWD/media":/media \
  --name video-composer video-meeting-composer:latest
```
Перейдите: `http://localhost:8501`.

Примечание: базовый FFmpeg в образе рассчитан на CPU. Для NVENC/QSV/VAAPI используйте базовый образ с соответствующей сборкой FFmpeg или соберите FFmpeg самостоятельно.

### 2. Клон репозитория и средства Python:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Linux (пример): sudo apt-get update && sudo apt-get install -y ffmpeg fonts-dejavu-core
```

## Запуск (Streamlit)

```bash
streamlit run app.py
```
Откройте браузер: `http://localhost:8501`

### Что доступно в интерфейсе
- 📁 Загрузка фонового изображения и двух видео спикеров
- 🎤 Настройка размеров окон спикеров (границы зависят от разрешения экспорта)
- 🎨 Настройка плашек (цвета, рамка, отступы, размер шрифта с динамическими лимитами)
- 📐 Настройка экспорта (разрешение, FPS, пресет и CRF FFmpeg, GPU)
- 🔍 Предпросмотр первого кадра и 📥 скачивание
- 🎬 Кнопка «Создать видео» с последующим скачиванием MP4

## Использование из кода (скрипт)

В проекте есть готовые сервисы и модели. Можно собрать видео программно (например, в отдельном скрипте), используя `ExportService` и `CompositionEngine`. Также доступен `ConfigManager` для парсинга аргументов, если вы решите сделать свой CLI-обертку.

Пример общей последовательности:
1) создать `MeetingConfig`, `SpeakerConfig`, `ExportConfig`
2) создать `CompositionEngine` и `ExportService`
3) вызвать `export_service.export_video(meeting_config, composition_engine)`

Для быстрого JPEG предпросмотра используйте `CompositionEngine.create_preview(...)`.

## Структура проекта

```
.
├── app.py
├── public/
│   └── plug.png
├── README.md
├── requirements.txt
└── src/
    ├── config/
    │   ├── config_manager.py
    │   └── __init__.py
    ├── models/
    │   ├── base.py
    │   ├── export_config.py
    │   ├── meeting_config.py
    │   ├── speaker_config.py
    │   └── __init__.py
    ├── services/
    │   ├── audio_processor.py
    │   ├── composition_engine.py
    │   ├── export_service.py
    │   ├── image_processor.py
    │   ├── video_processor.py
    │   └── __init__.py
    └── utils/
        ├── logger.py
        └── __init__.py
```

## Примечания по кодекам и GPU

- Пресет и CRF настраиваются в UI; для CPU используется `libx264`.
- При включенном GPU движок пытается найти `h264_nvenc` (NVIDIA), `h264_qsv` (Intel), `h264_vaapi` (VAAPI). Если не найдено — падает обратно на CPU.

## Советы и устранение неполадок

- FFmpeg не найден: установите FFmpeg и убедитесь, что он в PATH (`ffmpeg -version`).
- Нет шрифта для плашек: на Linux поставьте `fonts-dejavu-core` (используется `DejaVuSans-Bold`), на Windows/макОS шрифт берется из системы или применяется дефолтный.
- Ошибки OpenCV при показе изображений: проверьте корректность путей к файлам и поддержку кодеков вашей сборкой OpenCV/FFmpeg.
- GPU кодек не определяется: драйвер/библиотеки могут быть не установлены или не поддерживаться FFmpeg; переключитесь на CPU (снимите флажок «Использовать GPU» в UI).

## Лицензирование

Если в репозитории отсутствует файл LICENSE, считается, что проект распространяется без явной лицензии. Добавьте LICENSE по необходимости.

## Файлы и директории (назначение)

- `app.py`: Streamlit UI — загрузка файлов, настройки, предпросмотр и экспорт.
- `requirements.txt`: список зависимостей Python.
- `public/plug.png`: заглушка для области предпросмотра.
- `README.md`: документация.

Каталог `src/` — исходный код модулей:

- `src/utils/logger.py`: настройка консольного логгера с форматированием.
- `src/models/base.py`: базовая модель `BaseConfig` для унифицированной валидации Pydantic.
- `src/models/meeting_config.py`: `MeetingConfig` — пути к файлам и имена спикеров, проверка существования.
- `src/models/speaker_config.py`: `PositionConfig`, `SpeakerConfig` — размеры окон, параметры плашек (цвета, рамка, padding, шрифт).
- `src/models/export_config.py`: `ExportConfig` (+ `VideoCodecConfig`, `AudioCodecConfig`, `GPUConfig`) — разрешение, FPS, кодеки, CRF, пресеты, битрейт, GPU.
- `src/config/config_manager.py`: `ConfigManager` — создание CLI-парсера, преобразование аргументов в конфиги, базовая валидация.
- `src/services/video_processor.py`: работа с видео (открытие, метаданные, чтение кадров, letterboxing, расчет FPS/длины).
- `src/services/audio_processor.py`: извлечение аудио (FFmpeg), загрузка/обработка (Librosa), микширование/нормализация, сохранение WAV.
- `src/services/image_processor.py`: загрузка изображений, создание плашек (Pillow), RGBA-наложение поверх кадра (OpenCV).
- `src/services/composition_engine.py`: композиция кадра: фон → окна спикеров → плашки; формирование предпросмотра.
- `src/services/export_service.py`: полный экспорт: выбор кодека (GPU/CPU), запись временного видео, смешивание аудио, мультиплексирование FFmpeg.

## Архитектура: сервисы, поток данных и ключевые компоненты

### Сервисы (`src/services`)

- `VideoProcessor`:
  - загрузка видео и чтение кадров (OpenCV)
  - извлечение метаданных (FPS, размеры, количество кадров)
  - изменение размера с сохранением пропорций (letterboxing) под окно спикера
  - расчет итогового FPS и длины композиции

- `AudioProcessor`:
  - извлечение аудио из видео (FFmpeg → WAV)
  - загрузка и ресемплинг до 44.1 kHz (Librosa), моно
  - выравнивание длительности, суммирование и нормализация 2 дорожек
  - сохранение микса (SoundFile)

- `ImageProcessor`:
  - загрузка фона (OpenCV)
  - генерация плашек (Pillow) с учетом padding/рамки/цветов/шрифта
  - конвертация PIL→OpenCV и альфа-наложение RGBA поверх BGR/BGRA

- `CompositionEngine`:
  - масштабирование фона до целевого разрешения экспорта
  - вычисление позиций окон спикеров (симметрично по половинам кадра)
  - вставка окон спикеров и плашек на кадр
  - быстрый предпросмотр: чтение по одному кадру из каждого видео → JPEG

- `ExportService`:
  - определение доступного энкодера (NVENC/QSV/VAAPI/CPU)
  - покадровая запись временного видео (без аудио)
  - смешивание аудио (через `AudioProcessor`) и мультиплексирование с видео (FFmpeg)
  - применение параметров кодека из `ExportConfig` (preset, crf, bitrate)

### Поток данных (слои в микросервисном стиле)

1. UI (`app.py`) получает ввод пользователя → формирует `SpeakerConfig` и `ExportConfig`.
2. Предпросмотр: `CompositionEngine.create_preview(...)` → `ImageProcessor` (фон) + `VideoProcessor` (первые кадры) → композиция → JPEG.
3. Экспорт: `ExportService.export_video(...)` →
   - `VideoProcessor` открывает видео, считает FPS/длину → параметры пайплайна
   - цикл: `CompositionEngine.compose_frame(...)` → запись кадра в временное видео
   - `AudioProcessor` извлекает/смешивает аудио → FFmpeg мультиплексирует с видео
4. Результат: MP4 предлагается к скачиванию в UI.

Модели (`src/models`) обеспечивают строгую типизацию и валидацию, сервисы — изолированную бизнес-логику; UI — тонкий слой.

### Ключевые компоненты

- `Models`: `MeetingConfig`, `SpeakerConfig`, `ExportConfig` (+ codec/GPU конфиги)
- `ConfigManager`: CLI-парсер и преобразование аргументов в модели
- `Services`: видео/аудио/изображения + `CompositionEngine`/`ExportService` как координация пайплайна
- `UI` (`app.py`): Streamlit-интерфейс для настройки, предпросмотра и экспорта

