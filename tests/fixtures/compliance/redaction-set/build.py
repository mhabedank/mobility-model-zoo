"""Build the synthetic redaction test set (items.jsonl). Every identifier is invented.

Run: uv run python tests/fixtures/compliance/redaction-set/build.py
Each item: {"text": ..., "lang": "de"|"en", "spans": [{"kind": ..., "start": ..., "end": ...}]}.
"""

import json
import random
from pathlib import Path

FIRST = ["lena", "jonas", "mia", "paul", "emma", "noah", "lea", "finn", "sara", "tom", "anna", "ben"]
LAST = ["beispiel", "muster", "probe", "testmann", "fiktiv", "erdacht", "demo", "platzhalter"]
DOMAINS = ["posteo.de", "web.de", "gmx.net", "mailbox.org", "uni-beispiel.de", "firma-fiktiv.com"]
CITIES = [("10115", "Berlin"), ("80331", "München"), ("50667", "Köln"), ("20095", "Hamburg")]
STREETS = ["Lindenstraße", "Bahnhofstr.", "Am Mühlweg", "Rosenweg", "Marktplatz", "Parkallee"]

TEMPLATES = {
    "email": [
        ("de", "Schreiben Sie mir an {x}, dann melde ich mich."),
        ("en", "Drop me a line at {x} if the bus is late again."),
        ("de", "Kontakt für Rückfragen: {x}"),
    ],
    "phone": [
        ("de", "Rufen Sie mich unter {x} an."),
        ("en", "Call me on {x} after six."),
        ("de", "Tel.: {x}"),
    ],
    "handle": [
        ("en", "Thanks to {x} for the timetable tip."),
        ("de", "Wie {x} schon schrieb, fällt der Zug aus."),
    ],
    "profile_url": [("en", "See my post at {x} for photos."), ("de", "Mein Profil: {x}")],
    "iban": [("de", "Bitte überweisen Sie an {x}."), ("en", "Refund to IBAN {x} please.")],
    "address": [("de", "Ich wohne in der {x} und warte jeden Morgen.")],
    "plate": [("de", "Mein Auto mit dem Kennzeichen {x} stand im Halteverbot.")],
}


def value(kind, r):
    f, last = r.choice(FIRST), r.choice(LAST)
    if kind == "email":
        local = r.choice([f"{f}.{last}", f"{f}{r.randint(1, 99)}", f"{f[0]}.{last}"])
        dom = r.choice(DOMAINS)
        return r.choice([f"{local}@{dom}", f"{local} @ {dom}", f"{local}@{dom.replace('.', ' .', 1)}"])
    if kind == "phone":
        return r.choice(
            [
                f"+49 30 {r.randint(1000000, 9999999)}",
                f"030 {r.randint(100000, 999999)}",
                f"0151 {r.randint(1000000, 9999999)}",
                f"+44 20 {r.randint(1000, 9999)} {r.randint(1000, 9999)}",
                f"0049 89 {r.randint(100000, 999999)}",
            ]
        )
    if kind == "handle":
        return r.choice([f"@{f}_{last}", f"u/{f}{last}", f"/u/{f}{r.randint(10, 99)}"])
    if kind == "profile_url":
        return r.choice(
            [
                f"https://www.reddit.com/user/{f}{last}",
                f"https://twitter.com/{f}_{last}",
                f"https://forum.example-bahn.de/members/{f}{last}.{r.randint(100, 999)}/",
                f"https://www.facebook.com/{f}.{last}",
            ]
        )
    if kind == "iban":
        digits = "".join(str(r.randint(0, 9)) for _ in range(18))
        return r.choice(
            [
                f"DE{digits[:2]} {digits[2:6]} {digits[6:10]} {digits[10:14]} {digits[14:18]} 00",
                f"DE{digits}00",
            ]
        )
    if kind == "address":
        plz, city = r.choice(CITIES)
        street = r.choice([s for s in STREETS if s[0].isupper() and " " not in s])
        return f"{street} {r.randint(1, 120)}, {plz} {city}"
    if kind == "plate":
        district, letters = r.choice(["B", "M", "HH", "K", "F"]), r.choice(["AB", "XY", "MM", "Q"])
        return f"{district}-{letters} {r.randint(1, 9999)}"
    raise ValueError(kind)


def build(n=300, seed=20261008):
    r = random.Random(seed)
    kinds = list(TEMPLATES)
    items = []
    for i in range(n):
        kind = kinds[i % len(kinds)]
        lang, tpl = r.choice(TEMPLATES[kind])
        x = value(kind, r)
        text = tpl.replace("{x}", x)
        start = text.index(x)
        items.append(
            {
                "text": text,
                "lang": lang,
                "spans": [{"kind": kind, "start": start, "end": start + len(x)}],
            }
        )
    return items


if __name__ == "__main__":
    out = Path(__file__).with_name("items.jsonl")
    out.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in build()), encoding="utf-8")
    print(f"wrote {out}")
