#!/usr/bin/env python3
"""Convert a GitBook Git Sync export into the Docusaurus docs/ tree.

SUMMARY.md is the source of truth for structure: its `## HEADING` blocks are the
sidebar groups and its nested list items are the page order and labels. The
directory layout does not encode the grouping — Introduction lives at the export
root but belongs to the GENERAL group — so the sidebar is generated from
SUMMARY.md rather than from the filesystem.

Outputs:
  docs/**                     converted pages, README.md becoming index.md
  sidebars.generated.json     explicit sidebar mirroring SUMMARY.md
  static/gitbook/assets/**    only the assets actually referenced

Usage:
  python3 scripts/gitbook-import.py --source ../gitbook-export
"""

import argparse
import html
import json
import os
import re
import shutil
import sys
import urllib.parse

GROUP = re.compile(r"^##\s+(?P<label>.+?)\s*$")
ITEM = re.compile(r"^(?P<indent>\s*)\*\s+\[(?P<label>[^\]]*)\]\((?P<target>[^)]+)\)\s*$")
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
COVER = re.compile(r"^cover:\s*(?P<path>.+?)\s*$", re.M)
EMBED = re.compile(r"\{%\s*embed\s+url=\"?<?(?P<url>[^\">\s]+)>?\"?[^%]*?%\}"
                   r"(?P<caption>.*?)\{%\s*endembed\s*%\}", re.S)
HINT = re.compile(r"\{%\s*hint style=\"(?P<style>\w+)\"\s*%\}(?P<body>.*?)\{%\s*endhint\s*%\}", re.S)
TABS = re.compile(r"\{%\s*tabs?\s*%\}|\{%\s*endtabs?\s*%\}|\{%\s*tab title=\"[^\"]*\"\s*%\}|\{%\s*endtab\s*%\}")
LEFTOVER = re.compile(r"\{%.*?%\}", re.S)
# Asset filenames contain spaces and HTML-escaped ampersands, so the terminator
# has to come from the surrounding syntax rather than from whitespace.
ASSET_ATTR = re.compile(
    r"(?P<attr>src|href|poster)=(?P<q>[\"'])(?:\.\./)*\.gitbook/assets/"
    r"(?P<name>[^\"']+)(?P=q)")
ASSET_MD = re.compile(r"\]\((?:\.\./)*\.gitbook/assets/(?P<name>[^)]+)\)")
ASSET_ANY = re.compile(r"\.gitbook/assets/")
VOID_TAG = re.compile(
    r"<(?P<tag>img|br|hr|input|source|col|area|base|link|meta|param|track|wbr)"
    r"(?P<attrs>(?:\s[^>]*?)?)\s*/?>", re.I)
MD_LINK_README = re.compile(r"\]\((?P<pre>[^)]*?)README\.md(?P<post>[^)]*)\)")
HREF_README = re.compile(r"""href=["'](?P<pre>[^"']*?)README\.md(?P<post>[^"']*)["']""")
ADMONITION = {"info": "info", "warning": "caution", "danger": "danger",
              "success": "tip", "tip": "tip"}
VIDEO_EXT = (".mp4", ".webm", ".mov", ".m4v")
# GitBook's own marker for a link it could not resolve; keep the text, drop the
# link. The published site uses a broken:// scheme, the Git Sync export a
# site-absolute /broken/ path.
BROKEN_LINK = re.compile(r"\[(?P<text>[^\]]*)\]\((?:broken://|/broken/)[^)]*\)")


def parse_summary(text):
    """[(group_label, [item])] where item = {label, target, children:[item]}."""
    groups, current, stack = [], None, []
    for line in text.splitlines():
        g = GROUP.match(line)
        if g:
            current = (g.group("label"), [])
            groups.append(current)
            stack = []
            continue
        m = ITEM.match(line)
        if not m or current is None:
            continue
        depth = len(m.group("indent")) // 2
        node = {"label": m.group("label").strip(),
                "target": m.group("target").strip(),
                "children": []}
        while len(stack) > depth:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
        else:
            current[1].append(node)
        stack.append(node)
    return groups


