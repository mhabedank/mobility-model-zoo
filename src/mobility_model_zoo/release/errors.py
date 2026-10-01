"""Exceptions of the release tool, one per exit code (contracts/cli.md)."""

from __future__ import annotations


class ZooError(Exception):
    exit_code = 1


class GateFailed(ZooError):
    """A gate rule, schema, checksum or card validation failed."""

    exit_code = 1

    def __init__(self, failures: list[str]):
        self.failures = failures
        super().__init__("; ".join(failures))


class UsageError(ZooError):
    exit_code = 2


class ImmutabilityRefused(ZooError):
    """The version is already published, its tag exists, or it is not newer than the latest."""

    exit_code = 3


class ApprovalRefused(ZooError):
    """`--confirm` does not match, or the reviewed preview is missing or does not match."""

    exit_code = 4


class CredentialError(ZooError):
    exit_code = 5


class HubError(ZooError):
    """Hugging Face or GitHub was unreachable or returned an error. A retry is safe."""

    exit_code = 6
