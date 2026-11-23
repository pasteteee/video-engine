"""Word lists and patterns for transcript features (English).

Small, open, hand-built lists in the spirit of LIWC-style categories. They are counts of words,
not judgements; the downstream model decides what they mean in context.
"""

from __future__ import annotations

import re

W = lambda s: frozenset(s.split())  # noqa: E731

CATEGORIES: dict[str, frozenset[str]] = {
    "pron_i": W("i i'm i've i'd i'll me my mine myself"),
    "pron_we": W("we we're we've we'd we'll us our ours ourselves"),
    "pron_you": W("you you're you've you'd you'll your yours yourself yourselves"),
    "pron_they": W("they they're they've they'd they'll them their theirs themselves"),
    "pron_he_she": W("he he's he'd he'll him his himself she she's she'd she'll her hers herself"),
    "pron_impersonal": W("it it's its this that these those something anything everything nothing someone anyone everyone"),
    "article": W("a an the"),
    "negation": W("no not never none nobody nothing neither nor nowhere can't cannot don't doesn't didn't won't wouldn't isn't aren't wasn't weren't shouldn't couldn't haven't hasn't hadn't"),
    "hedge": W("maybe perhaps possibly probably somewhat seems seem seemed apparently sort kind guess suppose think thought believe might may could arguably fairly rather quite"),
    "certainty": W("always never certainly definitely absolutely clearly obviously surely undoubtedly indeed sure certain know fact truly every all must"),
    "absolutist": W("always never all every everyone everything nothing nobody completely totally entirely whole forever constantly"),
    "filler": W("um uh er ah erm hmm"),
    "discourse_marker": W("like basically actually literally well you-know anyway okay so"),
    "posemo": W("good great best better love loved like liked happy glad hope hopeful proud wonderful excellent fine nice strong peace free freedom thank thanks grateful opportunity success win won enjoy joy beautiful safe secure prosperity prosper trust honest care caring help"),
    "negemo": W("bad worse worst hate hated fear afraid angry anger sad hurt pain problem problems crisis threat danger dangerous fail failed failure lose lost terrible awful poor poverty unemployment inflation war attack destroy wrong crime worry worried"),
    "anxiety": W("worry worried afraid fear fearful nervous anxious uncertain uncertainty risk scared"),
    "gratitude": W("thank thanks grateful gratitude appreciate appreciated"),
    "affiliation": W("together friend friends family families ally allies partner partners community share shared help support join unite united neighbor neighbors people citizens"),
    "achievement": W("achieve achieved win won success successful accomplish accomplished goal goals build built progress improve improved best lead leader leadership strong strength"),
    "power": W("control power powerful strong force forces command authority dominate lead military defense"),
    "moral": W("right wrong fair unfair justice duty honor honest truth values moral faith freedom liberty dignity responsibility"),
    "future": W("will shall going tomorrow future next soon plan plans hope ahead"),
    "past": W("was were had did been ago yesterday before previously last"),
    "insight": W("think know consider understand realize believe mean feel see recognize decide"),
    "cause": W("because cause caused reason reasons therefore thus hence why since so result effect"),
    "discrepancy": W("should would could ought need needs needed want wanted wish hope"),
    "tentative": W("maybe perhaps guess may might possibly seem seems almost somewhat if or"),
    "contrast": W("but however yet although though whereas instead rather while"),
    "inclusive": W("and with include including both also together plus"),
    "exclusive": W("but without except exclude excluding or either"),
    "number_word": W("one two three four five six seven eight nine ten hundred thousand million billion percent half dozen first second third"),
    "quantifier": W("many much more most few less least lot lots some several enough every each"),
    "time": W("now today year years time times day days moment when then while during years month months"),
    "money": W("money tax taxes dollar dollars budget pay paid cost costs price prices income spend spending deficit economy economic"),
    "social": W("people person friend family talk talked told say said ask asked meet citizens neighbor nation country"),
    "perception": W("see look looked hear heard listen feel felt watch watched seen"),
    "body_words": W("hand hands eye eyes face heart head"),
    "action_verbs": W("do make build fight work give take create bring stop start change act move"),
    "address_audience": W("you your folks friends americans ladies gentlemen everyone everybody"),
    "superlative": W("best worst greatest most least biggest highest lowest strongest"),
    "intensifier": W("very really so extremely truly incredibly highly deeply totally absolutely"),
    "politeness": W("please thank thanks sorry pardon kindly appreciate"),
    "agreement": W("yes yeah agree agreed right exactly true correct indeed absolutely"),
    "apology": W("sorry apologize apologise regret mistake"),
    "humor_markers": W("laughter laugh laughs funny joke joking kidding"),
    "question_words": W("what why how when where who which whom whose"),
}

AUX_Q = W("are is am do does did would will can could should have has had shall may might was were")
SUBJ = W("you we i they it there he she that this")

RE_NUMBER = re.compile(r"^\$?\d[\d,.]*%?$")


def tokenize(text: str) -> str:
    return re.sub(r"[^a-z0-9'$%.,?!]", "", text.lower())


def bare(tok: str) -> str:
    return tok.strip(".,?!")


def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = re.findall(r"[aeiouy]+", w)
    n = len(groups)
    if w.endswith("e") and n > 1 and not w.endswith("le"):
        n -= 1
    return max(1, n)


LEADS = W("yourself yourselves and but so well now ask then or ago today yes no okay")
FUNCTION = W("as a an the to of that than in on at for with by so if not no more less")


def question_onsets(words: list[str]) -> list[int]:
    """Token indexes where an interrogative starts. Uses '?' when the transcript has it, else
    English word order: aux + 'you' anywhere ('do you feel'), aux + subject at a clause start or
    after a lead-in ('ask yourself are you'), 'is/are' + content word at a clause start
    ('is America as respected'), or wh-word + aux."""
    ws = [bare(w) for w in words]
    out = []
    for j in range(len(ws) - 1):
        a, b = ws[j], ws[j + 1]
        prev = ws[j - 1] if j else ""
        if words[j].endswith("?"):
            out.append(j)
        elif a in AUX_Q and b in ("you", "we") and prev not in ("what", "if", "that", "who", "which", "than", "as"):
            out.append(j)
        elif a in AUX_Q and b in SUBJ and (j == 0 or prev in LEADS):
            out.append(j)
        elif j == 0 and a in ("is", "are") and b and b not in FUNCTION and b not in SUBJ:
            out.append(j)
        elif (j == 0 or prev in LEADS) and a in CATEGORIES["question_words"] and b in AUX_Q:
            out.append(j)
    # merge onsets closer than 3 tokens
    merged = []
    for j in out:
        if not merged or j - merged[-1] > 3:
            merged.append(j)
    return merged


def clause_is_question(words: list[str]) -> bool:
    return bool(question_onsets(words))
