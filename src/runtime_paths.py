"""The single runtime-data root.

Everything Apocrysis writes while it runs - player state, saved games,
and logs - lives under one directory tree, never scattered into the
repository root or the launch cwd.

Layout (under APOCRYSIS_HOME, default `<repo>/.apocrysis/`):

    player/              per-campaign profiles (identity, progression,
                         investigation state)
    saves/               full-state session saves (named slots)
    logs/sessions/       human play-session transcripts (src/playlog.py)
    logs/telemetry/      bot-run / analysis output (opt-in via tool flags)

Override the whole tree with the `APOCRYSIS_HOME` environment variable
(the test suite points it at a per-test temp dir). The directory is the
installation's state; the repository stays just the game.

    RULE: no runtime-generated file may be created in the repo root.
    Anything written at run time goes through resolve() / *_dir().
"""
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

_KIND_SUBDIR = {
    "player": ("player",),
    "save": ("saves",),
    "session_log": ("logs", "sessions"),
    "telemetry": ("logs", "telemetry"),
}


def home() -> Path:
    """The runtime-data root. Read fresh each call so a test (or a
    relaunch) that sets APOCRYSIS_HOME takes effect immediately."""
    env = os.environ.get("APOCRYSIS_HOME")
    return Path(env).expanduser() if env else _REPO_ROOT / ".apocrysis"


def _dir(*parts) -> Path:
    p = home().joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


def player_dir() -> Path:
    return _dir("player")


def saves_dir() -> Path:
    return _dir("saves")


def session_logs_dir() -> Path:
    return _dir("logs", "sessions")


def telemetry_dir() -> Path:
    return _dir("logs", "telemetry")


def resolve(kind: str, name: str) -> str:
    """Absolute path for a runtime file of the given `kind`
    ('player' | 'save' | 'session_log' | 'telemetry').

    A bare filename is placed under that kind's directory. A name that
    already carries a directory component - or an absolute path - is
    honoured as-is (an explicit `--save /tmp/x.json`, or a test passing
    its own path), so callers keep full control when they want it.
    """
    if os.path.isabs(name) or os.path.dirname(name):
        return os.path.abspath(name)
    return str(_dir(*_KIND_SUBDIR[kind]) / name)


def dev_profile_path() -> str:
    """The `--dev` sandbox profile - wiped each run, never a real
    campaign file. Lives beside player profiles but clearly marked."""
    return resolve("player", "dev_playtest_profile.json")
