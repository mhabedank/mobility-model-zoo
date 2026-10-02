"""A tiny random span model built without network access (feature 004, T011).

Encoder: XLM-RoBERTa architecture with hidden size 32, 2 layers, 2 heads. Tokenizer: a word-level
tokenizer trained on a few German and English sentences, with offsets. Weights are random with a
fixed seed, so outputs are deterministic but meaningless.
"""

from __future__ import annotations

from pathlib import Path

import torch

from mobility_model_zoo.productdev.jtbd.span.extractor import SpanExtractor, default_config
from mobility_model_zoo.productdev.jtbd.span.model import ATTRIBUTE_LABELS, SpanTagger

SENTENCES = [
    "Im Landkreis fährt der letzte Bus um 18 Uhr.",
    "Wer abends aus der Stadt zurück will, muss ein Taxi nehmen.",
    "Ich pendle jeden Tag 40 Kilometer zur Arbeit, weil es keine andere Verbindung gibt.",
    "The charger at the depot was broken again; we lost two hours.",
    "Drivers want to plan their breaks around charging.",
    "63% of respondents said the app is too slow.",
]

ALL = tuple(ATTRIBUTE_LABELS)


def tiny_tokenizer():
    from tokenizers import Tokenizer, models, pre_tokenizers, trainers
    from transformers import PreTrainedTokenizerFast

    tok = Tokenizer(models.WordLevel(unk_token="<unk>"))
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    trainer = trainers.WordLevelTrainer(special_tokens=["<s>", "<pad>", "</s>", "<unk>"])
    tok.train_from_iterator(SENTENCES, trainer)
    return PreTrainedTokenizerFast(
        tokenizer_object=tok, bos_token="<s>", eos_token="</s>", cls_token="<s>",
        sep_token="</s>", pad_token="<pad>", unk_token="<unk>")


def tiny_extractor(dimensions: tuple[str, ...] = ALL, seed: int = 7,
                   thresholds: dict | None = None) -> SpanExtractor:
    from transformers import XLMRobertaConfig

    tokenizer = tiny_tokenizer()
    config = XLMRobertaConfig(
        vocab_size=len(tokenizer), hidden_size=32, num_hidden_layers=2, num_attention_heads=2,
        intermediate_size=64, max_position_embeddings=520, pad_token_id=tokenizer.pad_token_id,
        bos_token_id=tokenizer.bos_token_id, eos_token_id=tokenizer.eos_token_id)
    torch.manual_seed(seed)
    model = SpanTagger.from_config(config, {d: ATTRIBUTE_LABELS[d] for d in dimensions})
    extra = {"model": "tiny-fixture"}
    if thresholds is not None:
        extra["thresholds"] = thresholds
    return SpanExtractor(model, tokenizer, default_config(**extra))


def build_tiny_model(directory: Path, dimensions: tuple[str, ...] = ALL, seed: int = 7,
                     thresholds: dict | None = None) -> Path:
    # Low thresholds so the random model returns items to check.
    tiny_extractor(dimensions, seed, thresholds or {"unit": 0.0, "relevance": 0.0}) \
        .save_pretrained(directory)
    return directory


def span_outputs_from_mock(mock_dir: Path, chunks: dict, dimensions: tuple[str, ...]) -> dict:
    """jtbd-span-v1 outputs with the spans and labels of a mock model's answers (for tests).

    Chunks whose mock answer is not valid JSON are left out (they become excluded chunks).
    """
    import json as _json

    from mobility_model_zoo.productdev.jtbd.quotes import locate

    outputs = {}
    for chunk_id, chunk in chunks.items():
        answer = _json.loads((mock_dir / f"{chunk_id}.json").read_text())
        if "__raw__" in answer:
            continue
        items, used = [], []
        for item in answer["items"]:
            span = locate(item["quote"], chunk.text, used)
            if not span:
                continue
            used.append(span)
            items.append({"kind": item["kind"], "quote": chunk.text[span[0]:span[1]],
                          "start": span[0], "end": span[1], "score": 0.9,
                          **{d: item[d] for d in dimensions}})
        outputs[chunk_id] = {"output_format_version": "jtbd-span-v1",
                             "relevant": answer["relevant"], "relevance_probability": 0.5,
                             "dimensions": list(dimensions),
                             "items": sorted(items, key=lambda i: i["start"])}
    return outputs


