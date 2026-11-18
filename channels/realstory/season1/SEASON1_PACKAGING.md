# Real Story · Season 1 — пакет для YouTube

Всё, что нужно для выкладки 12 серий сезона: единый вид обложек, плейлист, трейлер канала, конечные заставки, календарь и тексты каждой серии. Тексты для YouTube на английском. Главы (таймкоды) вставляются из `youtube.md` готовой серии, на их месте стоит `[CHAPTERS: ...]`. Ссылки на соседние серии и плейлист вписываются после загрузки, на их месте `[link]`.

## 1. Обложки сезона: одна система на 12 серий

Шаблон: `channels/realstory/brand/thumb_s1.html` (ветка `claude/project-thread-gpuz73` в video-engine), рендер `node thumbs.js <variants.json> <out>` с полем `"tpl": "thumb_s1.html"`. Превью сезона: `season1_thumbs_grid.jpg`, параметры каждой обложки: `season1_thumbs.json`.

Что одинаково во всех 12:
- Сетка: текст всегда слева (58 px от края, 55–60 % ширины), предмет фото справа, правый нижний угол 250×100 пустой (время ролика и водяной знак).
- Шрифт: Archivo ширина 62 / 880, 2 строки (максимум 3). Первая строка кость `#f2efe8` (на светлой серии чернила `#0e0f11`), ключевая строка сигнальный красный `#e2231a`.
- Подпись сезона: тонкий сдвиг на 4 px слева у каждой буквы в акценте серии. Это единственное место, где акцент серии появляется на обложке, и оно делает 12 обложек одной серией в ленте.
- Моно-тег справа сверху: красный квадрат, `S1 E07` в акценте серии, дальше место и год. Номер серии помогает смотреть подряд.
- Второй крючок: моно-штамп над заголовком красным (`— 52 SECONDS`, `— REAL ATC RADIO`) и красный рисованный круг на главной детали фото. Без плашек, рамок и подложек под текстом: читаемость даёт затемнение в цвет фона серии и мягкая тень.
- Фон: настоящее фото серии во весь кадр (не графика), затемнение слева в цвет `ground` серии, лёгкое зерно. Знак канала на обложке не ставим.

Палитра сезона (соседние серии не делят фон, синий только у Gemini 8):

| Серия | Фон (ground) | Акцент | Откуда |
|---|---|---|---|
| S1E01 Apollo 12 | `#172331` | `#e08a3c` | штормовой сине-серый / оранжевая башня |
| S1E02 The Bloop | `бирюзово-зелёная глубина` | `ледяной циан` | из полярных фото |
| S1E03 Godwit B6 | `#2a2118` | `#d9824a` | илистый бурый / рыжее перо |
| S1E04 Every Tornado | `#23251c` | `#f2c230` | оливково-серая суперячейка / жёлтая сирена |
| S1E05 Hunga Tonga | `пепельный угольно-фиолетовый` | `серно-жёлтый` | проверить по GOES |
| S1E06 Ghost Octopus | `бездна, почти чёрный с фиолетом` | `бледный призрачно-розовый` | из кадров Okeanos |
| S1E07 Iceberg A23a | `#dfe5ea` | `#1f4fa8` | светлая серия: бледный лёд / кобальт |
| S1E08 Mars Landing | `#2b1a12` | `#efe2c6` | ржавый Jezero / кремовый парашют |
| S1E09 Saturn's Rings | `#2a2016` | `#d4a640` | сепия / старое золото |
| S1E10 Gemini 8 | `#0d1626` | `#e9c11b` | морской синий (единственный) / жёлтый поплавок |
| S1E11 13 Saturn V Launches | `#211a15` | `#ff8a2a` | тёплый графит выхлопа / пламя |
| S1E12 Flight 1549 | `#2b3540` | `#f2c12e` | сланцевый Гудзон / жёлтый плот |

Для каждой серии в превью собран вариант A. Треды серий делают свои A/B/C по этому шаблону, на своих фото и проверенных фактах; всё, что обещает обложка, должно быть в ролике.

## 2. Плейлист

**Название:** `Real Story · Season 1`

**Описание:**
```
Twelve true stories, each told with the records it left behind: NASA mission film and cockpit audio, NOAA underwater recordings, satellite images, air traffic control tapes and NTSB reports.

Lightning hits Apollo 12 twice. A young bird flies 11 days without landing. A volcano sends a pressure wave around the planet. An iceberg the size of a city waits 30 years, then leaves. A plane lands on the Hudson with 208 seconds to decide.

Every episode answers one question with the primary sources on screen, plus our own measurements from the data. Sources and credits are under every video.

New episodes on Wednesdays and Saturdays.
```
Порядок: E01 → E12 по номеру. Видимость: публичный, сортировка ручная. Добавить в «Избранные разделы» главной страницы канала первым рядом.

## 3. Трейлер канала (для новых зрителей, 50–55 с)

Собирается движком как короткая серия из кадров сезона: голос тот же (Kokoro am_michael), музыка подложкой, по 3–4 с на кадр, в конце знак канала и красный стоп-блок. Текст за кадром:

