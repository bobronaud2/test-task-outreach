from outreach.fetch import extract_text, pick_extra_links, url_variants

HTML = """
<html><head><title>Acme</title><meta name="description" content="Станки для заводов">
<script>var x = 1;</script></head>
<body>
  <h1>Acme</h1><p>Делаем   станки с 2005 года.</p>
  <a href="/o-kompanii/">О компании</a>
  <a href="/news">Новости</a>
  <a href="/news#top">Новости ещё раз</a>
  <a href="https://other.ru/about">Чужой сайт</a>
  <a href="/catalog">Каталог</a>
</body></html>
"""


def test_extract_text_drops_scripts_and_keeps_description():
    title, text = extract_text(HTML)
    assert title == "Acme"
    assert text.startswith("Станки для заводов")
    assert "Делаем станки с 2005 года." in text
    assert "var x" not in text


def test_pick_extra_links_keeps_same_host_about_and_news():
    links = pick_extra_links(HTML, "https://acme.ru/")
    assert links == ["https://acme.ru/o-kompanii", "https://acme.ru/news"]


def test_url_variants_try_https_first_then_http_and_www():
    assert url_variants("example.ru") == [
        "https://example.ru",
        "http://example.ru",
        "https://www.example.ru",
        "http://www.example.ru",
    ]
    assert url_variants("https://www.example.ru/") == [
        "https://www.example.ru/",
        "http://www.example.ru/",
    ]
