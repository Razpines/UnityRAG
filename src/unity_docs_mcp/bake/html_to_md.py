from __future__ import annotations

import html
import textwrap
from dataclasses import dataclass
from typing import Iterable, Optional

from bs4.element import NavigableString, Tag


@dataclass
class HtmlToTextOptions:
    keep_images: bool = False
    include_figure_captions: bool = True


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def render_list(tag: Tag, depth: int = 0) -> str:
    bullet = "-" if tag.name == "ul" else "1."
    lines = []
    for li in tag.find_all("li", recursive=False):
        prefix = "  " * depth + f"{bullet} "
        body_parts = []
        for child in li.children:
            rendered = element_to_md(child, depth=depth + 1)
            if rendered:
                body_parts.append(rendered.strip())
        body = " ".join(body_parts).strip()
        lines.append(prefix + body)
        for nested in li.find_all(["ul", "ol"], recursive=False):
            lines.append(render_list(nested, depth=depth + 1))
    return "\n".join(lines)


def render_table(tag: Tag) -> str:
    rows = []
    headers = tag.find_all("th")
    if headers:
        header_cells = [normalize_text(th.get_text(" ", strip=True)) for th in headers]
        rows.append("| " + " | ".join(header_cells) + " |")
        rows.append("|" + "|".join([" --- " for _ in header_cells]) + "|")
    for tr in tag.find_all("tr", recursive=False):
        cells = [normalize_text(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"], recursive=False)]
        if cells:
            rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def render_code_block(tag: Tag) -> str:
    language = ""
    class_attr = tag.get("class", [])
    for cls in class_attr:
        if cls.startswith("lang-"):
            language = cls.replace("lang-", "")
            break
    code_text = tag.get_text("", strip=False)
    code_text = html.unescape(code_text)
    fenced = f"```{language}\n{code_text}\n```"
    return fenced


def element_to_md(node, depth: int = 0, options: Optional[HtmlToTextOptions] = None) -> str:
    opts = options or HtmlToTextOptions()
    if isinstance(node, NavigableString):
        return normalize_text(str(node))
    if not isinstance(node, Tag):
        return ""

    name = node.name.lower()
    if name in ["style", "script", "noscript"]:
        return ""

    if name in ["h1", "h2", "h3", "h4"]:
        level = int(name[1])
        heading = "#" * level + " " + normalize_text(node.get_text(" ", strip=True))
        return "\n\n" + heading + "\n\n"
    if name == "p":
        text = normalize_text(node.get_text(" ", strip=True))
        return text + "\n\n"
    if name in ["ul", "ol"]:
        return render_list(node) + "\n\n"
    if name == "table":
        return render_table(node) + "\n\n"
    if name == "dl":
        lines = []
        terms = node.find_all("dt", recursive=False)
        for term in terms:
            dd = term.find_next_sibling("dd")
            term_text = normalize_text(term.get_text(" ", strip=True))
            desc_text = normalize_text(dd.get_text(" ", strip=True)) if dd else ""
            lines.append(f"- {term_text}: {desc_text}")
        return "\n".join(lines) + "\n\n"
    if name == "code" and node.parent and node.parent.name != "pre":
        return f"`{normalize_text(node.get_text(' ', strip=True))}`"
    if name == "pre":
        code_tag = node.find("code")
        if code_tag:
            return render_code_block(code_tag) + "\n\n"
        return f"```\n{html.unescape(node.get_text('', strip=False))}\n```\n\n"
    if name == "figure":
        parts = []
        if opts.keep_images:
            img = node.find("img")
            if img and img.get("src"):
                alt = img.get("alt", "")
                parts.append(f"![{alt}]({img['src']})")
        if opts.include_figure_captions:
            caption = node.find("figcaption")
            if caption:
                parts.append(normalize_text(caption.get_text(" ", strip=True)))
        return "\n\n".join(parts) + "\n\n" if parts else ""
    if name == "a":
        href = node.get("href", "")
        text = normalize_text(node.get_text(" ", strip=True))
        if not text:
            return ""
        return f"{text} ({href})" if href else text

    # Generic container: render children
    rendered_children = [element_to_md(child, depth=depth, options=opts) for child in node.children]
    return " ".join([child for child in rendered_children if child])