```
[Apollo 12 launch film] November 1969. Lightning hits a Moon rocket. Twice.
[Godwit B6 in hand] A four-month-old bird flies eleven days without landing.
[Bloop spectrogram] The ocean makes a sound so loud it crosses the Pacific.
[GOES Tonga ring] A volcano shakes barometers on the other side of the world.
[Hudson photo] A plane lands on a river. Two hundred and eight seconds.

These are real stories. We tell them with what they left behind:
the film, the radio, the logs, the data.
No re-enactments pretending to be footage. When something was never filmed, we say so.

One question per episode. One honest answer.
Real Story.
```
Титры на экране (по одному слою, без плашек): `1969 · HIT TWICE` → `11 DAYS · NONSTOP` → `1997 · NOT A MONSTER` → `2022 · FROM SPACE` → `208 SECONDS` → `REAL STORY` + стоп-блок. Длительность ~52 с, 1920×1080. Поставить в Studio → Настройка канала → Макет → «Трейлер для новых зрителей». Для подписчиков: последняя серия (Studio делает это автоматически при выборе «Рекомендуемое видео для подписчиков»).

## 4. Конечные заставки

Фон заставки уже есть: `branding_real_story/endscreen_1920x1080.png`, движок вставляет его в последние 20 с. В Studio для каждой серии:

- **Элемент 1 (большой слева):** конкретное видео, следующая серия сезона. Пока её нет на канале: «Самое подходящее для зрителя», потом заменить.
- **Элемент 2 (справа сверху):** плейлист `Real Story · Season 1`.
- **Подписка:** круг справа снизу.

| Серия | Элемент 1 | Почему |
|---|---|---|
| S1E01 | S1E02 The Bloop | следующая по порядку |
| S1E02 | S1E03 Godwit B6 | следующая по порядку |
| S1E03 | S1E04 Every Tornado | следующая по порядку |
| S1E04 | S1E05 Hunga Tonga | следующая по порядку |
| S1E05 | S1E06 Ghost Octopus | следующая по порядку |
| S1E06 | S1E07 Iceberg A23a | следующая по порядку |
| S1E07 | S1E08 Mars Landing | следующая по порядку |
| S1E08 | S1E09 Saturn's Rings | следующая по порядку |
| S1E09 | S1E10 Gemini 8 | следующая по порядку |
| S1E10 | S1E11 13 Saturn V Launches | следующая по порядку |
| S1E11 | S1E12 Flight 1549 | следующая по порядку |
| S1E12 | E01 Apollo 12 | круг сезона: с последней на первую |

Шортсы: в каждом шортсе в поле «Связанное видео» стоит полная серия. В закреплённом комментарии шортса ссылка на серию.

## 5. Календарь выкладки

Две серии в неделю, среда и суббота в 15:00 по Нью-Йорку (20:00 UTC, 23:00 МСК). Шортсы каждый день в 12:00 по Нью-Йорку (17:00 UTC, 20:00 МСК): первый и второй шортс серии на следующие два дня, третий в утро следующей серии в 10:00 по Нью-Йорку (15:00 UTC, 18:00 МСК), чтобы подогреть показ. Если серия не готова к дате, вся цепочка сдвигается на один слот, порядок не меняется. Загружать заранее как «Запланировано», приватно до времени выхода.

| Дата | День | Время (NY) | Что |
|---|---|---|---|
| 25.11.2026 | Ср | 15:00 | **Серия S1E01 · Apollo 12: The 5 Words That Saved the Mission** |
| 26.11.2026 | Чт | 12:00 | Шортс 1 к S1E01 Apollo 12 |
| 27.11.2026 | Пт | 12:00 | Шортс 2 к S1E01 Apollo 12 |
| 28.11.2026 | Сб | 10:00 | Шортс 3 к S1E01 Apollo 12 |
| 28.11.2026 | Сб | 15:00 | **Серия S1E02 · The Loudest Mystery Sound in the Ocean** |
| 29.11.2026 | Вс | 12:00 | Шортс 1 к S1E02 The Bloop |
| 30.11.2026 | Пн | 12:00 | Шортс 2 к S1E02 The Bloop |
| 02.12.2026 | Ср | 10:00 | Шортс 3 к S1E02 The Bloop |
| 02.12.2026 | Ср | 15:00 | **Серия S1E03 · 11 Days Without Landing** |
| 03.12.2026 | Чт | 12:00 | Шортс 1 к S1E03 Godwit B6 |
| 04.12.2026 | Пт | 12:00 | Шортс 2 к S1E03 Godwit B6 |
| 05.12.2026 | Сб | 10:00 | Шортс 3 к S1E03 Godwit B6 |
| 05.12.2026 | Сб | 15:00 | **Серия S1E04 · Every Tornado Since 1950 on One Map. They Didn't Increase, They Moved** |
| 06.12.2026 | Вс | 12:00 | Шортс 1 к S1E04 Every Tornado |
| 07.12.2026 | Пн | 12:00 | Шортс 2 к S1E04 Every Tornado |
| 09.12.2026 | Ср | 10:00 | Шортс 3 к S1E04 Every Tornado |
| 09.12.2026 | Ср | 15:00 | **Серия S1E05 · A Volcano Made a Tsunami With Air. We Measured It From Space** |
| 10.12.2026 | Чт | 12:00 | Шортс 1 к S1E05 Hunga Tonga |
| 11.12.2026 | Пт | 12:00 | Шортс 2 к S1E05 Hunga Tonga |
| 12.12.2026 | Сб | 10:00 | Шортс 3 к S1E05 Hunga Tonga |
| 12.12.2026 | Сб | 15:00 | **Серия S1E06 · It Was Found 10 Years Ago. It Still Has No Name** |
| 13.12.2026 | Вс | 12:00 | Шортс 1 к S1E06 Ghost Octopus |
| 14.12.2026 | Пн | 12:00 | Шортс 2 к S1E06 Ghost Octopus |
| 16.12.2026 | Ср | 10:00 | Шортс 3 к S1E06 Ghost Octopus |
| 16.12.2026 | Ср | 15:00 | **Серия S1E07 · The Iceberg That Waited 30 Years to Move** |
| 17.12.2026 | Чт | 12:00 | Шортс 1 к S1E07 Iceberg A23a |
| 18.12.2026 | Пт | 12:00 | Шортс 2 к S1E07 Iceberg A23a |
| 19.12.2026 | Сб | 10:00 | Шортс 3 к S1E07 Iceberg A23a |
| 19.12.2026 | Сб | 15:00 | **Серия S1E08 · Mars Landing, Second by Second** |
| 20.12.2026 | Вс | 12:00 | Шортс 1 к S1E08 Mars Landing |
| 21.12.2026 | Пн | 12:00 | Шортс 2 к S1E08 Mars Landing |
| 23.12.2026 | Ср | 10:00 | Шортс 3 к S1E08 Mars Landing |
| 23.12.2026 | Ср | 15:00 | **Серия S1E09 · Why Saturn's Rings Vanished in 1612** |
| 24.12.2026 | Чт | 12:00 | Шортс 1 к S1E09 Saturn's Rings |
| 25.12.2026 | Пт | 12:00 | Шортс 2 к S1E09 Saturn's Rings |
| 26.12.2026 | Сб | 10:00 | Шортс 3 к S1E09 Saturn's Rings |
| 26.12.2026 | Сб | 15:00 | **Серия S1E10 · Armstrong's Worst Minutes in Orbit** |
| 27.12.2026 | Вс | 12:00 | Шортс 1 к S1E10 Gemini 8 |
| 28.12.2026 | Пн | 12:00 | Шортс 2 к S1E10 Gemini 8 |
| 30.12.2026 | Ср | 10:00 | Шортс 3 к S1E10 Gemini 8 |
| 30.12.2026 | Ср | 15:00 | **Серия S1E11 · 13 Saturn V Launches at Once** |
| 31.12.2026 | Чт | 12:00 | Шортс 1 к S1E11 13 Saturn V Launches |
| 01.01.2027 | Пт | 12:00 | Шортс 2 к S1E11 13 Saturn V Launches |
| 02.01.2027 | Сб | 10:00 | Шортс 3 к S1E11 13 Saturn V Launches |
| 02.01.2027 | Сб | 15:00 | **Серия S1E12 · Flight 1549: 208 Seconds, Real Radio** |
| 03.01.2027 | Вс | 12:00 | Шортс 1 к S1E12 Flight 1549 |
| 04.01.2027 | Пн | 12:00 | Шортс 2 к S1E12 Flight 1549 |
| 05.01.2027 | Вт | 10:00 | Шортс 3 к S1E12 Flight 1549 |