def doc_id(target):
    """Docusaurus id for an export-relative .md path.

    Ids come from the output path, and this Docusaurus version does not collapse
    a folder's index.md to the folder id, so foo/README.md becomes foo/index.
    The root page is the exception: it carries an explicit frontmatter id.
    """
    rel = target[:-3] if target.endswith(".md") else target
    if rel in ("README", ""):
        return "introduction"
    if rel.endswith("/README"):
        return rel[: -len("/README")] + "/index"
    return rel


def dest_path(target):
    """docs/-relative output path; README.md becomes index.md."""
    if target == "README.md":
        return "index.md"
    return re.sub(r"README\.md$", "index.md", target)


def served_asset(name, prefix):
    return f"{prefix.rstrip('/')}/{urllib.parse.quote(name)}"


HTML_MD_HREF = re.compile(r"""href=(?P<q>["'])(?P<target>(?!https?:|/|#)[^"']+\.md)(?P<frag>)(?P=q)""")
CARD_TABLE = re.compile(r"<table[^>]*data-view=\"cards\"[^>]*>.*?</table>", re.S)
ROW = re.compile(r"<tr>(?P<cells>.*?)</tr>", re.S)
CELL = re.compile(r"<t[dh][^>]*>(?P<inner>.*?)</t[dh]>", re.S)
ANCHOR = re.compile(r"<a\s+href=[\"'](?P<href>[^\"']+)[\"'][^>]*>(?P<text>.*?)</a>", re.S)
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")


def cards_from_table(body):
    """Turn GitBook's card-view tables into a card grid.

    GitBook renders <table data-view="cards"> as cards, with one column holding
    the cover asset and another the target page. In the export both are plain
    anchors whose link text is a filename, so leaving the table in place would
    show a table of filenames. CSS alone cannot fix that — the cover has to
    become an <img> — so the markup is rebuilt here.
    """
    def convert(m):
        cards = []
        for row in ROW.finditer(m.group(0)):
            cells = [c.group("inner") for c in CELL.finditer(row.group("cells"))]
            if not cells:
                continue
            anchors = [(a.group("href"), a.group("text")) for c in cells
                       for a in ANCHOR.finditer(c)]
            if not anchors:
                continue                      # header row
            cover = next((h for h, _ in anchors
                          if h.lower().split("?")[0].endswith(IMAGE_EXT)), "")
            target = next((h for h, _ in anchors if h != cover), "")
            text = ""
            for c in cells:
                if not ANCHOR.search(c):
                    text = re.sub(r"<[^>]+>", "", c).strip()
                    if text:
                        break
            # No class on the img: Docusaurus adds its own to images in MDX and
            # two class attributes on one element is invalid HTML.
            img = f'<img src="{cover}" alt="" />' if cover else ""
            label = f'<span class="gb-card-text">{text}</span>' if text else ""
            if target:
                cards.append(f'<a class="gb-card" href="{target}">{img}{label}</a>')
            else:
                cards.append(f'<div class="gb-card">{img}{label}</div>')
        if not cards:
            return m.group(0)
        return '<div class="gb-cards">\n' + "\n".join(cards) + "\n</div>"

    return CARD_TABLE.sub(convert, body)


def html_md_to_route(body, page_dir, route_prefix):
    """Point raw-HTML .md hrefs at real routes.

    Docusaurus rewrites .md links written in markdown syntax, but raw HTML
    attributes pass through untouched, so a card table's <a href="logos.md">
    would ship a dead link.
    """
    def repl(m):
        target = m.group("target")
        joined = os.path.normpath(os.path.join(page_dir, target)) if page_dir else target
        route = joined[:-3] if joined.endswith(".md") else joined
        if route.endswith("/index"):
            route = route[: -len("/index")]
        if route in ("index", "."):
            route = ""
        q = m.group("q")
        return f"href={q}{route_prefix.rstrip('/')}/{route}{q}".replace("//", "/")
    return HTML_MD_HREF.sub(repl, body)


