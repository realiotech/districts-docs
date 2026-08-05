#!/usr/bin/env python3
"""Convert GitBook markdown into the docs/ tree Docusaurus expects.

Two sources are supported:

  --source DIR   a GitBook Git Sync checkout (preferred: assets are real files)
  --fetch URL    the published site, using its llms.txt index and .md endpoints

Ordering comes from llms.txt when fetching, or SUMMARY.md when reading a Git Sync
checkout. Either way page order becomes sidebar_position so the sidebar matches
the order GitBook showed.
"""

import argparse
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

BOILERPLATE = re.compile(
    r"^>\s*For the complete documentation index.*?\n\n", re.S | re.M
)
# The url is percent-encoded and wrapped in angle brackets, so the character
# class must admit '%' and stop only at '>' or the closing quote.
EMBED = re.compile(r"\{%\s*embed\s+url=\"?<?(?P<url>[^\">\s]+)>?\"?[^%]*?%\}"
                   r"(?P<caption>.*?)\{%\s*endembed\s*%\}", re.S)
FILE_REF = re.compile(r"""(?P<attr>src|href)=["']/files/(?P<fid>[A-Za-z0-9_-]+)["']""")
# GitBook card tables target pages by internal id; only Git Sync/the API can map them.
PAGE_REF = re.compile(r"""(?P<attr>href)=["']/pages/(?P<pid>[A-Za-z0-9_-]+)["']""")
# GitBook's own marker for a link it could not resolve.
BROKEN_LINK = re.compile(r"\[(?P<text>[^\]]*)\]\(broken://[^)]*\)")
# MDX parses JSX, so void elements must be self-closing or the page fails to build.
VOID_TAG = re.compile(
    r"<(?P<tag>img|br|hr|input|source|col|area|base|link|meta|param|track|wbr)"
    r"(?P<attrs>(?:\s[^>]*?)?)\s*/?>", re.I)
HINT = re.compile(r"\{%\s*hint style=\"(?P<style>\w+)\"\s*%\}(?P<body>.*?)\{%\s*endhint\s*%\}", re.S)
CONTENT_REF = re.compile(r"\{%\s*content-ref url=\"(?P<url>[^\"]+)\"\s*%\}.*?\{%\s*endcontent-ref\s*%\}", re.S)
# GitBook writes internal links site-absolute and keeps the .md suffix, e.g.
# ](/districts/general/introduction.md). Docusaurus resolves relative .md paths.
MD_LINK = re.compile(r"\]\((?P<target>/[^)\s]+\.md)(?P<frag>#[^)]*)?\)")
TABS = re.compile(r"\{%\s*tabs?\s*%\}|\{%\s*endtabs?\s*%\}|\{%\s*tab title=\"[^\"]*\"\s*%\}|\{%\s*endtab\s*%\}")
LEFTOVER = re.compile(r"\{%.*?%\}", re.S)
ADMONITION = {"info": "info", "warning": "caution", "danger": "danger",
              "success": "tip", "tip": "tip"}
VIDEO_EXT = (".mp4", ".webm", ".mov", ".m4v")


def _ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "gitbook-import"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as r:
            return r.read()
    except urllib.error.URLError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        # Framework python builds on macOS often ship without a CA bundle.
        out = subprocess.run(["curl", "-sSL", "--max-time", "30", url],
                             capture_output=True, check=False)
        if out.returncode != 0:
            raise SystemExit(
                f"TLS verification failed and curl fallback failed for {url}.\n"
                f"Install certifi (pip install certifi) or use --source.\n"
                f"{out.stderr.decode(errors='replace').strip()}"
            ) from exc
        return out.stdout


def pages_from_llms(base):
    """Return [(title, relpath)] in document order from the site's llms.txt."""
    text = fetch(f"{base.rstrip('/')}/llms.txt").decode("utf-8")
    out, seen = [], set()
    for title, url in re.findall(r"\[([^\]]+)\]\((https?://[^)]+\.md)\)", text):
        rel = urllib.parse.urlparse(url).path
        prefix = urllib.parse.urlparse(base).path.rstrip("/")
        if prefix and rel.startswith(prefix):
            rel = rel[len(prefix):]
        rel = rel.lstrip("/")
        if rel not in seen:
            seen.add(rel)
            out.append((title, rel))
    return out


def pages_from_summary(source):
    """Return [(title, relpath)] in SUMMARY.md order, falling back to a walk."""
    summary = os.path.join(source, "SUMMARY.md")
    out, seen = [], set()
    if os.path.exists(summary):
        with open(summary, encoding="utf-8") as fh:
            for title, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", fh.read()):
                rel = target.split("#")[0].lstrip("./")
                if rel.endswith(".md") and rel not in seen:
                    seen.add(rel)
                    out.append((title, rel))
    for root, _, files in os.walk(source):
        for name in sorted(files):
            if not name.endswith(".md") or name == "SUMMARY.md":
                continue
            rel = os.path.relpath(os.path.join(root, name), source)
            if rel not in seen:
                seen.add(rel)
                out.append((None, rel))
    return out


def first_heading(body):
    m = re.search(r"^#\s+(.+)$", body, re.M)
    return m.group(1).strip() if m else None


def convert_embeds(body, unresolved):
    def repl(m):
        url, caption = m.group("url").strip(), m.group("caption").strip()
        if url.lower().split("?")[0].endswith(VIDEO_EXT):
            block = (f'<video controls width="100%">\n'
                     f'  <source src="{url}" />\n'
                     f'</video>')
            return f"{block}\n\n{caption}\n" if caption else f"{block}\n"
        unresolved.append(url)
        label = caption or url
        return f"[{label}]({url})\n"
    return EMBED.sub(repl, body)


