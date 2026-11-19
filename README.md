# Mindfully Priya - website

Static rebuild of www.mindfullypriya.com (currently on Wix) with a fresh design,
ready to deploy on Vercel. Same content and photos as the live site; every page
keeps its Wix URL so search rankings carry over.

## Layout

- `content/` - one Markdown file per page, path = URL (`content/post/x.md` -> `/post/x`).
  Front matter sets `title`, `description` (meta tags, copied from Wix), and
  `layout` (`page`, `post` or `html`), `eyebrow`, `heading`, `lede`, `image`.
- `templates/` - `base.html` (header, footer), `page.html`, `post.html`.
- `assets/site.css` - the whole design system; tokens at the top.
- `public/` - build output that Vercel serves. Images live in `public/images/`.
- `_source/` - the scraped Wix pages the content was built from (reference only).

## Build and preview

    pip install markdown
    python3 build.py
    npx serve public        # http://localhost:3000

## Deploy

GitHub (public repo; main cannot be force-pushed or deleted) is linked to Vercel. Vercel runs `build.py` itself
(`buildCommand` in `vercel.json`): every pull request gets a preview link with
drafts included, and merging to `main` publishes the live site without drafts.
Priya changes and publishes the site herself through Claude Code; see `CLAUDE.md` for its rules.
Move the domain from Wix only once booking, forms and the shop are replaced:
links to `/booking-calendar/...`, `/challenge-page/...` and product checkout
still point at the Wix site.
