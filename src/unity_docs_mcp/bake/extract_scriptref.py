from __future__ import annotations

from pathlib import Path
from typing import Dict

from bs4 import BeautifulSoup

from .html_to_md import HtmlToTextOptions, element_to_md


SCRIPTREF_UNWANTED = [
    ".header-wrapper",
    "#sidebar",
    ".nextprev",
    ".lang-switcher",
    ".language-switcher",
    ".breadcrumb",
    ".related",
    ".suggest",
]


def drop_noise(root) -> None:
    for selector in SCRIPTREF_UNWANTED:
        for tag in root.select(selector):
            tag.decompose()


def extract_scriptref(html_path: Path, options: HtmlToTextOptions) -> Dict:
    with html_path.open("r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "lxml")

    main = soup.select_one("div#content-wrap div.section") or soup.select_one("div.section")
    if main is None and soup.body:
        main = soup.body
    if main is None:
        return {"title": html_path.stem, "text_md": "", "links": []}

    drop_noise(main)

    canonical_link = soup.find("link", rel="canonical")
    canonical_url = canonical_link.get("href") if canonical_link else None
    title_tag = soup.find("h1")
    title = title_tag.get_text(" ", strip=True) if title_tag else html_path.stem
    links = []
    for a in main.find_all("a"):
        href = a.get("href")
        if not href or href.startswith("#"):
            continue
        links.append({"href_raw": href, "href_text": a.get_text(" ", strip=True)})

    text_md = element_to_md(main, options=options)
    return {"title": title, "text_md": text_md, "links": links, "canonical_url": canonical_url}
