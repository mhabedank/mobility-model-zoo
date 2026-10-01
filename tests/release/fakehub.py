"""In-memory stand-in for `mobility_model_zoo.release.hub.Hub` (same methods, no network)."""

from __future__ import annotations

import hashlib
import itertools
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from mobility_model_zoo.release.errors import CredentialError, HubError

_counter = itertools.count(1)


def fake_sha() -> str:
    return hashlib.sha1(str(next(_counter)).encode()).hexdigest()


@dataclass
class FakeRepo:
    private: bool
    commits: dict[str, dict[str, bytes]] = field(default_factory=dict)  # commit -> files
    branches: dict[str, str] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)


class FakeHub:
    """Records every write in `self.writes`; failures can be injected per method name."""

    def __init__(self) -> None:
        self.repos: dict[str, FakeRepo] = {}
        self.writes: list[str] = []
        self.fail: dict[str, Exception] = {}
        self.validation = {"errors": [], "warnings": []}
        self.collections: dict[str, dict] = {}
        self.visibility_changes: list[str] = []

    def _maybe_fail(self, name: str) -> None:
        if name in self.fail:
            raise self.fail.pop(name)

    # ---- setup helpers for tests ---------------------------------------------------------------
    def seed(self, repo: str, files: dict[str, bytes], private: bool = True) -> str:
        r = self.repos.setdefault(repo, FakeRepo(private=private))
        parent = r.commits.get(r.branches.get("main", ""), {})
        sha = fake_sha()
        r.commits[sha] = {**parent, **files}
        r.branches["main"] = sha
        return sha

    def files_at(self, repo: str, revision: str) -> dict[str, bytes]:
        r = self.repos[repo]
        sha = r.branches.get(revision) or r.tags.get(revision) or revision
        if sha not in r.commits:
            raise HubError(f"unknown revision {revision}")
        return r.commits[sha]

    # ---- Hub interface -------------------------------------------------------------------------
    def visibility(self, repo: str) -> str | None:
        self._maybe_fail("visibility")
        r = self.repos.get(repo)
        return None if r is None else ("private" if r.private else "public")

    def create_repo(self, repo: str, private: bool) -> None:
        self._maybe_fail("create_repo")
        if repo in self.repos:
            raise HubError(f"{repo} exists")
        self.repos[repo] = FakeRepo(private=private)
        self.writes.append(f"create_repo {repo} private={private}")

    def refs(self, repo: str) -> dict[str, dict[str, str]]:
        r = self.repos[repo]
        return {"branches": dict(r.branches), "tags": dict(r.tags)}

    def list_files(self, repo: str, revision: str) -> list[str]:
        return sorted(self.files_at(repo, revision))

    def file_info(self, repo: str, path: str, revision: str) -> tuple[str, int] | None:
        data = self.files_at(repo, revision).get(path)
        return None if data is None else (hashlib.sha256(data).hexdigest(), len(data))

    def download(self, repo: str, path: str, revision: str, dest: Path) -> Path:
        self._maybe_fail("download")
        data = self.files_at(repo, revision)[path]
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def commit(self, repo: str, files: dict[str, Path], message: str, branch: str = "main") -> str:
        self._maybe_fail("commit")
        r = self.repos[repo]
        parent = r.commits.get(r.branches.get(branch, ""), {})
        sha = fake_sha()
        r.commits[sha] = {**parent, **{p: Path(f).read_bytes() for p, f in files.items()}}
        r.branches[branch] = sha
        self.writes.append(f"commit {repo}@{branch} {sorted(files)}")
        return sha

    def replace_branch(self, repo: str, branch: str, revision: str) -> None:
        r = self.repos[repo]
        sha = r.branches.get(revision) or r.tags.get(revision) or revision
        r.branches[branch] = sha
        self.writes.append(f"branch {repo}@{branch}")

    def create_tag(self, repo: str, tag: str, revision: str) -> None:
        self._maybe_fail("create_tag")
        r = self.repos[repo]
        if tag in r.tags:
            raise HubError(f"tag {tag} exists (409)")
        r.tags[tag] = r.branches.get(revision) or revision
        self.writes.append(f"tag {repo} {tag}")

    def validate_yaml(self, readme: str) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self.validation.items()}

    def create_collection(self, namespace: str, title: str, description: str) -> str:
        slug = f"{namespace}/{title.lower().replace(' ', '-')}-{len(self.collections) + 1}"
        self.collections[slug] = {"title": title, "items": []}
        self.writes.append(f"collection {slug}")
        return slug

    def add_collection_item(self, slug: str, repo: str, note: str) -> None:
        self.collections[slug]["items"].append((repo, note))
        self.writes.append(f"collection-item {slug} {repo}")


def credential_failure() -> CredentialError:
    return CredentialError("Hugging Face refused the token (401)")


def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)
