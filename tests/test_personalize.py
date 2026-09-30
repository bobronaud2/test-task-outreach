import httpx

from outreach.fetch import Page, SiteContent
from outreach.llm import LLMError, Research
from outreach.personalize import (
    STATUS_OK,
    STATUS_REVIEW,
    STATUS_SKIP,
    add_cross_row_hints,
    personalize_row,
)

ROW = {"company": "Acme", "website": "acme.ru", "email": "sales@acme.ru"}


def fetch_ok(url):
    return SiteContent("https://acme.ru", "https://acme.ru/", [Page("https://acme.ru/", "", "")])


def research_with(**overrides):
    base = Research("Вы делаете станки.", "https://acme.ru/", "Acme", True, "Россия")

    def research(company, site):
        return Research(**(base.__dict__ | overrides))

    return research


def run(row=ROW, fetch=fetch_ok, research=None, has_mx=lambda domain: True):
    return personalize_row(row, set(), set(), fetch, research or research_with(), has_mx)


def test_happy_path():
    result = run()
    assert result["status"] == STATUS_OK
    assert result["personalization"] == "Вы делаете станки."
    assert result["issues"] == ""


def test_foreign_company_on_mismatched_site_needs_review():
    result = run(
        research=research_with(matches_company=False, site_company="Beta", country="Китай")
    )
    assert result["status"] == STATUS_REVIEW
    assert "другой компании (Beta)" in result["issues"]
    assert "не из России" in result["issues"]


def test_missing_mx_blocks_sending():
    assert run(has_mx=lambda domain: False)["status"] == STATUS_SKIP


def test_unreachable_site_is_skipped():
    def fetch_fails(url):
        raise httpx.ConnectError("boom")

    result = run(fetch=fetch_fails)
    assert result["status"] == STATUS_SKIP
    assert "сайт недоступен" in result["issues"]


def test_redirect_to_other_domain_is_reported():
    def fetch_redirect(url):
        return SiteContent("https://acme.ru", "https://beta.ru/", [])

    assert "перенаправляет на beta.ru" in run(fetch=fetch_redirect)["issues"]


def test_llm_failure_keeps_row():
    def research_fails(company, site):
        raise LLMError("timeout")

    result = run(research=research_fails)
    assert result["status"] == STATUS_REVIEW
    assert result["company"] == "Acme"


def test_mismatched_email_domain_is_looked_up():
    def fetch_by_domain(url):
        title = "Nantong Tengzhong" if "nttzmt" in url else "Ункомтех"
        return SiteContent(url, url, [Page(url, title, "")])

    row = {"company": "Tengzhong", "website": "uncomtech.ru", "email": "sales@nttzmt.com"}
    result = run(row=row, fetch=fetch_by_domain)
    assert "что на домене email: nttzmt.com «Nantong Tengzhong»" in result["issues"]


def test_cross_row_hint_points_to_swapped_company():
    results = [
        {"company": "ТД Ункомтех", "site_company": "Sainty", "status": STATUS_OK, "issues": ""},
        {
            "company": "Tengzhong Machinery",
            "site_company": "ООО «Торговый Дом «УНКОМТЕХ»",
            "status": STATUS_OK,
            "issues": "",
        },
    ]
    add_cross_row_hints(results)
    assert results[0]["issues"] == ""
    assert "«ТД Ункомтех» из другой строки" in results[1]["issues"]
    assert results[1]["status"] == STATUS_REVIEW
