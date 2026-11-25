# video-engine

Движок для YouTube-каналов: от аналитики и выбора темы до публикации. Девять агентов передают друг другу файлы серии по строгим JSON-контрактам, владелец канала решает в трёх точках: тема, сценарий, финал. Каналы: Real Story (`channels/realstory`, документальные ролики с озвучкой) и amigurumi.ai (`channels/amigurumi`, шортсы «игрушка вяжется петля за петлёй», формат `build_short`).

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
| Кадр как у студийного фото | объектив 18°, в конце уровень глаз; игрушка стоит на полу с мягкой тенью и занимает около 70% безопасной зоны между подписями |
| Крючок в кадре | `grow --hook`: 3D-крючок толщиной из спеки (`yarn.hook_mm`) с рабочей нитью цвета текущей детали (`vengine/yarn/hook.py`). Пока ряды идут медленно, кончик крючка сидит на последней петле; когда ряд пролетает быстрее ~10° за кадр, крючок держится на краю ряда со стороны камеры и ныряет в ритме петель (как вязальщица, которая крутит деталь, а не крючок). Между деталями приподнимается, перед мордочкой уходит из кадра |
| Финал в ракурсе фото | `python -m vengine yarn match SPEC.json PHOTO --out match.json --sheet look.jpg` вырезает игрушку с фото и подбирает азимут и наклон по совпадению силуэтов (IoU); `grow --view match.json --rest S` останавливает разворот в этом ракурсе к секунде S и пишет его в `plan.json` (`final`). Монтаж (`vengine build`) делает это сам, если в раскадровке есть `photos.real`, и открывает «в жизни» наплывом 0,5 с из последнего кадра вязания в фото, совмещённое по силуэту |

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

## Шортсы амигуруми (формат build_short)
Ролик 30 с без голоса: крючок (студийное фото, имя игрушки) → игрушка вяжется по настоящей схеме из спеки amikit, всё быстрее, с подписями «Magic ring», «Increase», «+ head»… → «Done!» → фото вживую → CTA amigurumi.ai. Подписи, счётчик петель, чип скорости и музыка (тики петель, дроп на «Done!») считаются из одного `plan.json` вязания, поэтому всегда совпадают.

| Что | Где |
|---|---|
| Профиль канала, цвета, шрифты, тайминг, CTA, рендер вязания | `channels/amigurumi/channel.json`, `brand/BRANDBOOK.md` |
| Раскадровка шортса (схема `storyboard`) | `04_shots/storyboard.json` |
| Контракт рендера вязания (схема `knit_plan`) | `06_render/knit/plan.json` + `0000.png…` |
| Подписи, события музыки, текст рядов | `vengine/build/storyboard.py` |
| Точка подключения рендера вязания | `vengine/build/knit.py` (`auto` / `crochetsim` / `yarn` / `command`) |
| Композитор кадра | `vengine/build/comp.py` |
| Музыка и звуки петель (numpy) | `vengine/build/audio.py` |
| Каталог моделей: поиск, инфо, 3D-просмотр, загрузка в серию | `vengine/catalog.py`, `catalog` в channel.json |
| Агент | `.claude/agents/rs-build.md` |

```bash
python -m vengine catalog search amigurumi goat       # модели каталога amigurumi.ai
python -m vengine catalog info amigurumi goat-sweater-2027      # размер, часы, крючок, пряжа и метры по цветам, ссылки
python -m vengine catalog view amigurumi goat-sweater-2027      # HTML: крутящаяся 3D-модель + инфо
python -m vengine init amigurumi goat-sweater-2027    # папка серии
python -m vengine catalog pull <episode> goat-sweater-2027      # спека, GLB, фото, toy_info.json, черновик раскадровки
python -m vengine validate <episode>
python -m vengine build knit <episode> --jobs 8       # кадры вязания, можно продолжить после обрыва
python -m vengine build still <episode> --at 0.8,3,8,12,16,18,21,26
python -m vengine build all <episode>                 # mp4 + обложка Shorts + превью YouTube + лист кадров
```
Флаги рендера для одной серии лежат в раскадровке: `"knit": {"hook": true, "size": "810x1440", "ss": 2, "mblur": 2}` (крючок в кадре; вязание считается в 810x1440 и масштабируется в 1080x1920, так рендер почти в два раза быстрее).
Для рендера вязания нужны numba и scipy, пакет crochetsim (`build.knit.src` или `CROCHETSIM_SRC`) и amikit (`AMIKIT`).

## Новый канал
Скопировать `channels/realstory/` в `channels/<id>/`, поменять стиль, правила, голос, папку ключей и лимиты. Код движка не трогать.

## Дальше
Этап 2: YouTube (аналитик и публикатор). Этап 3: темы и планер. Этап 4: исследователь и сценарист. Этап 5: монтаж v2 (компоненты 32 сцен, Gemini Image + Veo). Этап 6: озвучка и QA. Этап 7: пилотная серия.
