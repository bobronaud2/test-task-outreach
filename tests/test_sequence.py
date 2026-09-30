import csv
from pathlib import Path

SEQUENCE = Path(__file__).parent.parent / "data" / "sequence.csv"
MAX_WORDS = 120
PERSONALIZATION_MAX_WORDS = 30


def load():
    with SEQUENCE.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def word_count(text):
    return len(text.split())


def test_three_steps_with_expected_delays():
    assert [(e["step"], e["delay_days"]) for e in load()] == [("1", "0"), ("2", "3"), ("3", "5")]


def test_every_email_has_subject_and_fits_limit():
    for email in load():
        assert email["subject"].strip()
        filled = email["body"].replace("{{персонализация}}", "слово " * PERSONALIZATION_MAX_WORDS)
        assert word_count(filled) <= MAX_WORDS, email["step"]


def test_first_email_uses_personalization():
    first, *rest = load()
    assert "{{персонализация}}" in first["body"]
    assert all("{{персонализация}}" not in email["body"] for email in rest)