Для серий 04, 07, 09, 10, 11, 12 шортсы ещё делаются в своих тредах: их названия и тексты придут в `youtube.md` серии.

## 6. Тексты серий

Категория у всех: Science & Technology (28). Плейлист: Real Story · Season 1. Флаг «Изменённый или синтетический контент»: да (синтетический голос). Язык: английский. Первое название в списке рекомендуемое.

### S1E01 · Apollo 12 · выход 25.11.2026

**Названия:**
1. Apollo 12: The 5 Words That Saved the Mission (45)
2. Lightning Hit Apollo 12 Twice. Five Words Saved It (50)
3. SCE to AUX: The 52 Seconds That Almost Ended Apollo 12 (54)

**Описание:**
```
November 14, 1969. Thirty-six seconds after liftoff, lightning hits Apollo 12. Sixteen seconds later it hits again. Almost every warning light comes on, the fuel cells drop offline, the guidance platform tumbles, and the screens in Houston fill with garbage numbers. Nobody can tell if the spacecraft is still alive.

A young engineer named John Aaron recognises the pattern from a test a year earlier. He says five words: "Try SCE to AUX." Almost nobody in Mission Control knows what that means. This is the 52 seconds that saved the mission, told with the real launch film, the real cockpit audio and the original NASA transcripts.

What's new here: we follow the chain of trust link by link, from Aaron to flight director Gerry Griffin to CapCom Gerald Carr to Alan Bean's hand on the switch, and stop the clock on three ways the story could have ended differently.

Sources
- NASA, Apollo 12 Mission Report (MSC-01855, March 1970)
- NASA, Analysis of Apollo 12 Lightning Incident (MSC-01540, February 1970)
- NASA, Apollo 12 Technical Air-to-Ground Voice Transcription and onboard voice recording
- NASA Johnson Space Center Oral History Project: John W. Aaron, Gerald D. Griffin
- NASA launch film and photographs of Apollo 12 (public domain)

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 1 of 12
Whole season: [playlist link]
Next: The Bloop · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#Apollo12 #NASA #SpaceHistory
```
**Теги:** Apollo 12, SCE to AUX, John Aaron, lightning strike, Saturn V, NASA, Mission Control, Pete Conrad, Alan Bean, space history, Apollo program, Mission Records, Apollo 12 lightning, Gerry Griffin, moon landing, 1969, NASA history, Real Story

**Закреплённый комментарий:** John Aaron was 24. If you have worked a job where one odd memory saved the day, tell us about it below.

### S1E02 · The Bloop · выход 28.11.2026

**Названия:**
1. The Loudest Mystery Sound in the Ocean (38)
2. The Bloop Was Not a Monster. NOAA's Recordings Show What It Was (63)
3. We Slowed the Bloop Back to Real Speed. Here's What It Is (57)

