# Карта поведения (`face-engine behavior`)

Не «моргание = стресс», а карта отклонений от собственной базы человека сразу по восьми
каналам (лицо ведущее): лицо, глаза, голова, тело, руки, голос, речь, несоответствия слов и тела.
Один сигнал ничего не значит. Интересен момент, где **несколько каналов одновременно**
ушли от базы (hotspot), особенно сразу после вопроса.

**Это не детектор лжи.** Мета-анализы не находят надёжного признака лжи (DePaulo et al. 2003,
158 признаков, медиана |d| ≈ 0.10; Bond & DePaulo 2006: люди угадывают ~54%). Все признаки
растут и от стресса, усталости, сложного вопроса, чтения документа, угла камеры. Подписи
в видео формулируются как мнение. Исследование и оценки доказательности:
`Content Hub / on-the-record/research/behavior-indicators.md`.

## Запуск (облако, CPU)

```bash
pip install -e ".[mediapipe,viz,featurebank]"     # + faster-whisper для --transcribe
apt-get install -y libegl1 libgles2               # нужно MediaPipe на Linux без GPU
face-engine models

face-engine behavior clip.mp4 -o out/                         # видео + звук
face-engine behavior clip.mp4 -o out/ --transcribe small.en   # + слова (faster-whisper)
face-engine behavior clip.mp4 -o out/ --words words.json --subject S   # слова с метками спикеров
face-engine behavior clip.mp4 -o out/ --baseline 0:60 --baseline 300:330   # база = спокойные отрезки
face-engine behavior clip.mp4 -o out/ --baseline-from out/calm.behavior.json  # база из другого ролика
face-engine behavior clip.mp4 -o out/ --states states.json     # [[0, 40, "positive"], [60, 90, "negative_safe"]]
face-engine behavior out/clip.landmarks.npz -o out/ --audio clip.mp4         # без повторной детекции
```

* Если HF-загрузка модели Whisper падает на `cas-server.xethub.hf.co`, запускать с `HF_HUB_DISABLE_XET=1`.
* Лэндмарки кешируются в `out/<stem>.landmarks.npz`; повторный запуск занимает секунды
  (`--redetect`, чтобы пересчитать). 37 с видео 480p детектируются ~50 с на CPU.
* `words.json`: `[[start, end, "word"], ...]` или `[[start, end, "word", "speaker"], ...]`.
  С метками спикеров (`--subject`) вопросы = реплики других людей, латентность ответа
  считается автоматически, голосовые признаки берутся только из реплик субъекта.
  Без меток вопросы ищутся по `?` в транскрипте или задаются `--questions q.json`
  (`[12.3, 40.1]` или `[[start, end, "text"], ...]`).
* Без транскрипта голос субъекта отделяется от голоса спрашивающего по движению губ.

Пороги: `--z 2` (SD от базы), `--min-channels 3`, `--cluster 5` (секунд).

## Что на выходе

| файл | что внутри |
|---|---|
| `<stem>.behavior.json` | `cues` (каталог с оценками доказательности и пометкой `tracked`), `baseline` (медиана и разброс каждого признака), `summary.notes` (готовые фразы), `hotspots`, `questions` (латентность, какие каналы сработали за 0–5 с, пик индекса, время возврата к базе), `mismatches`, `timeline` (каждые 0.5 с: индекс нагрузки, баллы каналов, ведущий признак канала, баллы и сырые значения всех признаков) |
| `<stem>.overlay.json` | для рендера, 10 кадров/с по часам исходника: `pressure`, `channels`, `zones` (эллипсы `[cx, cy, rx, ry]` в пикселях исходника для eyes, brow, mouth, face, head, shoulders, hands, torso), `highlights` (одна зона за раз: зона, признак, подпись, начало/конец), `hotspots` |
| `<stem>.moments.json` | для рендера, «лицо первым»: каждый момент со стимулом (вопрос), меткой (`discomfort`, `holding_back`, `flash`, `mismatch`, `possible_deception_cluster`, `face_change`), готовой формулировкой-мнением, баллом 0–100 с разбивкой (лицо 50, голова/взгляд 15, тело/руки 15, голос 10, речь 10), зоной для свечения, лицевыми событиями и поддержкой, `slowmo` (1.5 с вокруг пика для 0.25×), `face_box` по кадрам, `baseline_frame` (кадр «норма для него» + jpg), `quality` (размер лица, поворот, чтение, fps → `readable`), `confidence`, словами в окне, временем возврата к базе; плюс `idiolect` (привычные для человека признаки) |
| `<stem>.baseline_<state>.jpg` | типичный кадр человека в состоянии `listen` / `speak` / своих метках, вне моментов, голова и взгляд прямо |
| `<stem>.behavior.png` | таймлайн: индекс нагрузки, теплокарта каналов, hotspot-ы, концы вопросов |

