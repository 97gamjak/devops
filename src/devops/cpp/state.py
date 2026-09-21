"""State persistence for incremental C++ checks."""

import hashlib
import json
from pathlib import Path

DEFAULT_STATE_FILE = Path(".devops_cpp_state.json")

_RESULT_PASSED = "passed"
_RESULT_FAILED = "failed"

# Reserved key holding metadata about the config the state was produced with.
# It can never collide with a file path entry.
_CONFIG_KEY = "__config__"


def compute_config_hash(config_file: Path | None) -> str | None:
    """Return a hash of the raw contents of the TOML config file.

    Parameters
    ----------
    config_file: Path | None
        Path to the TOML config file, or ``None`` if none is in use.

    Returns
    -------
    str | None
        Hex SHA-256 digest, or ``None`` if there is no (readable) config file.

    """
    if config_file is None:
        return None
    try:
        return hashlib.sha256(config_file.read_bytes()).hexdigest()
    except OSError:
        return None


def load_state(state_file: Path, config_hash: str | None = None) -> dict[str, dict]:
    """Load per-file check state from a JSON file.

    The state is invalidated (an empty state is returned) when the config
    hash it was saved with differs from ``config_hash``, i.e. whenever the
    TOML config file changed, appeared or disappeared since the last run.

    Parameters
    ----------
    state_file: Path
        Path to the state file. Returns an empty dict if the file does not
        exist or cannot be parsed.
    config_hash: str | None
        Hash of the current config file as returned by ``compute_config_hash``.
        The returned state carries it so that ``save_state`` persists it.

    Returns
    -------
    dict[str, dict]
        Mapping of file path string to ``{"mtime": float, "result": str}``.

    """
    state = _read_state(state_file)
    stored_hash = state.get(_CONFIG_KEY, {}).get("hash")
    if stored_hash != config_hash:
        state = {}
    state.pop(_CONFIG_KEY, None)
    if config_hash is not None:
        state[_CONFIG_KEY] = {"hash": config_hash}
    return state


def _read_state(state_file: Path) -> dict[str, dict]:
    """Read the raw state dict, returning an empty dict on any failure."""
    if not state_file.exists():
        return {}
    try:
        with state_file.open() as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_state(state_file: Path, state: dict[str, dict]) -> None:
    """Write the state dict to a JSON file.

    Parameters
    ----------
    state_file: Path
        Destination path.
    state: dict[str, dict]
        State mapping as produced by ``update_entry``.

    """
    with state_file.open("w") as f:
        json.dump(state, f, indent=2)


def needs_check(path: Path, state: dict[str, dict]) -> bool:
    """Return True if ``path`` should be re-checked.

    A file needs checking when it is new (not in state), previously failed,
    or its modification time differs from the stored value.

    Parameters
    ----------
    path: Path
        File to test.
    state: dict[str, dict]
        State as returned by ``load_state``.

    Returns
    -------
    bool

    """
    key = str(path)
    if key not in state:
        return True
    entry = state[key]
    if entry.get("result") != _RESULT_PASSED:
        return True
    try:
        return path.stat().st_mtime != entry.get("mtime")
    except OSError:
        return True


def filter_incremental(files: list[Path], state: dict[str, dict]) -> list[Path]:
    """Return only the files from ``files`` that need checking.

    Parameters
    ----------
    files: list[Path]
        Full list of candidate files.
    state: dict[str, dict]
        State as returned by ``load_state``.

    Returns
    -------
    list[Path]

    """
    return [f for f in files if needs_check(f, state)]


def update_entry(state: dict[str, dict], path: Path, *, passed: bool) -> None:
    """Record the result for a single file in the state dict.

    Parameters
    ----------
    state: dict[str, dict]
        State dict to update in place.
    path: Path
        File that was checked.
    passed: bool
        Whether all checks passed for this file.

    """
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    state[str(path)] = {
        "mtime": mtime,
        "result": _RESULT_PASSED if passed else _RESULT_FAILED,
    }


def any_failed(state: dict[str, dict]) -> bool:
    """Return True if any file in ``state`` has a failed result.

    Parameters
    ----------
    state: dict[str, dict]
        State as returned by ``load_state``.

    Returns
    -------
    bool

    """
    return any(e.get("result") == _RESULT_FAILED for e in state.values())