**Описание:**
```
In 1997, NOAA's underwater microphones picked up a sound so loud it crossed thousands of kilometers of ocean. The internet called it a monster. We went back to NOAA's own recordings, slowed the famous file back to real speed, measured it, and followed the clues to an iceberg seven times the size of Manhattan that broke apart right inside NOAA's microphone array.

What's new here: the public Bloop file is sped up 16 times, and we measured that half of its energy sits below 15 Hz, under the edge of human hearing. We also ran the numbers on the SOFAR channel, the "pipe with no walls" that let the sound cross an ocean.

Sources
- NOAA PMEL, "Bloop": https://www.pmel.noaa.gov/acoustics/sounds/bloop.html
- NOAA Ocean Service, "What is the bloop?": https://oceanservice.noaa.gov/facts/bloop.html
- NOAA PMEL sounds: Train, Julia, Upsweep: https://www.pmel.noaa.gov/acoustics/sounds/train.html · https://www.pmel.noaa.gov/acoustics/sounds/julia.html · https://www.pmel.noaa.gov/acoustics/sounds/upsweep.html
- NOAA PMEL cryogenic sounds (Slow Down): https://www.pmel.noaa.gov/acoustics/specs_cryogenic.html
- Dziak et al. (2013), "Life and death sounds of iceberg A53a", Oceanography 26(2): https://tos.org/oceanography/assets/docs/26-2_dziak.pdf
- NASA, ISS016-E-023196 (iceberg A53a, Jan 15, 2008): https://images.nasa.gov/details/iss016e023196
- NASA/JPL, PIA21785 (Larsen C calving, 2017): https://images.nasa.gov/details/PIA21785
- Our calculations: real duration, energy below 15 Hz, SOFAR spreading loss.

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 2 of 12
Whole season: [playlist link]
Previous: Apollo 12 · [link]
Next: Godwit B6 · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#TheBloop #OceanMystery #NOAA
```
**Теги:** bloop, the bloop, bloop sound, NOAA, ocean mystery, underwater sound, icequake, iceberg, SOSUS, SOFAR channel, Antarctica, unexplained sounds, Case Closed, A53a, PMEL, hydrophone, ocean sounds, case closed, mystery solved, Real Story

**Закреплённый комментарий:** The famous Bloop file is sped up 16 times. Listen to the real-speed version in the video with headphones and tell us what you hear.

### S1E03 · Godwit B6 · выход 02.12.2026

**Названия:**
1. 11 Days Without Landing (23)
2. A 4-Month-Old Bird Flew 13,560 km Nonstop. Nobody Showed It the Way (67)
3. Godwit B6: 11 Days Nonstop From Alaska to Tasmania (50)

**Описание:**
```
In October 2022 a bar-tailed godwit called B6, about four months old, took off from Alaska and did not land for 11 days and 1 hour. It flew at least 13,560 km over open ocean and set the world record for the longest nonstop bird flight. Nobody showed it the way: the adults had left weeks earlier.

What's new here: we rebuilt B6's approximate route from the published waypoints and pulled NOAA's GFS weather model for every six hours of the flight. At about 1,500 m the wind blew the bird's way roughly 9 hours out of 10. It explains the overshoot past New Zealand. It doesn't clearly explain the sharp turn toward Tasmania.

Sources
- USGS Alaska Science Center, "Juvenile bar-tailed godwit B6 sets world record": https://www.usgs.gov/centers/alaska-science-center/news/juvenile-bar-tailed-godwit-b6-sets-world-record
- Guinness World Records, longest non-stop migration by a bird: https://www.guinnessworldrecords.com/world-records/86385-longest-non-stop-migration-by-a-bird
- Gill et al. (2009), "Extreme endurance flights by landbirds crossing the Pacific Ocean", Proc. R. Soc. B
- USGS, "Ultra-marathon champion bird may plan flights based on weather across the Pacific": https://www.usgs.gov/news/national-news-release/ultra-marathon-champion-bird-may-plan-flights-based-weather-across
- USGS tracking data, bar-tailed godwits: https://www.usgs.gov/data/tracking-data-bar-tailed-godwits-limosa-lapponica
- NOAA NCEI, GFS 1° analyses, Oct 12–25, 2022
- Map: Natural Earth (public domain)

Footage and photo credits
- Bar-tailed godwits, Wadden Sea (takeoff, swarm, feeding, flock): Beeld en Geluid / Open Images, via Wikimedia Commons, CC BY-SA 3.0 NL
- Bar-tailed godwit in surf, Dingle Peninsula, Ireland: Wikimedia Commons, CC BY-SA 4.0
- Bar-tailed godwits flying and landing: Terra X / ZDF, "Langstreckenrekord im Vogelflug", Wikimedia Commons, CC BY 4.0 (cropped)
- Photos: USGS Alaska Science Center (public domain)
- Godwit call: xeno-canto XC1107762, CC0
None of the footage shows B6 itself. The route map is our own approximate reconstruction, not B6's raw track.

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 3 of 12
Whole season: [playlist link]
Previous: The Bloop · [link]
Next: Every Tornado · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#Godwit #BirdMigration #WorldRecord
```
**Теги:** bar-tailed godwit, godwit B6, longest bird flight, nonstop flight, bird migration, world record, Alaska to Tasmania, animal navigation, tailwind, USGS, satellite tracking, One Path, 13560 km, longest flight, migration record, B6, Real Story

**Закреплённый комментарий:** B6 had never made this trip and the adults had already left. How do you think it knew where to go?

### S1E04 · Every Tornado · выход 05.12.2026

**Названия:**
1. Every Tornado Since 1950 on One Map. They Didn't Increase, They Moved (69)
2. 9x More Tornadoes? We Checked All 68,693 Records (48)
3. Why Tornadoes Got Deadlier Without Getting More Common (54)

