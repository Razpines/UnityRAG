from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from bs4 import BeautifulSoup

from .html_to_md import HtmlToTextOptions, element_to_md


UNWANTED_SELECTORS = [
    ".header-wrapper",
    "#sidebar",
    ".breadcrumbs",
    ".nextprev",
    "#_leavefeedback",
    ".footer-wrapper",
    ".lang-switcher",
    ".language-switcher",
    ".clear",
]


def drop_unwanted_nodes(root) -> None:
    for selector in UNWANTED_SELECTORS:
        for tag in root.select(selector):
            tag.decompose()


def drop_sections(root, section_titles: List[str]) -> None:
    titles = {title.lower() for title in section_titles}
    for heading in root.find_all(["h2", "h3", "h4"]):
        text = heading.get_text(" ", strip=True).lower()
        if text in titles:
            to_remove = [heading]
            sib = heading.find_next_sibling()
            while sib and not (sib.name and sib.name.startswith("h")):
                to_remove.append(sib)
                sib = sib.find_next_sibling()
            for node in to_remove:
                node.decompose()


def extract_manual(html_path: Path, options: HtmlToTextOptions, drop_sections_list: List[str]) -> Dict:
    with html_path.open("r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "lxml")

    main = soup.select_one("div#content-wrap div.section") or soup.select_one("div.section")
    if main is None and soup.body:
        main = soup.body
    if main is None:
        return {"title": html_path.stem, "text_md": "", "links": []}

    drop_unwanted_nodes(main)
    if drop_sections_list:
        drop_sections(main, drop_sections_list)

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