def convert_hints(body):
    def repl(m):
        kind = ADMONITION.get(m.group("style"), "note")
        inner = m.group("body").strip()
        return f":::{kind}\n\n{inner}\n\n:::"
    return HINT.sub(repl, body)


def relink(body, rel, prefix):
    """Rewrite GitBook's site-absolute .md links to paths relative to this page."""
    cur_dir = os.path.dirname(rel)

    def repl(m):
        target = m.group("target")
        if prefix and target.startswith(prefix.rstrip("/") + "/"):
            target = target[len(prefix.rstrip("/")) + 1:]
        else:
            target = target.lstrip("/")
        new = os.path.relpath(target, cur_dir) if cur_dir else target
        if not new.startswith("."):
            new = "./" + new
        return f"]({new}{m.group('frag') or ''})"

    return MD_LINK.sub(repl, body)


def convert(body, title, position, assets, unresolved_files, rel="", prefix="",
            is_root=False):
    body = BOILERPLATE.sub("", body, count=1)
    body = relink(body, rel, prefix)
    body = convert_hints(body)
    body = convert_embeds(body, unresolved_files)
    body = CONTENT_REF.sub(lambda m: f"[{m.group('url')}]({m.group('url')})", body)
    body = TABS.sub("", body)
    body = LEFTOVER.sub("", body)

    def file_repl(m):
        fid = m.group("fid")
        mapped = assets.get(fid)
        if mapped:
            return f'{m.group("attr")}="{mapped}"'
        unresolved_files.append(f"/files/{fid}")
        return f'{m.group("attr")}="/districts/img/missing/{fid}"'
    body = FILE_REF.sub(file_repl, body)

    def page_repl(m):
        pid = m.group("pid")
        mapped = assets.get(pid)
        if mapped:
            return f'{m.group("attr")}="{mapped}"'
        unresolved_files.append(f"/pages/{pid}")
        return f'{m.group("attr")}="#unresolved-{pid}"'
    body = PAGE_REF.sub(page_repl, body)

    def broken_repl(m):
        unresolved_files.append(f"broken:// link ({m.group('text') or 'no text'})")
        return m.group("text")
    body = BROKEN_LINK.sub(broken_repl, body)

    body = VOID_TAG.sub(
        lambda m: f'<{m.group("tag")}{m.group("attrs").rstrip().rstrip("/")} />', body)

    heading = first_heading(body)
    if heading:
        body = re.sub(r"^#\s+.+$", "", body, count=1, flags=re.M)
    label = title or heading or "Untitled"
    fm = ["---", f"title: {json.dumps(label)}", f"sidebar_label: {json.dumps(label)}",
          f"sidebar_position: {position}"]
    if is_root:
        # routeBasePath is '/', so one doc must claim the root or the site index 404s.
        fm.append("slug: /")
    fm += ["---", ""]
    return "\n".join(fm) + "\n" + body.strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--source", help="GitBook Git Sync checkout directory")
    src.add_argument("--fetch", help="published GitBook base URL")
    ap.add_argument("--out", default="docs")
    ap.add_argument("--assets", help="JSON map of GitBook file id -> served path")
    ap.add_argument("--root-page",
                    help="page whose slug becomes '/' (defaults to the first page)")
    ap.add_argument("--link-prefix",
                    help="site-absolute prefix to strip from internal links "
                         "(defaults to the --fetch URL path, e.g. /districts)")
    args = ap.parse_args()

    link_prefix = args.link_prefix
    if link_prefix is None:
        link_prefix = urllib.parse.urlparse(args.fetch).path if args.fetch else ""

    assets = {}
    if args.assets:
        with open(args.assets, encoding="utf-8") as fh:
            assets = json.load(fh)

    pages = pages_from_llms(args.fetch) if args.fetch else pages_from_summary(args.source)
    if not pages:
        sys.exit("no pages found")

    root_page = args.root_page or pages[0][1]
    if root_page not in {rel for _, rel in pages}:
        sys.exit(f"--root-page {root_page} is not one of the discovered pages")

    if os.path.isdir(args.out):
        shutil.rmtree(args.out)
    os.makedirs(args.out, exist_ok=True)

    unresolved = []
    counters = {}
    written = 0
    for title, rel in pages:
        if args.fetch:
            url = f"{args.fetch.rstrip('/')}/{rel}"
            try:
                body = fetch(url).decode("utf-8")
            except Exception as exc:                       # noqa: BLE001
                print(f"  skip {rel}: {exc}", file=sys.stderr)
                continue
        else:
            with open(os.path.join(args.source, rel), encoding="utf-8") as fh:
                body = fh.read()

        parent = os.path.dirname(rel)
        counters[parent] = counters.get(parent, 0) + 1
        dest = os.path.join(args.out, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(convert(body, title, counters[parent], assets, unresolved,
                             rel=rel, prefix=link_prefix,
                             is_root=(rel == root_page)))
        written += 1

    # A directory that is also a page becomes a category; give it a label.
    dirs = {os.path.dirname(rel) for _, rel in pages if os.path.dirname(rel)}
    for d in sorted(dirs):
        cat = os.path.join(args.out, d, "_category_.json")
        if os.path.exists(cat):
            continue
        label = d.split("/")[-1].replace("-", " ").title()
        with open(cat, "w", encoding="utf-8") as fh:
            json.dump({"label": label, "collapsible": True, "collapsed": True}, fh, indent=2)
            fh.write("\n")

    print(f"wrote {written} pages into {args.out}/ across {len(dirs)} categories")
    if unresolved:
        print(f"\n{len(unresolved)} unresolved reference(s) — supply --assets to fix:")
        for u in sorted(set(unresolved)):
            print(f"  {u}")


if __name__ == "__main__":
    main()