**Описание:**
```
We went through all 68,693 tornadoes in NOAA's Storm Prediction Center record, 1950 to 2022, and put every one of them on a single map. The count rose about nine times. Almost all of that growth is in the weakest tornadoes, the ones nobody used to see or report.

What really changed is quieter and more dangerous: tornadoes now come in bigger bursts, and the activity has shifted east, out of the open plains and into places where each tornado kills more people.

What's new here: our own counts from the full SPC database, split by rating, by decade and by region, and a plain answer to the question "are there more tornadoes now?".

Sources
- NOAA Storm Prediction Center, Severe Weather Database (tornadoes 1950-2022): https://www.spc.noaa.gov/wcm/
- Brooks, Carbin & Marsh (2014), Science, increased variability of tornado occurrence: https://doi.org/10.1126/science.1257460
- Gensini & Brooks (2018), npj Climate and Atmospheric Science, spatial trends in US tornado frequency: https://doi.org/10.1038/s41612-018-0048-2
- Simmons & Sutter (2005), tornado warnings and fatalities
- NWS Central Region, Joplin tornado service assessment (2011)
- NWS damage surveys: El Reno (May 31, 2013), Enderlin (June 20, 2025)
- Our calculations: counts by EF rating, decade and longitude from the SPC file.

Photo and video credits: NOAA / NSSL Photo Library, FEMA, NWS (public domain); Ray Bohac (CC BY 3.0); Jennifer Brindley, Ks0stm, Silosarg, Runningonbrains, Immewnity (CC BY-SA); Bob Webster, macahanC6R Eje Gustafsson (CC BY 2.0); BusyWikipedian (CC BY 4.0); Wikideas1 (CC0). Full list with links in the pinned comment.

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 4 of 12
Whole season: [playlist link]
Previous: Godwit B6 · [link]
Next: Hunga Tonga · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#Tornado #NOAA #WeatherData
```
**Теги:** tornadoes, tornado map, every tornado since 1950, tornado alley, dixie alley, tornado statistics, NOAA, Storm Prediction Center, SPC tornado database, EF5 tornado, Joplin tornado, El Reno tornado, tornado history, severe weather, climate and tornadoes, weather data, data visualization, Real Story

**Закреплённый комментарий:** All 68,693 tornadoes are in the map, including the tiny EF0s nobody counted in 1950. Where do you live, and did you expect it to be on this map? Full photo credits are below.

### S1E05 · Hunga Tonga · выход 09.12.2026

**Названия:**
1. A Volcano Made a Tsunami With Air. We Measured It From Space (60)
2. The Tonga Eruption Shook Barometers in Britain. We Tracked the Wave (67)
3. Hunga Tonga: The Pressure Wave That Moved the Sea Worldwide (59)

**Описание:**
```
On January 15, 2022, a volcano in the South Pacific exploded. Fifteen hours later, barometers in Britain jumped, with no storm anywhere near. That same day, the sea moved in the Caribbean and the Mediterranean, places the volcano's water could never reach in time.

We went back to NOAA's raw satellite data and tracked the pressure ring ourselves, frame by frame: 59 pictures, 41 measured positions, a straight line on the chart, 310 meters per second. Then we used that speed to predict when the wave hit Sydney, and found the extra report in Sydney Airport's own weather log, right on time.

What's new here: our own speed measurement from GOES-17, the Sydney Airport special report at 07:30 UTC (+2 hPa, back down 24 minutes later), the one-line formula that explains why Japan's tsunami rules failed that night, and why the deepest trench in the Southern Hemisphere sits right next to the volcano.

Sources
- NOAA GOES-17 ABI L2 imagery, bands 10 and 13, 15 Jan 2022 (NOAA Open Data on AWS): https://registry.opendata.aws/noaa-goes/
- NOAA NCEI Integrated Surface Database, Sydney Airport (YSSY) reports, 15 Jan 2022: https://registry.opendata.aws/noaa-isd/
- Copernicus Sentinel-2 L2A imagery, tile 1KFT, 2017–2022 (Element 84 / AWS): https://registry.opendata.aws/sentinel-2-l2a-cogs/
- Matoza et al. 2022, Science, atmospheric waves from the Hunga eruption: https://doi.org/10.1126/science.abo7063
- Proud et al. 2022, Science, plume height 57 km: https://doi.org/10.1126/science.abo4076
- USGS / Van Eaton et al. 2023, record lightning: https://www.usgs.gov/news/science-snippet/tongas-hunga-eruption-produced-most-intense-lightning-ever-recorded
- Clare et al. 2023, Science, seafloor flows and the cut cable: https://doi.org/10.1126/science.adi3038
- Imamura et al. 2022, Pure and Applied Geophysics, the tsunami in Japan: https://link.springer.com/article/10.1007/s00024-022-03058-0
- Japan Meteorological Agency, JpGU 2022 presentation U09-01: https://pub.confit.atlas.jp/en/event/jpgu2022/presentation/U09-01
- Devlin et al. 2023, Ocean Science, global water-level response: https://os.copernicus.org/articles/19/517/2023/
- NOAA NCEI, January 15, 2022 Tonga volcanic eruption and tsunami: https://ncei.noaa.gov/news/january-15-2022-tonga-volcanic-eruption-and-tsunami
- Royal Meteorological Society, the shockwave over the UK: https://rmets.org/metmatters/tongan-eruption-sends-atmospheric-shockwaves-around-world
- NASA SVS, Birth of a New Island: https://svs.gsfc.nasa.gov/12800/
- Krakatoa 1883 barograph passages (Acoustics Today, 2010): https://acousticstoday.org/issues/2010AT/Apr2010/files/basic-html/page18.html
- Map: Natural Earth (public domain)
- Our calculations: pressure-wave speed from GOES-17 (linear fit, 41 points), predicted arrival times, √(g·h) and depth = speed²/g.

Footage and image credits
- Himawari-8 imagery: JMA, NICT Digital Typhoon, CSU/CIRA, JAXA, NOAA/NESDIS (Wikimedia Commons, CC BY 4.0 and public domain)
- ISS photo ISS066-E-117997, GPS wave chart PIA24905 (NASA/JPL-Caltech), NASA SVS stills: NASA (public domain)
- Tsunami model stills: NOAA PMEL (public domain)
- Aerials of Tonga: NZ Defence Force (CC BY 4.0)
- Barometer recording: Tinux, Wikimedia Commons (CC0)
- Pressure change at Maunakea: CFHT / Gemini / NOIRLab / NSF / AURA (CC BY 4.0)
- Oil spill, Ventanilla: Ministerio de Defensa del Perú (CC BY 2.0); Peru coast: Presidencia de la República del Perú (CC BY 3.0)
- 2015 island footage: NASA "Birth of a New Island" (Kingdom of Tonga MLSNR; D. Grouille & C. Sabau)
Contains modified Copernicus Sentinel data 2017–2022.

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 5 of 12
Whole season: [playlist link]
Previous: Every Tornado · [link]
Next: Ghost Octopus · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#HungaTonga #Tsunami #Volcano
```
**Теги:** hunga tonga, tonga volcano, tonga eruption 2022, pressure wave, lamb wave, meteotsunami, tsunami, barometer, GOES-17, satellite data, krakatoa, volcano documentary, Hunga Tonga-Hunga Ha'apai, shockwave, volcanic eruption, NOAA, Real Story

