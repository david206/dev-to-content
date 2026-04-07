#!/usr/bin/env python3

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://dev.to/api"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export DEV posts as markdown and JSON metadata."
    )
    parser.add_argument(
        "--username",
        help="DEV username. Required for public exports. Omit when using DEVTO_API_KEY to export your own full archive.",
    )
    parser.add_argument(
        "--output-dir",
        default="exports",
        help="Directory to write exported files into. Default: exports",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=100,
        help="Number of posts to request per page. Default: 100",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("DEVTO_API_KEY"),
        help="DEV API key. Defaults to DEVTO_API_KEY if set.",
    )
    parser.add_argument(
        "--published-only",
        action="store_true",
        help="With an API key, export only your published posts instead of all posts.",
    )
    return parser.parse_args()


def build_headers(api_key: Optional[str]) -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": "dev-to-content-exporter/1.0",
    }
    if api_key:
        headers["api-key"] = api_key
    return headers


def request_json(path: str, headers: Dict[str, str], params: Optional[Dict] = None):
    url = f"{BASE_URL}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    req = Request(url, headers=headers)
    with urlopen(req) as resp:
        return json.load(resp)


def iter_articles(
    username: Optional[str],
    headers: Dict[str, str],
    per_page: int,
    use_authenticated_archive: bool,
    published_only: bool,
) -> Iterable[Dict]:
    page = 1

    while True:
        if use_authenticated_archive:
            endpoint = "/articles/me/published" if published_only else "/articles/me/all"
            payload = request_json(endpoint, headers, {"page": page, "per_page": per_page})
        else:
            payload = request_json(
                "/articles", headers, {"username": username, "page": page, "per_page": per_page}
            )

        if not payload:
            return

        for article in payload:
            yield article

        page += 1


def fetch_article_detail(article: Dict, headers: Dict[str, str]) -> Dict:
    if article.get("body_markdown"):
        return article
    return request_json(f"/articles/{article['id']}", headers)


def sanitize_filename(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "post"


def render_front_matter(article: Dict) -> str:
    tags = article.get("tag_list") or []
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    lines = [
        "---",
        f'title: {json.dumps(article.get("title", ""))}',
        f"devto_id: {article.get('id')}",
        f'slug: {json.dumps(article.get("slug", ""))}',
        f'url: {json.dumps(article.get("url", ""))}',
        f'published: {str(bool(article.get("published"))).lower()}',
        f'published_at: {json.dumps(article.get("published_at"))}',
        f'description: {json.dumps(article.get("description"))}',
        "tags:",
    ]
    lines.extend(f"  - {json.dumps(tag)}" for tag in tags)
    lines.append("---")
    return "\n".join(lines)


def write_article(article: Dict, output_dir: Path) -> Path:
    date_prefix = (article.get("published_at") or article.get("created_at") or "undated")[:10]
    filename = sanitize_filename(f"{date_prefix}-{article.get('slug') or article.get('id')}")
    markdown_path = output_dir / f"{filename}.md"
    metadata_path = output_dir / f"{filename}.json"

    body = article.get("body_markdown") or ""
    markdown = f"{render_front_matter(article)}\n\n{body.rstrip()}\n"
    markdown_path.write_text(markdown, encoding="utf-8")
    metadata_path.write_text(json.dumps(article, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return markdown_path


def main() -> int:
    if not args.username and not args.api_key:
        print(
            "error: provide --username for public exports or set DEVTO_API_KEY / --api-key for your own archive",
            file=sys.stderr,
        )
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    headers = build_headers(args.api_key)
    use_authenticated_archive = bool(args.api_key and not args.username)

    exported_files: List[str] = []
    try:
        for idx, article in enumerate(
            iter_articles(
                args.username,
                headers,
                args.per_page,
                use_authenticated_archive,
                args.published_only,
            ),
            start=1,
        ):
            detailed_article = fetch_article_detail(article, headers)
            path = write_article(detailed_article, output_dir)
            exported_files.append(path.name)
            print(f"[{idx}] exported {path.name}")
            time.sleep(0.05)
    except HTTPError as exc:
        print(f"HTTP error {exc.code}: {exc.reason}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Network error: {exc.reason}", file=sys.stderr)
        return 1

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "count": len(exported_files),
                "files": exported_files,
                "mode": "authenticated" if use_authenticated_archive else "public",
                "username": args.username,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Exported {len(exported_files)} posts into {output_dir}")
    return 0


args = parse_args()


if __name__ == "__main__":
    raise SystemExit(main())
