# video-engine

Движок для YouTube-каналов: от аналитики и выбора темы до публикации. Девять агентов передают друг другу файлы серии по строгим JSON-контрактам, владелец канала решает в трёх точках: тема, сценарий, финал. Каналы: Real Story (`channels/realstory`) и LoreSquare, теории и разборы One Piece (`channels/loresquare`).

План и обоснование инструментов: [Движок канала Real Story: архитектура и инструменты](https://claude.ai/artifact/E3RMnEPNdBExNCehEVBHrT).

## Что уже есть (этап 1, каркас)
| Часть | Где |
|---|---|
| Профиль канала: стиль, правила, голос, лимиты разнообразия, ключи | `channels/<id>/channel.json` |
| Контракты передач (9 схем) | `vengine/schemas/*.schema.json` |
| Проверка схем и ссылок между файлами (факты, источники, медиа, строки, кадры) | `vengine/contracts.py` |
| Библиотека из 32 типа сцен в трёх регистрах | `vengine/scenes.py` |
| Правила разнообразия монтажа | `vengine/variety.py` |
| Линтер ИИ-текста по категориям Wikipedia «Signs of AI writing» | `vengine/ailint.py` |
| Агенты | `.claude/agents/rs-*.md` |
| Оркестратор | `.claude/skills/realstory-engine/SKILL.md` |

## Канал LoreSquare (теории по манге)
Пока только генерация видео: этап `publish` выключен в профиле (`pipeline.skip`), серия заканчивается на финальном одобрении. Четыре формата, у каждого своя длина, структура и проверки (`python -m vengine formats loresquare`):

| Формат | Что это | Кадр |
|---|---|---|
| `top_theories` | Топ 3–5 теорий с сайта: автор, улики с главами, контраргумент, счёт сообщества. Каждая теория режется в отдельный шортс | 16:9, 6–10 мин |
| `chapter_breakdown` | Разбор новой главы: один вопрос, мотивы, замысел автора, setup→payoff, теория, прогноз | 16:9, 8–14 мин |
| `chapter_moments` | 3–5 моментов последних глав, которые выстрелят в сюжете или двигают загадку сайта | 16:9, 4–7 мин |
| `site_promo` | Одна функция LoreSquare на живом сайте с реальной теорией | 9:16, 30–45 с |

Что проверяет движок: глава вышла официально (`topic.release`, дата не в будущем), кадры манги только из вышедших глав, не больше трети ролика, по 3–5 с, с нашим комментарием и никогда два подряд; пересказ не больше 20 % в разборах; каждое утверждение помечено как канон, вывод, теория или мнение сообщества; у формата есть все обязательные блоки сценария. Данные сайта: `python -m vengine lore top --channel loresquare` или коннектор LoreSquare. Стиль «Тушь»: `channels/loresquare/brand/STYLEGUIDE.md`, компоненты `channels/loresquare/kit/`.

## Команды
```bash
pip install -r requirements.txt
python -m vengine channels
python -m vengine init realstory bloop --root ./episodes
python -m vengine init loresquare ch1193 --format chapter_breakdown
python -m vengine formats loresquare
python -m vengine lore top --channel loresquare --n 5 --out ./top.json
python -m vengine status ./episodes/bloop
python -m vengine validate ./episodes/bloop
python -m vengine variety ./episodes/bloop/04_shots/shotlist.json --channel realstory
python -m vengine variety <ep>/04_shots/shotlist.json --channel loresquare --format top_theories
python -m vengine ailint ./episodes/bloop/03_script/script.json
python -m vengine approve ./episodes/bloop script --note "ок, но убрать вторую цитату"
python -m pytest -q
```

## Папка серии
```
01_topic/topic_card.json      тема, сигналы спроса, общеизвестный слой, угол
02_research/findings.json     источники, факты со статусами, свои расчёты, выводы
02_research/media.json        фото/видео/документы с лицензиями и тем, что в кадре
03_script/script.json         строки, эмоции и подача для голоса, крючки, факты
04_shots/shotlist.json        покадровый план: тип сцены, медиа, движение, звук
05_voice/words.json           тайминг слов озвучки
06_render/                    main.mp4, шортсы, обложки
07_qa/qa_report.json          проверки, замечания с таймкодами, вердикт
08_publish/publish.json       что и куда загружено
state.json                    одобрения владельца
```

## Новый канал
Скопировать `channels/realstory/` в `channels/<id>/`, поменять стиль, правила, голос, папку ключей и лимиты. Несколько видов роликов на канале описываются в `formats`, свои типы сцен подключаются через `scene_domains`. Код движка не трогать.

## Дальше
Этап 2: YouTube (аналитик и публикатор). Этап 3: темы и планер. Этап 4: исследователь и сценарист. Этап 5: монтаж v2 (компоненты 32 сцен, Gemini Image + Veo). Этап 6: озвучка и QA. Этап 7: пилотная серия.
