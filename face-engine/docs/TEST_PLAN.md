# План проверки изменений

Дата: 2026-11-24. Команды запускаются из корня с .venv/Scripts/python.

| Группа | Кейсы | Проверка |
|---|---|---|
| Геометрия | similarity, отражения, вырождение, повороты | tests/test_geometry.py |
| Лицо | нейтраль, AU и прототипы при разных позах/силе, асимметрия, взгляд, blink vs squint, baseline, пропуски | tests/test_face.py |
| Тело | позы, масштаб, ладони, видимость, жесты/shift/shrug | tests/test_body.py |
| Время | сглаживание, NaN, интервалы, события | tests/test_temporal.py |
| Engine/CLI/cache | структура, JSON, фото, пустой вход, плагины, npz round trip, demo/analyze, сегменты | tests/test_engine.py |
| Банк | именованные признаки, baseline, вопросы, tags, digest | tests/test_featurebank.py |
| Новые показатели | двустороннее закрытие, wink, пропуски/знаменатель, длительность, один кадр, wrap углов, скорость через пробелы | tests/test_behavior.py |
| Контракты | FPS 0/negative/NaN/Inf, времена repeat/reverse/NaN/irregular, пустой список анализаторов, Inf JSON, nonconsecutive indices | tests/test_behavior.py |
| Визуализация | реальная запись overlay + timeline из synthetic frames | tests/test_viz.py |
| Реальная фотография | smile/Duchenne, yaw, crossed arms на MediaPipe portrait | tests/test_mediapipe_integration.py; скачать фото/модели, FACE_ENGINE_SAMPLES |
| Дополнительная устойчивость | некорректные face shapes, Inf anchors, constant face points; разные FPS и noise | дополнительные regression/sweep |
| Звук | генерация WAV, ffmpeg/librosa, тишина и voiced signal, finite output | tests/test_audio_integration.py (test-media extra) |

Результаты фактических прогонов записываются в TEST_RESULTS.md. Недоступные проверки отмечаются явно; они не считаются пройденными. Точность относительно независимой разметки не подменяется синтетическими тестами.


## Дополнительные входные случаи

`tests/test_input_edges.py`: полуоткрытые интервалы с дробными границами;
перекрытие слов и выход конца слова за длину клипа; повреждённые формы массивов
face/body/visibility и бесконечные координаты тела. Реальный WAV/ffmpeg smoke
выполняется отдельно от замоканных PCM-тестов.


## Независимая разметка

TalkingFace: все 5000 кадров и 61 blink ID; без подбора порогов; проверить timestamps,
посчитать one-to-one interval IoU, TP/FP/FN и P/R/F1, просмотреть ошибки.
Eyeblink8: выполнены все восемь роликов и сравнение вариантов по тому же протоколу.
Оценщик: tests/test_evaluation.py. Результаты: BENCHMARKS.md.


## Завершение плана

Все перечисленные инженерные группы пройдены. Дополнительно:
- tests/test_evaluation.py и test_dataset_evaluation.py: границы IoU, one-to-one matching,
  неизвестные кадры, повторные детекции, micro-агрегация и запрет пропуска отсутствующего отчёта.
- tests/test_temporal.py и test_face.py: hysteresis, NaN-разрывы, невалидные release-пороги.
- tests/test_input_edges.py: закрытие детектора/видеозахвата при неудачной инициализации.
- tests/test_engine.py: фактические настройки в meta.engine_config.
Фактический итог: 179 passed, 0 skipped. Независимая количественная оценка относится
к blink-событиям; остальные семейства покрыты инженерными и сквозными проверками,
их точность по независимой разметке не заявляется.