def local_for_embed(url, available):
    """Local asset filename backing a GitBook storage URL, if there is one.

    Embeds keep pointing at signed files.gitbook.com URLs even in the export,
    while the file itself is committed under .gitbook/assets. Nothing links the
    two but the trailing filename, so match on that — otherwise the site keeps a
    hard dependency on GitBook hosting and the media dies with the space.
    """
    # The storage path keeps its separators percent-encoded, so unquote before
    # splitting or the "filename" comes back as spaces/<id>/uploads/<id>/name.
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
    name = path.rsplit("/", 1)[-1] if path else ""
    return name if name and name in available else ""


def convert_body(body, asset_prefix, used_assets, unresolved, available_assets=()):
    body = HINT.sub(
        lambda m: f":::{ADMONITION.get(m.group('style'), 'note')}\n\n"
                  f"{m.group('body').strip()}\n\n:::", body)

    def embed(m):
        url, caption = m.group("url").strip(), m.group("caption").strip()
        if url.lower().split("?")[0].endswith(VIDEO_EXT):
            local = local_for_embed(url, available_assets)
            if local:
                used_assets.add(local)
                src = served_asset(local, asset_prefix)
            else:
                src = url
                unresolved.append(f"embed still remote, no local asset: {url[:70]}")
            block = f'<video controls width="100%">\n  <source src="{src}" />\n</video>'
            return f"{block}\n\n{caption}\n" if caption else f"{block}\n"
        unresolved.append(f"non-video embed: {url}")
        return f"[{caption or url}]({url})\n"
    body = EMBED.sub(embed, body)

    def broken(m):
        unresolved.append(f"broken:// link in GitBook: {m.group('text') or 'no text'}")
        return m.group("text")
    body = BROKEN_LINK.sub(broken, body)

    body = TABS.sub("", body)
    body = LEFTOVER.sub("", body)

    def asset_name(raw):
        return html.unescape(urllib.parse.unquote(raw)).strip()

    def attr_sub(m):
        name = asset_name(m.group("name"))
        used_assets.add(name)
        q = m.group("q")
        return f"{m.group('attr')}={q}{served_asset(name, asset_prefix)}{q}"
    body = ASSET_ATTR.sub(attr_sub, body)

    def md_sub(m):
        name = asset_name(m.group("name"))
        used_assets.add(name)
        return f"]({served_asset(name, asset_prefix)})"
    body = ASSET_MD.sub(md_sub, body)

    if ASSET_ANY.search(body):
        unresolved.append("asset path left unrewritten (unexpected syntax)")

    body = MD_LINK_README.sub(lambda m: f"]({m.group('pre')}index.md{m.group('post')})", body)
    body = HREF_README.sub(lambda m: f'href="{m.group("pre")}index.md{m.group("post")}"', body)
    body = VOID_TAG.sub(
        lambda m: f'<{m.group("tag")}{m.group("attrs").rstrip().rstrip("/")} />', body)
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="GitBook Git Sync checkout")
    ap.add_argument("--out", default="docs")
    ap.add_argument("--assets-out", default="static/gitbook/assets")
    ap.add_argument("--asset-prefix", default="/districts/gitbook/assets")
    ap.add_argument("--sidebar-out", default="sidebars.generated.json")
    ap.add_argument("--route-prefix", default="/districts")
    args = ap.parse_args()

    summary_path = os.path.join(args.source, "SUMMARY.md")
    if not os.path.exists(summary_path):
        sys.exit(f"no SUMMARY.md in {args.source}; is that a Git Sync export?")
    with open(summary_path, encoding="utf-8") as fh:
        groups = parse_summary(fh.read())
    if not groups:
        sys.exit("SUMMARY.md parsed to zero groups")

    if os.path.isdir(args.out):
        shutil.rmtree(args.out)
    if os.path.isdir(args.assets_out):
        shutil.rmtree(args.assets_out)
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.assets_out, exist_ok=True)

    src_assets_dir = os.path.join(args.source, ".gitbook", "assets")
    available_assets = set(os.listdir(src_assets_dir)) if os.path.isdir(src_assets_dir) else set()
    used_assets, unresolved, missing = set(), [], []
    written = 0

    def emit(node):
        nonlocal written
        src = os.path.join(args.source, node["target"])
        if not os.path.exists(src):
            missing.append(node["target"])
            return
        with open(src, encoding="utf-8") as fh:
            raw = fh.read()

        fm = FRONTMATTER.match(raw)
        head = fm.group(0) if fm else ""
        body = raw[len(head):]
        cover = COVER.search(head)

        body = convert_body(body, args.asset_prefix, used_assets, unresolved,
                            available_assets)
        body = html_md_to_route(body, os.path.dirname(dest_path(node["target"])),
                                args.route_prefix)
        body = cards_from_table(body)
        # The label in SUMMARY.md is authoritative, so drop the page's own H1.
        body = re.sub(r"^#\s+.+$", "", body, count=1, flags=re.M).strip()

        if cover:
            name = html.unescape(urllib.parse.unquote(
                re.sub(r"^(?:\.\./)*\.gitbook/assets/", "", cover.group("path").strip())))
            used_assets.add(name)
            body = (f'<div class="gitbook-cover">\n'
                    f'  <img src="{served_asset(name, args.asset_prefix)}" alt="" />\n'
                    f"</div>\n\n" + body)

        ident = doc_id(node["target"])
        fmo = ["---"]
        # A frontmatter id replaces only the last path segment and may not
        # contain a slash, so it is set solely for the root page; every other
        # id is derived from the file path.
        if ident == "introduction":
            fmo += [f"id: {json.dumps(ident)}", "slug: /"]
        fmo += [f"title: {json.dumps(node['label'])}",
                f"sidebar_label: {json.dumps(node['label'])}",
                "---", ""]

        dest = os.path.join(args.out, dest_path(node["target"]))
        os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write("\n".join(fmo) + "\n" + body + "\n")
        written += 1
        for child in node["children"]:
            emit(child)

    def sidebar_node(node):
        ident = doc_id(node["target"])
        if not node["children"]:
            return {"type": "doc", "id": ident}
        return {"type": "category", "label": node["label"],
                "link": {"type": "doc", "id": ident},
                "collapsible": True, "collapsed": True,
                "items": [sidebar_node(c) for c in node["children"]]}

    sidebar = []
    for label, items in groups:
        for node in items:
            emit(node)
        # GitBook renders groups as always-open headings, not accordions.
        sidebar.append({"type": "category", "label": label,
                        "collapsible": False, "collapsed": False,
                        "items": [sidebar_node(n) for n in items]})

    with open(args.sidebar_out, "w", encoding="utf-8") as fh:
        json.dump(sidebar, fh, indent=2)
        fh.write("\n")

    src_assets = os.path.join(args.source, ".gitbook", "assets")
    copied = 0
    for name in sorted(used_assets):
        src = os.path.join(src_assets, name)
        if not os.path.exists(src):
            unresolved.append(f"missing asset: {name}")
            continue
        shutil.copy2(src, os.path.join(args.assets_out, name))
        copied += 1
    orphans = 0
    if os.path.isdir(src_assets):
        orphans = len([n for n in os.listdir(src_assets) if n not in used_assets])

    print(f"wrote {written} pages into {args.out}/")
    print(f"sidebar: {len(sidebar)} groups -> {args.sidebar_out}")
    print(f"assets: copied {copied} referenced, skipped {orphans} unreferenced")
    if missing:
        print(f"\n{len(missing)} SUMMARY entry(ies) with no file:", file=sys.stderr)
        for t in missing:
            print(f"  {t}", file=sys.stderr)
    if unresolved:
        print(f"\n{len(unresolved)} unresolved reference(s):", file=sys.stderr)
        for u in sorted(set(unresolved)):
            print(f"  {u}", file=sys.stderr)


if __name__ == "__main__":
    main()
