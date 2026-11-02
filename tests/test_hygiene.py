import re
from pathlib import Path

from dorarv.reference import ROOT

SKIP = {".venv", "__pycache__", ".pytest_cache", "dorarv.egg-info", "src/dora_register_validator.egg-info"}
TEXT = {".py", ".md", ".csv", ".sql", ".json", ".txt", ".toml", ".gitignore"}
FORBIDDEN = re.compile(r"\b(claude|anthropic|chatgpt|gpt-?\d|openai|llm|copilot|ai-generated|agent)\b", re.I)
PERSONAL = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}|danielfreire|/Users/|hl-vault|doorway|slr_workbench", re.I)


def _files():
    for p in ROOT.rglob("*"):
        if p.is_file() and not any(s in p.parts or s in p.as_posix() for s in SKIP) and not p.name.endswith(".egg-info") \
                and "egg-info" not in p.as_posix() and (p.suffix in TEXT or p.name == ".gitignore"):
            yield p


def test_no_tool_or_vendor_mentions():
    bad = [(str(p.relative_to(ROOT)), m.group(0)) for p in _files() if p.name != "test_hygiene.py"
           for m in FORBIDDEN.finditer(p.read_text(errors="ignore"))]
    assert not bad, bad[:5]


def test_no_personal_data_or_private_project_names():
    bad = [(str(p.relative_to(ROOT)), m.group(0)) for p in _files() if p.name != "test_hygiene.py"
           for m in PERSONAL.finditer(p.read_text(errors="ignore"))]
    assert not bad, bad[:5]


def test_venv_is_ignored():
    assert ".venv/" in (ROOT / ".gitignore").read_text()
