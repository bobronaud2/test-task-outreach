import re
from collections import Counter
from functools import cache
from urllib.parse import urlparse

import dns.exception
import dns.resolver

EMAIL_RE = re.compile(r"^[\w.+-]+@([\w-]+\.)+[\w-]{2,}$")

FREEMAIL_DOMAINS = {
    "gmail.com",
    "mail.ru",
    "bk.ru",
    "inbox.ru",
    "list.ru",
    "internet.ru",
    "yandex.ru",
    "ya.ru",
    "rambler.ru",
    "outlook.com",
    "hotmail.com",
    "yahoo.com",
    "icloud.com",
    "126.com",
    "163.com",
    "qq.com",
    "sina.com",
}


def site_domain(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if "://" not in url:
        url = "https://" + url
    host = (urlparse(url).hostname or "").lower()
    return host.removeprefix("www.")


def email_domain(email: str) -> str:
    return email.strip().rsplit("@", 1)[-1].lower() if "@" in email else ""


def brand(domain: str) -> str:
    labels = domain.split(".")[:-1]
    if len(labels) > 1 and labels[-1] in {"com", "net", "org", "co"}:
        labels = labels[:-1]
    return labels[-1].replace("-", "") if labels else ""


def same_domain(a: str, b: str) -> bool:
    if not (a and b):
        return False
    # sales@spb.company.ru, company.com and com-pany.ru are treated as the same company
    return a == b or a.endswith("." + b) or b.endswith("." + a) or brand(a) == brand(b)


@cache
def has_mx(domain: str) -> bool:
    try:
        return bool(dns.resolver.resolve(domain, "MX", lifetime=10))
    except dns.exception.DNSException:
        return False


def duplicates(rows: list[dict], key: str) -> set[str]:
    counts = Counter(value for row in rows if (value := key_value(row, key)))
    return {value for value, n in counts.items() if n > 1}


def key_value(row: dict, key: str) -> str:
    if key == "website":
        return site_domain(row.get("website", ""))
    return row.get(key, "").strip().lower()


def static_issues(row: dict, dup_sites: set[str], dup_emails: set[str]) -> list[str]:
    email = row.get("email", "").strip()
    site = site_domain(row.get("website", ""))
    mail_domain = email_domain(email)
    issues = []

    if not EMAIL_RE.match(email):
        issues.append(f"некорректный email: {email or 'пусто'}")
    elif mail_domain in FREEMAIL_DOMAINS:
        issues.append(f"email на бесплатной почте ({mail_domain}), не корпоративный")
    elif not same_domain(mail_domain, site):
        issues.append(f"домен email ({mail_domain}) не совпадает с сайтом ({site or 'нет'})")

    if site and site in dup_sites:
        issues.append(f"сайт {site} встречается в базе несколько раз")
    if email and email.lower() in dup_emails:
        issues.append(f"email {email} встречается в базе несколько раз")
    return issues
