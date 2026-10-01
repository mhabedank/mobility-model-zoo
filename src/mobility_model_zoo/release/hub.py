"""All calls to the Hugging Face Hub, in one place so that tests can replace them (`FakeHub`).

Nothing in this module changes the visibility of an existing repository, deletes a tag or
overwrites one (spec FR-007, research R3).
"""

from __future__ import annotations

import functools
import hashlib
import os
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import httpx

from mobility_model_zoo.release.errors import CredentialError, HubError

VALIDATE_YAML_URL = "https://huggingface.co/api/validate-yaml"
RELEASE_TOKEN = "HF_RELEASE_TOKEN"
STAGING_TOKEN = "HF_STAGING_TOKEN"

T = TypeVar("T")


def token_from_env(name: str) -> str:
    token = os.environ.get(name, "").strip()
    if not token:
        raise CredentialError(f"{name} is not set")
    return token


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _wrap(fn: Callable[..., T]) -> Callable[..., T]:
    """Map Hub errors to CredentialError (exit 5) or HubError (exit 6), never echoing a token."""

    @functools.wraps(fn)
    def inner(*args: Any, **kwargs: Any) -> T:
        from huggingface_hub.errors import HfHubHTTPError

        try:
            return fn(*args, **kwargs)
        except HfHubHTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status in (401, 403):
                raise CredentialError(f"Hugging Face refused the token ({status}) in {fn.__name__}")
            raise HubError(f"Hugging Face error in {fn.__name__}: {status} {type(e).__name__}")
        except (httpx.HTTPError, OSError) as e:
            raise HubError(f"Hugging Face unreachable in {fn.__name__}: {type(e).__name__}")

    return inner


class Hub:
    """Thin wrapper around `huggingface_hub.HfApi` with the operations the release tool needs."""

    def __init__(self, token: str):
        from huggingface_hub import HfApi

        self._api = HfApi(token=token)
        self._token = token

    # ---- repositories --------------------------------------------------------------------------
    @_wrap
    def visibility(self, repo: str) -> str | None:
        """"private", "public", or None if the repo does not exist (or is not visible)."""
        from huggingface_hub.errors import RepositoryNotFoundError

        try:
            info = self._api.repo_info(repo)
        except RepositoryNotFoundError:
            return None
        return "private" if info.private else "public"

    @_wrap
    def create_repo(self, repo: str, private: bool) -> None:
        self._api.create_repo(repo, private=private, exist_ok=False)

    @_wrap
    def refs(self, repo: str) -> dict[str, dict[str, str]]:
        refs = self._api.list_repo_refs(repo)
        return {
            "branches": {b.name: b.target_commit for b in refs.branches},
            "tags": {t.name: t.target_commit for t in refs.tags},
        }

    @_wrap
    def list_files(self, repo: str, revision: str) -> list[str]:
        return sorted(self._api.list_repo_files(repo, revision=revision))

    @_wrap
    def file_info(self, repo: str, path: str, revision: str) -> tuple[str, int] | None:
        """(sha256, size) of one file at `revision`, or None if it does not exist."""
        infos = self._api.get_paths_info(repo, [path], revision=revision)
        if not infos or not hasattr(infos[0], "size"):
            return None
        info = infos[0]
        lfs = getattr(info, "lfs", None)
        if lfs is not None and getattr(lfs, "sha256", None):
            return lfs.sha256, info.size
        with tempfile.TemporaryDirectory() as tmp:
            local = self.download(repo, path, revision, Path(tmp))
            return sha256_file(local), local.stat().st_size

    @_wrap
    def download(self, repo: str, path: str, revision: str, dest: Path) -> Path:
        """Download one file to `dest/<path>` and return the local path."""
        got = Path(self._api.hf_hub_download(repo, path, revision=revision, local_dir=dest))
        target = dest / path
        if got.resolve() != target.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(got, target)
        return target

    @_wrap
    def commit(self, repo: str, files: dict[str, Path], message: str, branch: str = "main") -> str:
        """Upload `files` (repo path -> local file) as one commit on `branch`; return the commit."""
        from huggingface_hub import CommitOperationAdd

        ops = [CommitOperationAdd(path_in_repo=p, path_or_fileobj=str(f)) for p, f in sorted(files.items())]
        info = self._api.create_commit(repo, ops, commit_message=message, revision=branch)
        return info.oid

    @_wrap
    def replace_branch(self, repo: str, branch: str, revision: str) -> None:
        """Create `branch` at `revision`, replacing an existing branch of that name (previews only)."""
        if branch in self.refs(repo)["branches"]:
            self._api.delete_branch(repo, branch=branch)
        self._api.create_branch(repo, branch=branch, revision=revision)

    @_wrap
    def create_tag(self, repo: str, tag: str, revision: str) -> None:
        self._api.create_tag(repo, tag=tag, revision=revision, exist_ok=False)

    # ---- model cards ---------------------------------------------------------------------------
    @_wrap
    def validate_yaml(self, readme: str) -> dict[str, list[str]]:
        """The Hub's own card validation: {"errors": [...], "warnings": [...]}."""
        r = httpx.post(
            VALIDATE_YAML_URL,
            json={"content": readme, "repoType": "model"},
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()

        def text(entry: Any) -> str:
            return str(entry.get("message", entry)) if isinstance(entry, dict) else str(entry)

        return {
            "errors": [text(e) for e in data.get("errors") or []],
            "warnings": [text(w) for w in data.get("warnings") or []],
        }

    # ---- collections ---------------------------------------------------------------------------
    @_wrap
    def create_collection(self, namespace: str, title: str, description: str) -> str:
        coll = self._api.create_collection(title, namespace=namespace, description=description)
        return coll.slug

    @_wrap
    def add_collection_item(self, slug: str, repo: str, note: str) -> None:
        self._api.add_collection_item(slug, repo, "model", note=note[:500], exists_ok=True)