def write_span_run(settings, run_id: str, outputs: dict, dimensions: tuple[str, ...],
                   excluded: list[str] = (), sha: str = "a" * 64) -> str:
    """A complete student run with backend `span` on the main split (for tests)."""
    from datetime import UTC, datetime

    from mobility_model_zoo.productdev.jtbd.freeze import load_manifest, schema_sha256
    from mobility_model_zoo.productdev.jtbd.jsonio import write_json
    from mobility_model_zoo.productdev.jtbd.schema import (
        ExcludedChunk,
        LabelRunManifest,
        RunSettings,
    )

    frozen = load_manifest(settings)
    directory = settings.runs_dir / run_id
    for chunk_id, output in outputs.items():
        write_json(directory / "parsed" / f"{chunk_id}.json", output)
    manifest = LabelRunManifest(
        run_id=run_id, role="student", backend="span", model_id="productdev-jtbd-span-xlmr",
        model_version=sha[:12], family="xlm-roberta", host="local",
        settings=RunSettings(temperature=0.0, structured_output="post_validation",
                             dimensions=list(dimensions), model_sha256=sha),
        guideline_sha256=frozen["hashes"]["guideline"], schema_sha256=schema_sha256(),
        criteria_sha256=frozen["hashes"]["criteria"], split="main",
        started_at=datetime.now(UTC), finished_at=datetime.now(UTC), status="complete",
        excluded_chunks=[ExcludedChunk(chunk_id=c, reason="fixture") for c in excluded])
    write_json(directory / "manifest.json", manifest.model_dump(mode="json"))
    return run_id


# ---- training dataset fixtures (feature 004, T019-T026) --------------------------------------------
PROSE = ("Die Busse im Landkreis fahren abends nur noch selten, und viele Menschen pendeln deshalb "
         "mit dem eigenen Auto zur Arbeit. Drivers say the depot chargers fail too often and they "
         "lose hours every week waiting for a free charging point. ")


def prose(seed_word: str, chars: int = 4200) -> str:
    """Prose-like text (enough letters and words for autochunk) made unique by `seed_word`."""
    text = ""
    n = 0
    while len(text) < chars:
        n += 1
        text += f"{seed_word} {n}. " + PROSE
    return text


def span_train_env(tmp_path: Path, **span_train) -> tuple[Path, Path]:
    """(benchmark config, training config): the mini corpus as the benchmark, and a training
    dataset config sharing its snapshot store, with sampled redaction review."""
    import shutil

    import yaml
    from helpers import FIXTURE

    work = tmp_path / "mini"
    shutil.copytree(FIXTURE, work)
    raw = yaml.safe_load((work / "pilot.yaml").read_text())
    raw["benchmark_version"] = "train-test-v1"
    raw["paths"].update(data="train_store", snapshots="store/snapshots",
                        ledger="store/budget/ledger.jsonl", benchmarks="train_store/benchmarks")
    raw["span_train"] = {
        "dataset": "train-test-v1", "exclude_benchmark": "pilot.yaml",
        "redaction": {"version": "redact-v2", "review": "sampled",
                      "sample": {"fraction": 0.5, "min": 2,
                                 "always_review_source_types": ["forum_review"]}},
        "validation": {"fraction_of_snapshots": 0.34, "seed": 1},
        "min_usable_chunks": 2, **span_train}
    (work / "span.yaml").write_text(yaml.safe_dump(raw, allow_unicode=True))
    return work / "pilot.yaml", work / "span.yaml"


def make_snapshot(settings, url: str, text: str, source_type: str = "paper",
                  permitted: str = "training_allowed") -> str:
    from mobility_model_zoo.productdev.jtbd.sources.snapshot import create_snapshot

    record = create_snapshot(settings, text.encode("utf-8"), "txt", url, {
        "source_type": source_type, "license": "CC-BY-4.0", "legal_basis": "fixture",
        "access_terms_checked": "fixture", "permitted_uses": permitted,
        "retention_until": "2030-01-01"})
    return record["snapshot_id"]


def snapshot_map(path: Path, snapshot_ids: list[str], language: str = "en") -> Path:
    import yaml

    path.write_text(yaml.safe_dump({"snapshots": {s: {
        "plan_id": f"T{n}", "use": "train", "sub_area": "public_transport_rural",
        "language": language, "region": "DACH", "country": "DE", "date": "2025-01-01"}
        for n, s in enumerate(snapshot_ids)}}))
    return path


def write_train_chunks(settings, specs: list[tuple[str, str, str]], text: str | None = None
                       ) -> list[str]:
    """Training chunks from (snapshot_id, language, source_type) specs (for tests)."""
    from mobility_model_zoo.productdev.jtbd.corpus.store import save_chunk
    from mobility_model_zoo.productdev.jtbd.schema import ChunkRecord

    ids = []
    for n, (snapshot_id, language, source_type) in enumerate(specs, start=1):
        body = text or f"Chunk {n}. " + PROSE
        save_chunk(settings, ChunkRecord.model_validate({
            "chunk_id": f"ch-{n:03d}", "snapshot_id": snapshot_id, "ranges": [(0, len(body))],
            "text": body, "token_count": len(body) // 4, "split": "train",
            "sub_area": "public_transport_rural", "source_type": source_type, "region": "DACH",
            "country": "DE", "language": language, "date": "2025-01-01", "license": "CC-BY-4.0",
            "relevance_intent": "relevant",
            "redaction": {"patterns_version": "redact-v2", "manual_review_at": None,
                          "check_passed": False}}))
        ids.append(f"ch-{n:03d}")
    return ids