### Математика

1. Каждый признак — дорожка по кадрам: уровень (AU, доля времени, градусы, полутоны) или
   поток событий (моргания, кивки, пожатия, слова-паразиты).
2. Скользящие окна с шагом 0.5 с: уровни 2 с (среднее), разброс тона 3 с, частоты 8 с (в минуту).
3. База = медиана и робастный разброс (MAD/IQR) окон из базовых отрезков (по умолчанию весь
   ролик). Для каждого признака есть нижний предел разброса, чтобы плоская база не давала
   огромных z.
4. Балл = z по базе со знаком направления из литературы (`up`, `down`, `both`).
5. Балл канала = сильнейший признак канала. **Индекс нагрузки** 0–100 = среднее трёх
   сильнейших каналов по части выше 1 SD (потолок 4 SD); 0 = всё в пределах нормы человека.
6. **Hotspot** = ≥3 каналов ≥2 SD в пределах 5 с. Привязывается к вопросу, если вопрос
   кончился за 0–6 с до начала.

### Лицо первым (правило владельца, 25 ноября)

Спецификация: `Content Hub/production-map/otr-visual-first-spec.md`.

* **Состояния.** Каждое окно сравнивается с базой того же состояния и ракурса:
  `speak` / `listen` (голос + движение губ, или реплики субъекта по меткам спикеров),
  свои метки из `--states` (`positive`, `negative_safe`), ракурс `front` (|yaw| < 15°) /
  `side` (15–35°); дальше 35° лицо не читается. Группа получает свою базу от 10 с данных,
  меньше 30 с помечается `thin`; иначе берётся база состояния, потом общая.
  Всё это в `behavior.json → states` (длительность, `thin`, медианы/разброс/p95 по каждому
  признаку, пороги микродёрганий, кадры базы, `idiolect`).
* **Микродёрганья** (`twitches`): любой AU (слева, справа или в среднем) выше личного p95
  для этого состояния (+0.1, минимум 0.3), подъём над окружением ≥ 0.25, длительность
  ≤ 0.5 с, вне морганий, без резкого поворота головы; AU рта (10, 17, 20, 23) во время
  речи не считаются.
* **Губы внутрь** (`lip_suck`): видимая красная кайма губ (или нижней губы) резко меньше
  нейтральной при закрытом рте — прокси AU28/AU32 и сильного сжатия.
* **Момент** = окно 0–5 с после вопроса (или вокруг лицевого события, если вопросов нет),
  где есть лицевое событие (≥1 микродёрганье или ≥2 лицевых признака с z ≥ 2.5) и
  поддержка: другой канал с z ≥ 2 или второе лицевое событие. Голосовой/речевой сигнал
  без лица моментом не считается.
* **Качество**: лицо ≥ 120 px по высоте (лоб–подбородок), поворот ≤ 35°, ≥ 25 fps, не
  смотрит вниз в бумаги (≥30% окна голова/взгляд ниже −15°). Иначе `readable: false` с
  причиной, и сценарий не должен заявлять прочтение.

### Подача (UNDER OATH)

