# video-engine

Движок для YouTube-каналов: от аналитики и выбора темы до публикации. Девять агентов передают друг другу файлы серии по строгим JSON-контрактам, владелец канала решает в трёх точках: тема, сценарий, финал. Первый канал: Real Story (`channels/realstory`).

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

## Пряжа: анимация вязания игрушки (`vengine/yarn`)
Кадры роста игрушки петля за петлёй из выкройки amikit: `python -m vengine yarn grow SPEC.json OUT --size 1080x1920 --dur 16 --reveal 3.5 [--frames a:b]` пишет `OUT/%04d.png` и `OUT/plan.json` (раунды, детали, прогресс для подписей и звука). Уже готовые кадры пропускаются, поэтому рендер можно продолжать и делить на куски. Нужны `pip install -r requirements-yarn.txt` и папка с amikit в `$AMIKIT`.

| Что | Как |
|---|---|
| Нет ряби и дёрганья цвета | текстура и цвет привязаны к длине нити, а не к пикселям экрана; детали мельче 2 px плавно гаснут; AO и пух без случайного шума; карта теней прикреплена к игрушке; сглаживание 3×3 с гауссом |
| Цветные зоны выкройки | цвет каждой петли из `toy.chart` amikit (мордочки, полоски, края шапок) |
| Плавная анимация | кончик нити плавно «наматывается», камера сглажена и не наезжает на мелкие детали, скорость поворота ограничена по сдвигу в пикселях, финальный разворот без скачка скорости, размытие движения при быстрых кадрах |
| Проверка | `python -m vengine yarn probe SPEC.json OUT` считает мерцание (вторая разность соседних кадров) |

## Команды
```bash
pip install -r requirements.txt
python -m vengine channels
python -m vengine init realstory bloop --root ./episodes
python -m vengine status ./episodes/bloop
python -m vengine validate ./episodes/bloop
python -m vengine variety ./episodes/bloop/04_shots/shotlist.json --channel realstory
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
Скопировать `channels/realstory/` в `channels/<id>/`, поменять стиль, правила, голос, папку ключей и лимиты. Код движка не трогать.

## Дальше
Этап 2: YouTube (аналитик и публикатор). Этап 3: темы и планер. Этап 4: исследователь и сценарист. Этап 5: монтаж v2 (компоненты 32 сцен, Gemini Image + Veo). Этап 6: озвучка и QA. Этап 7: пилотная серия.
