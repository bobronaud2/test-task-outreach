from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
EXTRA_PAGE_HINTS = (
    "about",
    "o-kompanii",
    "o-nas",
    "company",
    "kompaniya",
    "news",
    "novosti",
    "press",
    "cases",
    "keysy",
    "kejsy",
    "clients",
    "klienty",
    "projects",
    "proekty",
)
MAX_EXTRA_PAGES = 3
MAX_CHARS_PER_PAGE = 4000


@dataclass
class Page:
    url: str
    title: str
    text: str


@dataclass
class SiteContent:
    requested_url: str
    final_url: str
    pages: list[Page]


def normalize_url(url: str) -> str:
    url = url.strip()
    return url if "://" in url else "https://" + url


def extract_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "form"]):
        tag.decompose()
    title = soup.title.get_text(strip=True) if soup.title else ""
    meta = soup.find("meta", attrs={"name": "description"})
    description = meta.get("content", "").strip() if meta else ""
    body = " ".join(soup.get_text(" ", strip=True).split())
    text = f"{description}\n{body}" if description else body
    return title, text[:MAX_CHARS_PER_PAGE]


def pick_extra_links(html: str, base_url: str) -> list[str]:
    base_host = urlparse(base_url).hostname
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        url = urljoin(base_url, a["href"]).split("#")[0].rstrip("/")
        parsed = urlparse(url)
        if parsed.hostname != base_host or url in links or url == base_url.rstrip("/"):
            continue
        if any(hint in parsed.path.lower() for hint in EXTRA_PAGE_HINTS):
            links.append(url)
    return links[:MAX_EXTRA_PAGES]


def url_variants(url: str) -> list[str]:
    parsed = urlparse(normalize_url(url))
    host = parsed.hostname or ""
    hosts = [host] if host.startswith("www.") else [host, "www." + host]
    # Plenty of small company sites have broken TLS or answer only on plain HTTP with www
    variants = [f"{scheme}://{h}{parsed.path}" for h in hosts for scheme in ("https", "http")]
    return list(dict.fromkeys([normalize_url(url), *variants]))


def get_first_available(url: str, client: httpx.Client) -> tuple[str, httpx.Response]:
    error: httpx.HTTPError | None = None
    for candidate in url_variants(url):
        try:
            response = client.get(candidate)
            response.raise_for_status()
            return candidate, response
        except httpx.HTTPError as exc:
            error = exc
    raise error


def fetch_site(url: str, client: httpx.Client) -> SiteContent:
    requested, response = get_first_available(url, client)
    final_url = str(response.url)
    title, text = extract_text(response.text)
    pages = [Page(final_url, title, text)]
    for link in pick_extra_links(response.text, final_url):
        try:
            extra = client.get(link)
            extra.raise_for_status()
        except httpx.HTTPError:
            continue
        title, text = extract_text(extra.text)
        pages.append(Page(str(extra.url), title, text))
    return SiteContent(requested, final_url, pages)


def make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.8"},
        follow_redirects=True,
        timeout=15,
    )
