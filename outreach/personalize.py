import csv
import logging
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

from outreach import checks
from outreach.fetch import SiteContent, fetch_site, make_client
from outreach.llm import LLMError, Research, research_company

log = logging.getLogger(__name__)

OUTPUT_FIELDS = ["personalization", "personalization_source", "site_company", "status", "issues"]
STATUS_OK = "ok"
STATUS_REVIEW = "проверить"
STATUS_SKIP = "не отправлять"

Fetcher = Callable[[str], SiteContent]
Researcher = Callable[[str, SiteContent], Research]
MxChecker = Callable[[str], bool]


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def write_rows(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def personalize_row(
    row: dict,
    dup_sites: set[str],
    dup_emails: set[str],
    fetch: Fetcher,
    research: Researcher,
    has_mx: MxChecker = checks.has_mx,
) -> dict:
    issues = checks.static_issues(row, dup_sites, dup_emails)
    blocking = False

    mail_domain = checks.email_domain(row.get("email", ""))
    if mail_domain and not has_mx(mail_domain):
        issues.append(f"у домена {mail_domain} нет MX-записи, письмо не дойдёт")
        blocking = True

    result = dict(row) | dict.fromkeys(OUTPUT_FIELDS, "")
    if not row.get("website"):
        issues.append("не указан сайт")
        return result | {"status": STATUS_SKIP, "issues": "; ".join(issues)}
    try:
        site = fetch(row.get("website", ""))
    except httpx.HTTPError as exc:
        issues.append(f"сайт недоступен: {exc.__class__.__name__}")
        return result | {"status": STATUS_SKIP, "issues": "; ".join(issues)}

    corporate_mail = mail_domain and mail_domain not in checks.FREEMAIL_DOMAINS
    if corporate_mail and not checks.same_domain(mail_domain, checks.site_domain(row["website"])):
        issues.append(f"что на домене email: {describe_site(mail_domain, fetch)}")

    requested = checks.site_domain(site.requested_url)
    landed = checks.site_domain(site.final_url)
    if not checks.same_domain(requested, landed):
        issues.append(f"сайт {requested} перенаправляет на {landed}")

    try:
        found = research(row.get("company", ""), site)
    except LLMError as exc:
        issues.append(f"не удалось получить персонализацию: {exc}")
        return result | {"status": STATUS_REVIEW, "issues": "; ".join(issues)}

    if not found.matches_company:
        issues.append(
            f"сайт принадлежит другой компании ({found.site_company or 'неизвестно'}), "
            f"а не «{row.get('company', '')}»"
        )
    if found.country and found.country.lower() not in {"россия", "russia", "рф"}:
        issues.append(f"компания не из России ({found.country}), не наша ЦА")
    if not found.fact:
        issues.append("на сайте нет конкретного факта для персонализации")

    if blocking:
        status = STATUS_SKIP
    elif issues:
        status = STATUS_REVIEW
    else:
        status = STATUS_OK
    return result | {
        "personalization": found.fact,
        "personalization_source": found.source_url,
        "site_company": found.site_company,
        "status": status,
        "issues": "; ".join(issues),
    }


def describe_site(domain: str, fetch: Fetcher) -> str:
    try:
        title = fetch(domain).pages[0].title
    except (httpx.HTTPError, IndexError):
        return f"{domain} (не открывается)"
    return f"{domain} «{title[:80]}»" if title else domain


LEGAL_FORMS = {"ооо", "ао", "зао", "пао", "тд", "гк", "нпк", "ltd", "co", "inc", "llc", "group"}


def name_tokens(name: str) -> str:
    words = re.sub(r"[^\w]+", " ", name.lower()).split()
    return " ".join(word for word in words if word not in LEGAL_FORMS)


def add_cross_row_hints(results: list[dict]) -> None:
    # Catches shuffled columns: the site of one row describes a company from another row
    names = [(r.get("company", ""), name_tokens(r.get("company", ""))) for r in results]
    for result in results:
        site_company = name_tokens(result.get("site_company", ""))
        own = name_tokens(result.get("company", ""))
        for company, tokens in names:
            if len(tokens) >= 4 and tokens != own and tokens in site_company:
                hint = f"похоже, сайт относится к компании «{company}» из другой строки"
                result["issues"] = "; ".join(filter(None, [result["issues"], hint]))
                if result["status"] == STATUS_OK:
                    result["status"] = STATUS_REVIEW


def personalize_file(
    source: Path, target: Path, workers: int = 4, limit: int | None = None
) -> None:
    rows = read_rows(source)[:limit]
    dup_sites = checks.duplicates(rows, "website")
    dup_emails = checks.duplicates(rows, "email")

    with make_client() as client:

        def fetch(url: str) -> SiteContent:
            return fetch_site(url, client)

        def process(indexed: tuple[int, dict]) -> dict:
            index, row = indexed
            done = personalize_row(row, dup_sites, dup_emails, fetch, research_company)
            log.info("%d/%d %s: %s", index + 1, len(rows), row.get("company"), done["status"])
            return done

        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(process, enumerate(rows)))

    add_cross_row_hints(results)
    write_rows(target, results)
