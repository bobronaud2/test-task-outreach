import pytest

from outreach import checks


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.example.ru/about", "example.ru"),
        ("example.ru", "example.ru"),
        ("HTTP://Shop.Example.RU", "shop.example.ru"),
        ("", ""),
    ],
)
def test_site_domain(url, expected):
    assert checks.site_domain(url) == expected


def test_same_domain_accepts_subdomains():
    assert checks.same_domain("spb.example.ru", "example.ru")
    assert not checks.same_domain("notexample.ru", "example.ru")
    assert not checks.same_domain("", "example.ru")


def test_same_domain_accepts_same_brand_in_other_zone():
    assert checks.same_domain("mailganer.ru", "mailganer.com")
    assert checks.same_domain("jatcarbide.com", "jat-carbide.com")
    assert checks.same_domain("internor.com.cn", "internor.ru")
    assert not checks.same_domain("surfstudio.ru", "surf.ru")


def row(**overrides):
    return {"company": "Acme", "website": "acme.ru", "email": "sales@acme.ru"} | overrides


def test_clean_row_has_no_issues():
    assert checks.static_issues(row(), set(), set()) == []


def test_mismatched_email_domain():
    issues = checks.static_issues(row(email="sales@other.com"), set(), set())
    assert issues == ["домен email (other.com) не совпадает с сайтом (acme.ru)"]


def test_freemail_is_reported_instead_of_domain_mismatch():
    issues = checks.static_issues(row(email="swyct@126.com"), set(), set())
    assert len(issues) == 1
    assert "бесплатной почте" in issues[0]


def test_invalid_email():
    assert checks.static_issues(row(email="sales@"), set(), set())[0].startswith("некорректный")


def test_duplicates_are_found_by_domain_and_email():
    rows = [
        row(website="https://www.acme.ru"),
        row(website="acme.ru", email="SALES@acme.ru"),
        row(website="beta.ru", email="info@beta.ru"),
    ]
    assert checks.duplicates(rows, "website") == {"acme.ru"}
    assert checks.duplicates(rows, "email") == {"sales@acme.ru"}

    issues = checks.static_issues(rows[0], {"acme.ru"}, {"sales@acme.ru"})
    assert len(issues) == 2