`highlights` уже отобраны под стиль: одна зона светится за раз, до трёх зон на hotspot,
по 1.6 с, подписи вида `LIP PRESS · 2.8 SD from own baseline`. Зона `voice` — для
волны/подписи у звука, не для лица. Перед пиком показывать базу и оговорку
«одно отклонение ≠ ложь».

## Признаки (45)

| id | канал | подпись | направление | оценка | нужно |
|---|---|---|---|---|---|
| `lip_press` | face | lip press | up | B | video |
| `chin_raise` | face | chin raise | up | B | video |
| `lip_corner_depress` | face | mouth corners down | up | C | video |
| `brow_lower` | face | brow lowered | up | C | video |
| `inner_brow_raise` | face | inner brows up | up | C | video |
| `eyes_widen` | face | eyes widened | up | C | video |
| `lid_tighten` | face | lids tightened | up | C | video |
| `lip_stretch` | face | lips stretched | up | C | video |
| `disgust_face` | face | nose/upper lip raised | up | C | video |
| `social_smile` | face | lip-only smile | up | B | video |
| `one_sided_mouth` | face | one-sided mouth | up | C | video |
| `lip_suck` | face | lips pulled in | up | C | video |
| `micro_twitch` | face | micro twitches | up | C | video |
| `expressivity` | face | facial movement | both | C | video |
| `blink_rate` | eyes | blink rate | both | B | video |
| `long_closures` | eyes | long eye closures | up | C | video |
| `gaze_aversion` | eyes | gaze averted | up | B | video |
| `gaze_shifts` | eyes | gaze shifts | up | C | video |
| `head_motion` | head | head movement | both | C | video |
| `head_nods` | head | nods | both | C | video |
| `head_shakes` | head | head shakes | up | C | video |
| `head_down` | head | head lowered | up | C | video |
| `lean_back` | body | leans back | up | C | video |
| `posture_shifts` | body | posture shifts | up | C | video |
| `shrugs` | body | shrugs | up | C | video |
| `arms_crossed` | body | arms crossed | up | D | video |
| `body_motion` | body | body movement | both | C | video |
| `illustrators` | hands | speech gestures | down | B | video |
| `self_touch_face` | hands | touches face | up | C | video |
| `self_touch_neck` | hands | touches neck | up | D | video |
| `self_touch_head` | hands | touches head/hair | up | D | video |
| `hand_wringing` | hands | hands together | up | C | video |
| `pitch` | voice | voice pitch | up | B | video |
| `pitch_variability` | voice | pitch range | both | C | video |
| `loudness` | voice | loudness | both | C | video |
| `voice_tension` | voice | voice tension | up | C | video |
| `silence` | voice | silence in answers | up | B | video |
| `speech_rate` | speech | speech rate | both | C | words |
| `fillers` | speech | um / uh | up | B | words |
| `hedges` | speech | hedges | up | B | words |
| `non_recall` | speech | can't recall | up | C | words |
| `repairs` | speech | self-repairs | up | C | words |
| `response_latency` | speech | answer delay | up | B | words |
| `yes_no_mismatch` | mismatch | word vs head | up | C | words |
| `certainty_shrug` | mismatch | sure + shrug | up | D | words |

`video` признаки идут из лэндмарков MediaPipe (лицо 478, поза 33, кисти 21) через
анализаторы движка; `audio` — librosa (pyin F0, RMS, спектр); `words` — из транскрипта.

## Чего пока нет

* rPPG (пульс по цвету кожи), зрачки: при разрешении депозиций и пресс-конференций ненадёжно.
* Ноги и стопы: обычно вне кадра.
* Несколько человек в кадре: движок читает одно лицо; для второго человека — отдельный кроп.
* Облизывание губ, глотание, сжатие челюсти (масстер): не по 35 точкам лица.
* Диаризация внутри движка: метки спикеров нужно подать в `words.json`
  (например, WhisperX + pyannote на своей машине).
* Уклонение от ответа по смыслу (ответ не на тот вопрос) — задача для LLM поверх
  `questions[].text` и `answer_text`.
* Пороги не откалиброваны на размеченных данных; держать их как эвристику.
