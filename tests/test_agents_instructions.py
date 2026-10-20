from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / "AGENTS.md"


def test_agents_honor_existing_cache_configuration() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert "Prefer project-local environments and caches" not in text
    assert "HF_HOME" in text
    assert "XDG_CACHE_HOME" in text
    assert "treat them as intentional" in text
    assert "preserve them in commands and Slurm scripts" in text
    assert "checking quotas, project conventions, and existing user-configured cache locations" in text


def test_agents_distinguish_virtualenvs_from_large_caches() -> None:
    text = AGENTS.read_text(encoding="utf-8")
    assert "project-specific virtual environments" in text
    assert "do not move large reusable caches or downloaded models into the project directory" in text
