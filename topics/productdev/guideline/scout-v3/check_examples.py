"""Check the worked examples of guideline v3 against brief.yaml.

Usage: uv run python topics/productdev/guideline/scout-v3/check_examples.py

Checks, per example and item:
- every quote, executor_role and situation is a verbatim substring of the text;
- every quote occurs exactly once, has no edge whitespace or punctuation, and
  quotes of one example do not overlap;
- every enum and list value is valid against brief.yaml;
- links use the {from, to, relation} encoding, point to existing items and use
  a relation listed under the link field in brief.yaml;
- relevant is true if and only if the example has items;
- job_kind is set on jobs and only on jobs;
- executor_role and situation do not start with an article, possessive,
  demonstrative or preposition, and executor_role is not a generic word
  (Fable review 2, M-7 and M-8);
- society is used only when the quote has a word for everyone (M-6);
- states_solution is true only on gains (M-4);
- link_connectives in brief.yaml is a closed list for every link field (M-2).

Prints the distributions of kind, actor_type, evidence_type and evidence_scope.
Exits with status 1 if any error is found. Reads no file outside this folder.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent

# Keys of a brief section that are not enum values.
META = {
    "drafted_by",
    "approval",
    "previous_approval",
    "owner",
    "owner_en",
    "owner_choice",
    "rule",
    "values",
    "boundaries",
    "applies_to",
}
NON_VALUES = {
    "kind": META | {"job_versus_gain", "feelings", "pain_versus_negated_gain"},
    "actor_type": META,
    "evidence_type": META | {"reported_speech", "same_need_twice"},
    "evidence_scope": META,
    "job_kind": META,
}
ITEM_KEYS = [
    "id",
    "kind",
    "quote",
    "actor_type",
    "evidence_type",
    "evidence_scope",
    "job_kind",
    "executor_role",
    "situation",
    "mode",
    "improve",
    "states_solution",
]
LINK_FIELDS = ["actor_pair", "means_end", "order"]
EDGE_CHARS = " \t\n.,;:!?"

# First words a pointer must not start with (M-7: no article, possessive,
# demonstrative or preposition). Lower case, English and German.
POINTER_LEADS = set(
    (
        "a an the this that these those my our your his her its their at by for from in"
        " into of on to with every each"
        " der die das den dem des ein eine einen einem einer eines mein meine meinen"
        " meinem meiner meines unser unsere unseren unserem unserer unseres ihr ihre"
        " ihren ihrem ihrer ihres sein seine seinen seinem seiner seines dieser diese"
        " dieses diesem diesen jener jene jenes jenem jenen solche solchen solcher"
        " solches solchem jeden jede jedes jedem jeder am auf aus bei beim im mit nach"
        " von vom vor zu zum zur"
    ).split()
)
# Generic words that get no role (M-8).
GENERIC_ROLES = set("i we people members leute ich wir man you one".split())
# Words for everyone that society needs in the quote (M-6).
SOCIETY_WORDS = set("alle allen allgemeinheit everyone everybody public".split())


def enum_values(brief: dict, field: str) -> set[str]:
    section = brief[field]
    return {k for k in section if k not in NON_VALUES[field]}


def main() -> int:
    brief = yaml.safe_load((HERE / "brief.yaml").read_text(encoding="utf-8"))
    examples = yaml.safe_load((HERE / "examples.yaml").read_text(encoding="utf-8"))["examples"]

    enums = {f: enum_values(brief, f) for f in NON_VALUES}
    lists = {"mode": set(brief["mode"]["values"]), "improve": set(brief["improve"]["values"])}
    relations = {f: set(brief[f]["values"]) for f in LINK_FIELDS}
    expected = {
        "kind": {"job", "pain", "gain"},
        "actor_type": {"individual", "worker", "organization", "public_sector", "society"},
        "evidence_type": {"opinion", "anecdote", "routine", "observation", "measurement"},
        "evidence_scope": {"single", "multiple", "quantified"},
        "job_kind": {"functional", "emotional", "social"},
    }

    errors: list[str] = []
    for field, values in enums.items():
        if values != expected[field]:
            errors.append(f"brief.yaml: {field} values read as {sorted(values)}")
    connectives = brief.get("link_connectives") or {}
    for field in LINK_FIELDS:
        words = connectives.get(field)
        if not isinstance(words, list) or not words or not all(isinstance(x, str) for x in words):
            errors.append(f"brief.yaml: link_connectives.{field} is not a closed list of words")

    seen_ids: set[str] = set()
    all_items: list[dict] = []
    lang_count: Counter = Counter()
    for ex in examples:
        eid = ex.get("id", "?")
        where = f"{eid}"
        if eid in seen_ids:
            errors.append(f"{where}: duplicate example id")
        seen_ids.add(eid)
        text = ex["text"]
        lang = ex.get("language")
        lang_count[lang] += 1
        if lang not in {"de", "en"}:
            errors.append(f"{where}: language {lang!r}")
        if "shows" not in ex:
            errors.append(f"{where}: missing shows")
        items = ex.get("items") or []
        if ex.get("relevant") is not (len(items) > 0):
            errors.append(f"{where}: relevant={ex.get('relevant')} but {len(items)} items")

        spans: list[tuple[int, int, str]] = []
        by_id: dict[str, dict] = {}
        for it in items:
            iid = it.get("id", "?")
            w = f"{where} {iid}"
            if list(it.keys()) != ITEM_KEYS:
                errors.append(f"{w}: keys {list(it.keys())}")
            if iid in by_id:
                errors.append(f"{w}: duplicate item id")
            by_id[iid] = it
            q = it.get("quote") or ""
            n = text.count(q) if q else 0
            if n == 0:
                errors.append(f"{w}: quote not in text: {q!r}")
            elif n > 1:
                errors.append(f"{w}: quote occurs {n} times")
            else:
                start = text.index(q)
                spans.append((start, start + len(q), iid))
            if q and (q[0] in EDGE_CHARS or q[-1] in EDGE_CHARS):
                errors.append(f"{w}: edge whitespace or punctuation in quote {q!r}")
            for field in ("kind", "actor_type", "evidence_type", "evidence_scope"):
                if it.get(field) not in enums[field]:
                    errors.append(f"{w}: {field}={it.get(field)!r}")
            if it.get("kind") == "job":
                if it.get("job_kind") not in enums["job_kind"]:
                    errors.append(f"{w}: job without valid job_kind ({it.get('job_kind')!r})")
            elif it.get("job_kind") is not None:
                errors.append(f"{w}: job_kind on a {it.get('kind')}")
            for field in ("executor_role", "situation"):
                v = it.get(field)
                if v is not None and (not isinstance(v, str) or v not in text):
                    errors.append(f"{w}: {field} not in text: {v!r}")
                if isinstance(v, str) and v.split():
                    if v.split()[0].lower() in POINTER_LEADS:
                        errors.append(f"{w}: {field} starts with a determiner or preposition: {v!r}")
                    if field == "executor_role" and v.lower() in GENERIC_ROLES:
                        errors.append(f"{w}: generic word as executor_role: {v!r}")
            if it.get("actor_type") == "society":
                tokens = {t.strip(".,;:!?'\"").lower() for t in q.split()}
                if not tokens & SOCIETY_WORDS:
                    errors.append(f"{w}: society without a word for everyone in the quote")
            if it.get("states_solution") is True and it.get("kind") != "gain":
                errors.append(f"{w}: states_solution true on a {it.get('kind')}")
            for field in ("mode", "improve"):
                v = it.get(field)
                if not isinstance(v, list):
                    errors.append(f"{w}: {field} is not a list")
                    continue
                bad = [x for x in v if x not in lists[field]]
                if bad:
                    errors.append(f"{w}: {field} values {bad}")
                if len(set(v)) != len(v):
                    errors.append(f"{w}: duplicate {field} values")
            if not isinstance(it.get("states_solution"), bool):
                errors.append(f"{w}: states_solution not boolean")
            all_items.append({**it, "_lang": lang})

        spans.sort()
        for (_s1, e1, a), (s2, _e2, b) in zip(spans, spans[1:], strict=False):
            if s2 < e1:
                errors.append(f"{where}: quotes {a} and {b} overlap")

        links = ex.get("links")
        if not isinstance(links, dict) or sorted(links) != sorted(LINK_FIELDS):
            errors.append(f"{where}: links must have exactly {LINK_FIELDS}")
            continue
        for field in LINK_FIELDS:
            for link in links[field] or []:
                w = f"{where} {field} {link}"
                if not isinstance(link, dict) or sorted(link) != ["from", "relation", "to"]:
                    errors.append(f"{w}: not {{from, to, relation}}")
                    continue
                a, b = link["from"], link["to"]
                if a not in by_id or b not in by_id:
                    errors.append(f"{w}: unknown item")
                    continue
                if a == b:
                    errors.append(f"{w}: self link")
                if link["relation"] not in relations[field]:
                    errors.append(f"{w}: relation {link['relation']!r}")
                if field == "actor_pair":
                    if by_id[b]["kind"] != "pain":
                        errors.append(f"{w}: target is not a pain")
                    if by_id[a]["actor_type"] == by_id[b]["actor_type"] and (
                        by_id[a]["executor_role"] == by_id[b]["executor_role"]
                    ):
                        errors.append(f"{w}: same actor on both ends")
                if field == "means_end" and by_id[a]["actor_type"] != by_id[b]["actor_type"]:
                    errors.append(f"{w}: actor types differ")
                if field == "order" and link["relation"] == "during":
                    if text.index(by_id[a]["quote"]) > text.index(by_id[b]["quote"]):
                        errors.append(f"{w}: during must start from the earlier quote")

    n = len(all_items)
    empties = sum(1 for ex in examples if not ex.get("items"))
    print(f"examples: {len(examples)} ({dict(lang_count)}), empty: {empties}, items: {n}")
    for field in ("kind", "actor_type", "evidence_type", "evidence_scope"):
        c = Counter(it[field] for it in all_items)
        dist = ", ".join(f"{k} {v} ({100 * v / n:.0f} %)" for k, v in c.most_common())
        print(f"{field}: {dist}")
    for lang in ("de", "en"):
        c = Counter(it["actor_type"] for it in all_items if it["_lang"] == lang)
        print(f"actor_type [{lang}]: {dict(c.most_common())}")
    ss = sum(1 for it in all_items if it["states_solution"])
    print(f"states_solution true: {ss}")
    links = Counter(f for ex in examples for f in LINK_FIELDS for _ in ex["links"][f])
    print(f"links: {dict(links)}")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\n0 errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
