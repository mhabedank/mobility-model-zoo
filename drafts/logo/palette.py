"""The poster identity as a full token set, with every pair that carries meaning checked.

Day print on paper, night print on navy. The one warm accent stays rare: links are a deep
blue-green, not orange, so that orange keeps meaning "this is the thing that matters".
Information graphics need more hues than a brand palette, so s-a/s-b/s-c and the job/pain/gain
pairs form a documented data-ink extension instead of being improvised per graphic.
"""

LIGHT = {
    "bg": "#F8F3E6", "surface": "#FFFCF4", "surface-2": "#F0E8D5",
    "text": "#062544", "muted": "#4A5A52", "border": "#D9CDB2", "border-strong": "#7D8C82",
    "link": "#0B4A70", "link-hover": "#062544", "focus": "#A8500C",
    "accent": "#062544", "on-accent": "#FBEED0", "mark": "#CA6A0A", "code-bg": "#F0E8D5",
    "job-bg": "#DCE9F2", "job-ink": "#0B4A70",
    "pain-bg": "#F9E3C4", "pain-ink": "#8A4310",
    "gain-bg": "#D8ECDC", "gain-ink": "#1C5E3F",
    "s-a": "#0B4A70", "s-b": "#5F8E8A", "s-c": "#A8500C",
}
DARK = {
    "bg": "#041C33", "surface": "#062544", "surface-2": "#0B3050",
    "text": "#FBEED0", "muted": "#A5DBC6", "border": "#17496F", "border-strong": "#6C928C",
    "link": "#8FC8E8", "link-hover": "#CDE8F6", "focus": "#ED9B20",
    "accent": "#ED9B20", "on-accent": "#062544", "mark": "#ED9B20", "code-bg": "#041C33",
    "job-bg": "#0E3C5C", "job-ink": "#9FD0EA",
    "pain-bg": "#6B3A0E", "pain-ink": "#F5C07A",
    "gain-bg": "#14452F", "gain-ink": "#9BD4A6",
    "s-a": "#86B6D8", "s-b": "#A5DBC6", "s-c": "#ED9B20",
}

# (foreground, background, minimum, what it is)
PAIRS = [
    ("text", "bg", 4.5, "Flie&szlig;text auf der Seite"),
    ("text", "surface", 4.5, "Text auf Karten"),
    ("text", "surface-2", 4.5, "Text auf abgesetzten Fl&auml;chen"),
    ("text", "code-bg", 4.5, "Code"),
    ("muted", "bg", 4.5, "Sekund&auml;rtext"),
    ("muted", "surface", 4.5, "Sekund&auml;rtext auf Karten"),
    ("link", "bg", 4.5, "Links"),
    ("link", "surface", 4.5, "Links auf Karten"),
    ("on-accent", "accent", 4.5, "Knopfbeschriftung"),
    ("job-ink", "job-bg", 4.5, "Chip job"),
    ("pain-ink", "pain-bg", 4.5, "Chip pain"),
    ("gain-ink", "gain-bg", 4.5, "Chip gain"),
    ("focus", "bg", 3.0, "Fokusring"),
    ("border-strong", "bg", 3.0, "starke Rahmen"),
    ("mark", "bg", 3.0, "Akzentelemente"),
    ("s-a", "bg", 3.0, "Serie A"),
    ("s-b", "bg", 3.0, "Serie B"),
    ("s-c", "bg", 3.0, "Serie C"),
]


def lum(h: str) -> float:
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a: str, b: str) -> float:
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def report(name: str, p: dict) -> int:
    print(f"\n=== {name} ===")
    bad = 0
    for fg, bg, need, what in PAIRS:
        r = ratio(p[fg], p[bg])
        ok = r >= need
        bad += 0 if ok else 1
        flag = "   " if ok else " ->"
        print(f"{flag} {what:34} {fg:14} auf {bg:11} {r:5.2f}:1  (mind. {need})")
    return bad


if __name__ == "__main__":
    bad = report("Tagdruck (hell)", LIGHT) + report("Nachtdruck (dunkel)", DARK)
    print(f"\n{bad} Paare unter der Schwelle." if bad else "\nAlle Paare bestehen.")