**Закреплённый комментарий:** Did your own barometer or weather station catch the wave on January 15, 2022? Post the time and place below.

### S1E06 · Ghost Octopus · выход 12.12.2026

**Названия:**
1. It Was Found 10 Years Ago. It Still Has No Name (47)
2. The Ghost Octopus Still Has No Name. Its Nursery May Not Last (61)
3. Casper, the Ghost Octopus: Found in 2016, Still Unnamed (55)

**Описание:**
```
In February 2016, a NOAA robot 4,290 meters down off Hawaii filmed a pale octopus nobody had ever seen. The internet named it Casper. Ten years later it still has no scientific name.

We went back to NOAA's own footage, dive records and the research that followed. Its relatives lay their eggs on dead sponges, the sponges only grow on rocks called manganese nodules, and those rocks grow a few millimeters every million years. Then we looked at the only full-scale mining test ever run and the first US commercial deep-sea mining application that is under review right now.

What's new here: our own calculation of the nursery's age (2.5 to 5 million years) and the pressure at Casper's depth.

Sources
- NOAA OER, EX1603 Dive 1 footage, "Very Deep, Ghostlike Incirrate Octopod" (27 Feb 2016)
- NOAA OER, EX1603 Dive 01 summary: https://oer.hpc.msstate.edu/okeanos/ex1603/EX1603_Dive01_Summary_20160227_FINAL.pdf
- M. Vecchione, NOAA OER mission log (2 Mar 2016): https://oceanexplorer.noaa.gov/okeanos/explorations/ex1603/logs/mar2/mar2.html
- Purser et al. (2016), Current Biology 26(24): https://doi.org/10.1016/j.cub.2016.10.052
- Robison et al. (2014), PLoS ONE, 53-month brooding of Graneledone boreopacifica
- Simon-Lledó et al. (2019), Scientific Reports, DISCOL 26 years later: https://doi.org/10.1038/s41598-019-44492-w
- Executive Order 14285 (24 Apr 2025)
- Our calculations: nodule age (radius ÷ growth rate), pressure at 4,290 m.

Footage and images: NOAA Ocean Exploration (public domain); GEOMAR ROV KIEL 6000 (CC BY 4.0); Ifremer (CC BY 4.0); Hannes Grobe / AWI (CC BY-SA 4.0).

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 6 of 12
Whole season: [playlist link]
Previous: Hunga Tonga · [link]
Next: Iceberg A23a · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#GhostOctopus #DeepSea #NOAA
```
**Теги:** ghost octopus, casper octopus, deep sea octopus, NOAA, Okeanos Explorer, deep sea mining, manganese nodules, Clarion-Clipperton Zone, new species, deep sea creatures, ocean exploration, incirrate octopus, EX1603, Hawaii deep sea, Real Story

**Закреплённый комментарий:** Casper still has no scientific name. If you could name it, what would it be?

### S1E07 · Iceberg A23a · выход 16.12.2026

**Названия:**
1. The Iceberg That Waited 30 Years to Move (40)
2. The World's Biggest Iceberg Sat Still for 30 Years. Then It Left (64)
3. A23a: We Tracked the Biggest Iceberg on Earth From Space (56)