DIMENSIONS = ("relevance", "item_matching", "kind", "actor_type", "evidence_type",
              "evidence_scope")


def pilot_decision(recommended: str | None = "mock-teacher-y", failed: tuple[str, ...] = ()
                   ) -> dict:
    return {"decision": "go",
            "per_dimension": {d: {"passed": d not in failed} for d in DIMENSIONS},
            "teacher_fitness": {"recommended": recommended}}


def write_recipe(path: Path, dimensions: list[str] | None, **overrides) -> Path:
    """A copy of configs/productdev/jtbd/span-xlmr.yaml with test overrides."""
    import yaml
    from helpers import FIXTURE

    repo = FIXTURE.parents[2]
    recipe = yaml.safe_load((repo / "configs/productdev/jtbd/span-xlmr.yaml").read_text())
    recipe["dimensions"] = dimensions
    for key, value in overrides.items():
        recipe[key] = {**recipe[key], **value} if isinstance(value, dict) else value
    path.write_text(yaml.safe_dump(recipe, sort_keys=False))
    return path


def teacher_env(tmp_path: Path, recommended: str = "mock-teacher-y",
                failed: tuple[str, ...] = ()) -> tuple[Path, Path, str]:
    """(benchmark config, training config, teacher run id): a decided pilot on the mini corpus
    and a training dataset whose chunks repeat the benchmark texts (so the mock teacher's answers
    fit), each from its own snapshot, reviewed, frozen and labeled by the recommended teacher."""
    from helpers import pilot, reference_chain

    from mobility_model_zoo.productdev.jtbd.config import load_settings
    from mobility_model_zoo.productdev.jtbd.corpus.store import load_chunks
    from mobility_model_zoo.productdev.jtbd.jsonio import write_json

    bench, train = span_train_env(tmp_path)
    reference_chain(bench)
    write_json(load_settings(bench).analysis_dir / "decision.json",
               pilot_decision(recommended, failed))
    settings = load_settings(train)
    for chunk in load_chunks(load_settings(bench), "main"):
        n = int(chunk.chunk_id[3:])
        write_train_chunks_from(settings, chunk, f"snap-{n:012d}")
    pilot(train, "corpus", "review-sample", "--seed", "1")
    pilot(train, "corpus", "mark-reviewed", "--all")
    pilot(train, "corpus", "redact-check")
    pilot(train, "freeze")
    out = pilot(train, "label", "--role", "teacher", "--backend", "mock", "--model", recommended,
                "--split", "train")
    return bench, train, out["run_id"]


def write_train_chunks_from(settings, chunk, snapshot_id: str) -> None:
    from mobility_model_zoo.productdev.jtbd.corpus.store import save_chunk

    data = chunk.model_dump(mode="json")
    data.update(snapshot_id=snapshot_id, split="train",
                redaction={"patterns_version": "redact-v2", "manual_review_at": None,
                           "check_passed": False})
    save_chunk(settings, type(chunk).model_validate(data))


def build_tiny_encoder(directory: Path) -> Path:
    """A local base encoder (random tiny XLM-RoBERTa plus tokenizer) for training tests."""
    extractor = tiny_extractor(())
    extractor.model.encoder.save_pretrained(directory)
    extractor.tokenizer.save_pretrained(directory)
    return directory


def git_commit_all(directory: Path, message: str = "fixture") -> str:
    import subprocess

    def git(*args: str) -> str:
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.org",
                               *args], cwd=directory, check=True, capture_output=True,
                              text=True).stdout.strip()

    if not (directory / ".git").exists():
        git("init", "-q")
    git("add", "-A")
    git("commit", "-q", "--allow-empty", "-m", message)
    return git("rev-parse", "HEAD")


def trained_env(tmp_path: Path, dims: tuple[str, ...] = ("actor_type",), **recipe_overrides):
    """A teacher-labeled, frozen training dataset and a committed recipe with a tiny local
    encoder: (train config, recipe path, work dir)."""
    from helpers import pilot

    failed = tuple(d for d in ("actor_type", "evidence_type", "evidence_scope") if d not in dims)
    _, train, run = teacher_env(tmp_path, failed=failed)
    work = train.parent
    encoder = build_tiny_encoder(work / "tiny-encoder")
    recipe = write_recipe(work / "recipe.yaml", list(dims),
                          base_encoder={"name": str(encoder), "revision": None},
                          training={"batch_size": 2, "max_epochs": 2},
                          **recipe_overrides)
    pilot(train, "span", "build-rows", "--run", run, "--recipe", str(recipe))
    pilot(train, "span", "freeze-data")
    git_commit_all(work)
    return train, recipe, work
