"""Linter for AI-sounding narration (English).

Based on the categories of the Wikipedia editors' guide "Wikipedia:Signs of AI writing"
(https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing). The phrase lists below
were written from that guide's categories and examples; the cloud container cannot
reach Wikipedia, so re-sync them with the live page from a machine that can
(`python -m vengine ailint --print-rules` shows what is checked).

Lexical signs are caught by regex. Structural signs (rule of three, monotone sentence
length, "not X but Y" parallelisms, participle tails) are caught by heuristics and
reported as warnings for the writer's second pass.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import mean, pstdev


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    pattern: str
    level: str  # error = rewrite, warn = look again
    why: str     # shown to the writer, Russian
    fix: str


def _words(*ws: str) -> str:
    return r"\b(?:" + "|".join(ws) + r")\b"


RULES: list[Rule] = [
    Rule("ai-vocab", "AI vocabulary", _words(
        "delve[sd]?", "delving", "tapestry", "intricate", "intricacies", "interplay", "multifaceted",
        "testament", "pivotal", "paramount", "meticulous(?:ly)?", "underscore[sd]?", "underscoring",
        "showcas(?:e|es|ed|ing)", "foster(?:s|ed|ing)?", "garner(?:s|ed)?", "bolster(?:s|ed)?",
        "realm", "embark(?:s|ed)?", "beacon", "unwavering", "commendable", "seamless(?:ly)?",
        "nuanced", "resonate[sd]?", "harness(?:es|ed)?", "elevate[sd]?", "enduring", "vibrant",
        "boasts?", "noteworthy", "invaluable", "ever-evolving", "game-?changer"),
        "error", "Слово из списка, которое модели используют намного чаще людей.",
        "Скажи проще и конкретнее: что именно произошло, какое число, кто."),
    Rule("significance", "Undue emphasis on significance or legacy",
         r"\b(?:stands? as|serves? as a (?:reminder|symbol|testament)|a testament to|plays? an? (?:vital|crucial|pivotal|key|significant) role|"
         r"(?:key|pivotal|critical) (?:moment|turning point)|indelible mark|left (?:a|an) (?:lasting|indelible) (?:mark|legacy)|"
         r"marks? a (?:significant|pivotal)|reflects? (?:the )?broader|setting the stage for|"
         r"evolving landscape|in the (?:broader|wider) context|deeply rooted|cemented (?:its|his|her|their) place)\b",
         "error", "Раздувание значимости: так пишут, когда нечего сказать по фактам.",
         "Убери оценку и покажи факт, из которого значимость видна сама."),
    Rule("promo", "Promotional language",
         r"\b(?:rich (?:cultural )?(?:heritage|history|tapestry)|nestled|in the heart of|breathtaking|stunning|"
         r"must-see|renowned|world-class|groundbreaking|captivating|awe-inspiring|diverse array|natural beauty|"
         r"commitment to)\b",
         "error", "Рекламный тон, на канале документальной честности он режет слух.",
         "Замени описанием: размер, время, что видно на подлинном кадре."),
    Rule("editorial", "Editorializing",
         r"\b(?:it(?:'s| is) (?:important|worth|crucial) (?:to note|noting|to remember|to mention)|"
         r"it should be noted|notably|interestingly|importantly|needless to say|it goes without saying)\b",
         "error", "Рассказчик объясняет зрителю, что важно, вместо того чтобы показать.",
         "Удали вводную, оставь сам факт; акцент сделает голос."),
    Rule("connectives", "Overused connectives",
         r"(?:^|[.!?]\s+)(?:Moreover|Furthermore|Additionally|In addition|Consequently|Thus|Hence|Indeed)\b",
         "warn", "Канцелярские связки в начале фразы, в устной речи так не говорят.",
         "Начни фразу с действия или числа; связь передаст монтаж."),
    Rule("summary", "Section summaries",
         r"(?:^|[.!?]\s+)(?:In (?:summary|conclusion)|Overall|Ultimately|In essence|All in all|To sum up)\b",
         "error", "Шаблонный итог абзаца.", "Закончи сильным фактом или вопросом, без подведения итогов."),
    Rule("participle-tail", "Superficial analysis with -ing tails",
         r",\s+(?:highlighting|underscoring|emphasizing|reflecting|symbolizing|showcasing|illustrating|"
         r"demonstrating|contributing to|ensuring|cementing|signaling|marking)\b",
         "error", "Хвост на -ing после запятой: пустой «анализ», типичный для модели.",
         "Отрежь хвост или сделай из него отдельную фразу с конкретикой."),
    Rule("vague-attribution", "Vague attributions",
         r"\b(?:experts (?:say|agree|believe|argue|note)|(?:many|some) (?:say|believe|argue)|"
         r"observers (?:have )?(?:noted|cited)|is widely (?:regarded|considered|seen)|"
         r"has been described as|researchers (?:have )?(?:found|suggest)(?! that \w+ \d))\b",
         "error", "Ссылка на безымянных экспертов. На канале каждая мысль имеет источник.",
         "Назови кого именно и где: отчёт, стенограмма, имя."),
    Rule("negative-parallel", "Negative parallelism",
         r"\b(?:not only\b.{0,60}\bbut(?: also)?|it(?:'s| is| was) not (?:just|only|merely)\b.{0,60}[,;—-]\s*it(?:'s| is| was)|"
         r"isn't just\b|wasn't just\b|not because\b.{0,50}\bbut because)\b",
         "warn", "Конструкция «не просто X, а Y» — самый узнаваемый приём ИИ-текста.",
         "Скажи прямо, что это было. Одна такая фраза на серию максимум."),
    Rule("challenges", "Challenges and future prospects",
         r"\b(?:despite (?:these|its|the) challenges|faces? (?:several|numerous|many) challenges|"
         r"future (?:prospects|remains)|continues? to (?:thrive|evolve|inspire|captivate)|remains? to be seen)\b",
         "error", "Шаблон «несмотря на трудности… продолжает…».", "Расскажи, что конкретно известно сейчас, с датой."),
    Rule("chatbot", "Chatbot artefacts",
         r"\b(?:as an AI|I hope this helps|let me know|certainly!|great question|as of my (?:last )?(?:knowledge|training)|"
         r"here(?:'s| is) (?:a|the) (?:script|breakdown)|feel free to)\b",
         "error", "Остаток ответа чат-бота.", "Удалить."),
    Rule("youtube-cliche", "YouTube narration cliches (channel rule)",
         r"\b(?:buckle up|let(?:'s| us) dive in|dive (?:deep )?into|little did (?:they|he|she|we) know|"
         r"the answer (?:may|will) (?:surprise|shock) you|you won't believe|in a world where|"
         r"journey|fascinating|mind-?blowing|without further ado|stay tuned|smash (?:that|the) like)\b",
         "warn", "Затёртый оборот ютуб-рассказчиков, звучит дёшево.",
         "Крючок делай фактом: время, число, цитата, деталь кадра."),
]

_SENT = re.compile(r"[^.!?]+[.!?]?")
_TRIPLET = re.compile(r"\b(\w+(?:\s\w+)?),\s(\w+(?:\s\w+)?),?\s(?:and|or)\s(\w+)\b", re.I)


def lint_text(text: str) -> list[dict]:
    hits = []
    for r in RULES:
        for m in re.finditer(r.pattern, text, flags=re.I | re.M):
            hits.append({"rule": r.id, "level": r.level, "match": m.group(0).strip(" ,"),
                         "why": r.why, "fix": r.fix})
    return hits


def lint_lines(lines: list[dict]) -> dict:
    """lines: [{'id','text'}]. Returns per-line hits plus whole-script structural checks."""
    per_line, total_words = [], 0
    full = " ".join(l["text"] for l in lines)
    for l in lines:
        h = lint_text(l["text"])
        total_words += len(l["text"].split())
        if h:
            per_line.append({"line_id": l["id"], "text": l["text"], "hits": h})

    structural = []
    w100 = max(total_words, 1) / 100

    dashes = full.count("—") + full.count(" - ") + full.count("--")
    if dashes / w100 > 1.0:
        structural.append({"rule": "em-dash", "level": "warn",
                           "msg": f"{dashes} тире на {total_words} слов: у моделей тире вдвое чаще, чем у людей. Замени часть точками."})

    triplets = _TRIPLET.findall(full)
    if len(triplets) / w100 > 0.5:
        structural.append({"rule": "rule-of-three", "level": "warn",
                           "msg": f"{len(triplets)} перечислений по три ({'; '.join(', '.join(t) for t in triplets[:3])}…). "
                                  "Правило трёх выдаёт модель. Оставь два пункта или один, но точный."})

    sents = [s.strip() for s in _SENT.findall(full) if len(s.split()) >= 3]
    if len(sents) >= 8:
        lens = [len(s.split()) for s in sents]
        cv = pstdev(lens) / mean(lens)
        if cv < 0.35:
            structural.append({"rule": "monotone-length", "level": "warn",
                               "msg": f"Фразы почти одной длины (разброс {cv:.2f}). Живая речь чередует 3 слова и 20."})
        starts = [s.split()[0].lower() for s in sents]
        common = max(set(starts), key=starts.count)
        if starts.count(common) / len(starts) > 0.25:
            structural.append({"rule": "same-opener", "level": "warn",
                               "msg": f"{starts.count(common)} фраз начинаются с «{common}»."})

    errors = sum(1 for p in per_line for h in p["hits"] if h["level"] == "error")
    warns = sum(1 for p in per_line for h in p["hits"] if h["level"] == "warn") + len(structural)
    return {"words": total_words, "errors": errors, "warnings": warns,
            "ok": errors == 0, "lines": per_line, "structural": structural}


def format_report(rep: dict) -> str:
    out = [f"Слов: {rep['words']}. Ошибок: {rep['errors']}, предупреждений: {rep['warnings']}."]
    for p in rep["lines"]:
        out.append(f"\n[{p['line_id']}] {p['text']}")
        for h in p["hits"]:
            out.append(f"  {'✗' if h['level'] == 'error' else '!'} «{h['match']}»: {h['why']} → {h['fix']}")
    for s in rep["structural"]:
        out.append(f"\n! {s['msg']}")
    return "\n".join(out)
