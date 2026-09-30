import json

import pytest

from outreach.fetch import Page, SiteContent
from outreach.llm import LLMError, build_prompt, parse_response

ANSWER = {
    "fact": "Вы делаете станки с 2005 года.",
    "source_url": "https://acme.ru/about",
    "site_company": "Acme",
    "matches_company": True,
    "country": "Россия",
}


def test_parse_structured_output():
    research = parse_response(json.dumps({"is_error": False, "structured_output": ANSWER}))
    assert research.fact == ANSWER["fact"]
    assert research.matches_company is True


def test_parse_falls_back_to_result_text():
    research = parse_response(json.dumps({"is_error": False, "result": json.dumps(ANSWER)}))
    assert research.source_url == ANSWER["source_url"]


@pytest.mark.parametrize(
    "stdout",
    ["not json", json.dumps({"is_error": True, "result": "limit"}), json.dumps({"result": "hi"})],
)
def test_parse_errors(stdout):
    with pytest.raises(LLMError):
        parse_response(stdout)


def test_prompt_mentions_redirect():
    site = SiteContent("https://acme.ru", "https://beta.ru/", [Page("https://beta.ru/", "B", "t")])
    prompt = build_prompt("Acme", site)
    assert "перенаправил на: https://beta.ru/" in prompt
    assert "<page url='https://beta.ru/'>" in prompt