**Описание:**
```
In August 1986 a slab of ice more than twice the size of Greater London broke off Antarctica's Filchner Ice Shelf. Within months it ran aground on the floor of the Weddell Sea, and there it sat for more than 30 years. It was called A23a.

In 2020 it started to move. In 2024 it got caught in a spinning column of water and turned in place for months. Then it broke free, drifted north toward South Georgia, and began to fall apart.

What's new here: we tracked A23a ourselves from satellite images, measured its position frame by frame and worked out how fast it drifted at each stage of the journey.

Sources
- British Antarctic Survey, A23a news and expedition reports: https://www.bas.ac.uk/
- European Space Agency / Copernicus Sentinel-1 and Sentinel-2 imagery of A23a (2023-2025): https://www.esa.int/
- NASA Earth Observatory, A23a image stories: https://earthobservatory.nasa.gov/
- U.S. National Ice Center, Antarctic iceberg positions: https://usicecenter.gov/
- Our calculations: positions and drift speed from dated satellite images.

Image credits: contains modified Copernicus Sentinel data (2023-2025); Pierre Markuse (CC BY 2.0); NASA (public domain). Full list with links in the pinned comment.

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 7 of 12
Whole season: [playlist link]
Previous: Ghost Octopus · [link]
Next: Mars Landing · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#A23a #Iceberg #Antarctica
```
**Теги:** A23a, iceberg A23a, largest iceberg, biggest iceberg in the world, Antarctica, Weddell Sea, South Georgia, Taylor column, Filchner Ice Shelf, iceberg drift, satellite images, Copernicus Sentinel, British Antarctic Survey, NASA Earth Observatory, ice, polar science, Real Story

**Закреплённый комментарий:** We measured A23a's drift from dated satellite images. If you spot a position we got wrong, post the date and the image and we will check it.

### S1E08 · Mars Landing · выход 19.12.2026

**Названия:**
1. Mars Landing, Second by Second (30)
2. Nobody Was Flying It: Perseverance Lands Itself on Mars (55)
3. Perseverance's Landing in Real Video, Second by Second (54)

**Описание:**
```
In February 2021 a one-ton rover landed itself on Mars. Radio signals took more than 11 minutes to reach Earth, so nobody could touch the controls. This is the Perseverance landing, second by second, with the real onboard video and the real voice of mission control.

We follow it from the parachute (with a secret message hidden in its pattern) to the moment it finds itself on a hazard map of Jezero crater, picks its own landing spot and is lowered on ropes by a rocket-powered sky crane.

Sources
NASA/JPL-Caltech: Perseverance descent and touchdown onboard video (Feb 22, 2021), Mars 2020 landing commentary, NASA Photojournal images PIA23722, PIA23970, PIA24167, PIA24268, PIA24285, PIA24349, PIA24378, PIA24428, PIA24431, PIA24485, PIA25214, NASA HQ photos NHQ202102180010 and NHQ202102180050, Mars microphone recording (Feb 20, 2021).

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 8 of 12
Whole season: [playlist link]
Previous: Iceberg A23a · [link]
Next: Saturn's Rings · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#Mars #Perseverance #NASA
```
**Теги:** Perseverance, Mars landing, NASA, JPL, sky crane, Jezero crater, Mars 2020, dare mighty things, Swati Mohan, real video, space, Mission Records, Mars 2020 landing, terrain relative navigation, Mars rover, Real Story

**Закреплённый комментарий:** Did you find the message hidden in the parachute before we decoded it? It is in the video at the parachute section.

### S1E09 · Saturn's Rings · выход 23.12.2026

**Названия:**
1. Why Saturn's Rings Vanished in 1612 (35)
2. Galileo Lost Saturn's Rings in 1612. Here's Where They Went (59)
3. Saturn's Rings Disappear Every 15 Years. Galileo Saw It First (61)

**Описание:**
```
In 1610 Galileo pointed his telescope at Saturn and saw something no one could explain: a planet with two companions, one on each side. He hid the discovery in a coded anagram. Two years later he looked again, and the companions were gone.

The rings had not vanished. Earth had moved into their plane, and rings hundreds of thousands of kilometers wide but in most places only tens of meters thick turned edge-on and almost disappeared. It took Christiaan Huygens until 1659 to work it out. The same thing happens roughly every 15 years, and we watched it happen with Hubble and Cassini.

What's new here: Galileo's own drawings and letters next to the Hubble and Cassini images of the modern ring-plane crossings, and the geometry that makes the rings disappear.

Sources
- Galileo Galilei, letters on Saturn (1610-1612), including the anagram and the letter to Mark Welser (1 Dec 1612)
- Christiaan Huygens, Systema Saturnium (1659), scans on Wikimedia Commons
- NASA / ESA Hubble images of the 1995 ring-plane crossing (PIA01273 and related)
- NASA / JPL-Caltech / Space Science Institute, Cassini images of the 2009 equinox
- NASA, Saturn ring-plane crossing 2025 explainers: https://science.nasa.gov/saturn/
- Our calculations: the ring opening angle seen from Earth, 1610-2025.

Image credits: NASA, ESA, JPL-Caltech, Space Science Institute (public domain); historical scans via Wikimedia Commons (public domain). Full list with links in the pinned comment.

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 9 of 12
Whole season: [playlist link]
Previous: Mars Landing · [link]
Next: Gemini 8 · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#Saturn #Galileo #Astronomy
```
**Теги:** Saturn, Saturn's rings, Galileo, Galileo Saturn, 1612, rings disappear, ring plane crossing, Huygens, Systema Saturnium, Cassini, Hubble, Saturn equinox, history of astronomy, telescope history, astronomy, space history, Real Story

**Закреплённый комментарий:** Galileo thought Saturn had swallowed its children. What would you have guessed in 1612 with a 20x telescope?

### S1E10 · Gemini 8 · выход 26.12.2026

**Названия:**
1. Armstrong's Worst Minutes in Orbit (34)
2. Gemini 8: The First Docking, Then a Spin Nobody Could Stop (58)
3. 3 Years Before the Moon, Armstrong Nearly Didn't Make It Home (61)

