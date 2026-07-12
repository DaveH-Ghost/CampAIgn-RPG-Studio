# Scene decoration images

Upload images from the **Scene decorations** panel (**Browse…** or **+ Sprite** / **+ Background**). Files are saved here and referenced as `assets/your-file.png` in decorations.

Uploaded images are **gitignored** — they stay on your machine only and are not committed to the repo.

Re-selecting an image that already exists in this folder (same file contents) reuses the existing path instead of creating a duplicate.

Supported: PNG, JPG, GIF, WebP, SVG (max 10 MB). Sprite decorations may use negative **X** / **Y** to extend art beyond the grid edges.

Paths resolve to `/static/assets/...` in the Studio UI.
