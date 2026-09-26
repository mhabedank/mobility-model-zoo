"""Error types mapped to the CLI exit codes in contracts/cli.md."""


class PilotError(Exception):
    exit_code = 1


class ValidationFailed(PilotError):
    exit_code = 1


class UsageError(PilotError):
    exit_code = 2


class FrozenHashMismatch(PilotError):
    exit_code = 3


class BudgetRefused(PilotError):
    exit_code = 4


class CrawlOnceRefused(PilotError):
    exit_code = 5


class BackendFailure(PilotError):
    exit_code = 6