**Описание:**
```
March 16, 1966. Neil Armstrong and Dave Scott do something nobody has done before: they join two spacecraft in orbit. Minutes later the joined pair starts to roll, and it does not stop. The flight was planned for three days. They came home the same day, in the wrong ocean.

We tell it with NASA's own archive: the docking photos taken through the window at 1,000, 260, 210 and 2 feet, the photo captions, the flight director's words and the recovery photos from the Pacific.

What's new here: we checked the landing spot against the map. Two NASA accounts disagree, and only one of them can be right.

Sources
- NASA, Gemini VIII mission report and press materials (1966)
- NASA Image and Video Library, Gemini 8 photographs S66-25781, S66-18613 and related: https://images.nasa.gov/
- Gene Kranz, NASA oral history and "Failure Is Not an Option"
- NASA JSC Oral History Project: David R. Scott
- NASA podcast "Houston We Have a Podcast", Gemini 8 episode
- Our check: the splashdown position on the map.

Photos and film: NASA (public domain).

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 10 of 12
Whole season: [playlist link]
Previous: Saturn's Rings · [link]
Next: 13 Saturn V Launches · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#Gemini8 #NeilArmstrong #NASA
```
**Теги:** Gemini 8, Neil Armstrong, Dave Scott, Agena, first docking in space, Gemini program, NASA history, space history, spacecraft spin, Gene Kranz, Mission Control, 1966, Project Gemini, astronaut, Apollo 11, space race, Mission Records, Real Story

**Закреплённый комментарий:** Armstrong was 35. Three years later he commanded Apollo 11. Which moment of Gemini 8 do you think got him that seat?

### S1E11 · 13 Saturn V Launches · выход 30.12.2026

**Названия:**
1. 13 Saturn V Launches at Once (28)
2. All 13 Saturn V Launches, Side by Side, Started at T-0 (54)
3. We Synced Every Saturn V Launch. They Are Not the Same (54)

**Описание:**
```
Between 1967 and 1973 NASA launched 13 Saturn V rockets. Not one was lost, and no one was hurt on the way up. We lined up the launch film of all 13 and started them at the same instant.

Side by side, they are not the same. Some clear the tower faster, some lean, some shake. We measured each one on the film and explain what changed from flight to flight and why.

What's new here: our own frame-by-frame timing of all 13 launches from the original NASA film, synchronized at T-0.

Sources
- NASA, Saturn V Flight Manual (SA-503) and Saturn V news reference
- NASA / Marshall Space Flight Center, Saturn V launch vehicle flight evaluation reports, AS-501 to AS-513
- NASA Kennedy Space Center launch film and photographs (public domain)
- NASA Image and Video Library: https://images.nasa.gov/
- Our measurements: time to clear the tower and early climb, from the launch film.

Photos and film: NASA (public domain).

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 11 of 12
Whole season: [playlist link]
Previous: Gemini 8 · [link]
Next: Flight 1549 · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#SaturnV #Apollo #NASA
```
**Теги:** Saturn V, Saturn V launch, all Saturn V launches, Apollo, Apollo 11 launch, Skylab, moon rocket, F-1 engine, NASA history, rocket launch, launch footage, Kennedy Space Center, space history, rocket comparison, Wernher von Braun, Mission Records, Real Story

**Закреплённый комментарий:** Guess before the answer: which of the 13 cleared the tower fastest? Write your pick, no peeking.

### S1E12 · Flight 1549 · выход 02.01.2027

**Названия:**
1. Flight 1549: 208 Seconds, Real Radio (36)
2. 208 Seconds From Bird Strike to the Hudson, With the Real ATC Tape (66)
3. Could Flight 1549 Have Made It Back? We Did the Math (52)

**Описание:**
```
January 15, 2009. US Airways Flight 1549 leaves LaGuardia, flies into a flock of Canada geese and loses power in both engines. 208 seconds later the Airbus is floating on the Hudson River, and all 155 people on board get out alive.

We tell it with the real air traffic control recording and the NTSB investigation, second by second: what the pilots knew, what the controller offered, and how much time there really was.

What's new here: our own glide calculation from the recorded altitude and speed. Could they have reached LaGuardia or Teterboro? The numbers answer it.

Sources
- NTSB, Aircraft Accident Report AAR-10/03, Loss of Thrust in Both Engines After Encountering a Flock of Birds and Subsequent Ditching on the Hudson River (2010): https://www.ntsb.gov/investigations/AccidentReports/Reports/AAR1003.pdf
- FAA, air traffic control recording and transcript, US Airways 1549 (2009), via Wikimedia Commons
- NTSB public docket, flight data and cockpit voice recorder transcript
- Our calculations: altitude and distance versus time, glide reach to LaGuardia and Teterboro.

Photo and audio credits: Greg L (CC BY 2.0); FAA and NTSB (public domain). Full list with links in the pinned comment.

Chapters
[CHAPTERS: paste from the final cut's youtube.md]

Real Story · Season 1 · Episode 12 of 12
Whole season: [playlist link]
Previous: 13 Saturn V Launches · [link]

Narration: synthetic voice (Kokoro TTS). Music: generated. All photos, film, audio and recordings shown as real are original archive material; anything nobody filmed is labelled as an illustration.
Found a mistake? Tell us in the comments and we will fix it.

#Flight1549 #Aviation #NTSB
```
**Теги:** Flight 1549, US Airways 1549, Miracle on the Hudson, Sully, Chesley Sullenberger, Jeffrey Skiles, Hudson River landing, bird strike, ATC recording, air traffic control audio, NTSB, aviation history, ditching, Airbus A320, LaGuardia, Teterboro, plane crash investigation, Real Story

**Закреплённый комментарий:** All 155 people survived. If you were in that cabin and want to add a correction or a memory, we will read every reply.
