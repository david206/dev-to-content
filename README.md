# dev-to-content

Export your DEV posts into local Markdown, JSON, and downloaded image assets.

## What it does

The script paginates through your DEV posts and writes:

- one `.md` file per post with front matter and the original `body_markdown`
- one `.json` file per post with the raw API response
- downloaded cover images when available
- downloaded image URLs referenced in each post's Markdown or inline HTML
- one `manifest.json` file listing the exported files

## Requirements

- Python 3.11+

## Usage

Export a user's public published posts:

```bash
python3 fetch_devto_posts.py --username your_devto_username
```

Export your own full archive, including drafts and unpublished posts:

```bash
export DEVTO_API_KEY=your_devto_api_key
python3 fetch_devto_posts.py
```

Export only your published posts with an API key:

```bash
export DEVTO_API_KEY=your_devto_api_key
python3 fetch_devto_posts.py --published-only
```

Choose a different output folder:

```bash
python3 fetch_devto_posts.py --username your_devto_username --output-dir devto-export
```

## Notes

- If you pass `--username`, the script uses DEV's public articles endpoint.
- If you omit `--username` and provide `DEVTO_API_KEY`, the script uses the authenticated archive endpoints.
- Exported files are written into `exports/` by default.
- Downloaded images are stored under `exports/assets/<post-slug>/`.
- The script does not rewrite Markdown image URLs yet; it only downloads the files locally.
