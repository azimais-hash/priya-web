"""Build the static site: content/**/*.md -> public/**/*.html.

Every page keeps the URL it had on Wix, so rankings carry over. Run with
`python3 build.py`; output lands in public/, which Vercel serves as-is.
"""
import html
import os
import re
import shutil
from datetime import datetime

import markdown

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, 'content')
PUBLIC = os.path.join(ROOT, 'public')
TEMPLATES = os.path.join(ROOT, 'templates')
BASE_URL = 'https://www.mindfullypriya.com'

NAV = [
    ('/one-to-one-coaching-programs', '1:1 Coaching'),
    ('/general-7', 'Reclamation Programme'),
    ('/general-6', 'Corporate'),
    ('/event-list', 'Programmes'),
    ('/mindfully-priya-coaching', 'About'),
    ('/blog', 'Journal'),
    ('/shop', 'Shop'),
]


def read_page(path):
    """Split a content file into (front matter dict, markdown body)."""
    text = open(path, encoding='utf-8').read()
    meta = {}
    if text.startswith('---\n'):
        head, _, text = text[4:].partition('\n---\n')
        for line in head.splitlines():
            if ':' in line:
                k, _, v = line.partition(':')
                meta[k.strip()] = v.strip()
    return meta, text


def render_md(body):
    return markdown.markdown(body, extensions=['attr_list', 'md_in_html', 'tables', 'smarty'])


def template(name):
    return open(os.path.join(TEMPLATES, name), encoding='utf-8').read()


def fill(tpl, **kw):
    return re.sub(r'\{\{(\w+)\}\}', lambda m: str(kw.get(m.group(1), '')), tpl)


def nav_html(url):
    items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if url == href or url.startswith(href + '/') else ''
        items.append(f'<li><a href="{href}"{cur}>{label}</a></li>')
    return '\n'.join(items)


def image_tag(img_id, alt='', cls='', sizes='100vw', eager=False):
    if not img_id:
        return ''
    ext = 'png' if os.path.exists(os.path.join(PUBLIC, 'images', img_id + '.png')) else 'jpg'
    load = 'eager' if eager else 'lazy'
    c = f' class="{cls}"' if cls else ''
    return f'<img src="/images/{img_id}.{ext}" alt="{html.escape(alt)}"{c} loading="{load}" decoding="async">'


def post_date(meta):
    try:
        return datetime.strptime(meta.get('date', ''), '%Y-%m-%d')
    except ValueError:
        return datetime(2000, 1, 1)


def fmt_date(d):
    return d.strftime('%-d %B %Y')


def post_card(p):
    m = p['meta']
    return (f'<a class="card" href="{p["url"]}">'
            f'<span class="card-img">{image_tag(m.get("image"), m.get("title", ""))}</span>'
            f'<span class="card-meta">{fmt_date(post_date(m))} &middot; {m.get("read", "")}</span>'
            f'<span class="card-title">{html.escape(m.get("heading") or m["title"])}</span></a>')


def main():
    pages = []
    for dirpath, _, files in os.walk(CONTENT):
        for f in files:
            if not f.endswith('.md'):
                continue
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, CONTENT)[:-3]
            url = '/' if rel == 'index' else '/' + rel
            meta, body = read_page(path)
            pages.append({'rel': rel, 'url': url, 'meta': meta, 'body': body})

    posts = sorted((p for p in pages if p['rel'].startswith('post/')),
                   key=lambda p: post_date(p['meta']), reverse=True)
    blocks = {
        'POSTS': '<div class="cards">' + ''.join(post_card(p) for p in posts) + '</div>',
        'LATEST_POSTS': '<div class="cards">' + ''.join(post_card(p) for p in posts[:3]) + '</div>',
    }

    base = template('base.html')
    for p in pages:
        m, body = p['meta'], p['body']
        for key, val in blocks.items():
            body = body.replace('{{' + key + '}}', val)
        layout = m.get('layout', 'page')
        if layout == 'html':
            main_html = body
        else:
            content = render_md(body)
            hero_img = image_tag(m.get('image'), m.get('image_alt', ''), 'hero-img', eager=True)
            extra = ''
            if layout == 'post':
                others = [q for q in posts if q is not p][:3]
                extra = ('<section class="band band-sand"><div class="wrap"><p class="eyebrow">Keep reading</p>'
                         '<div class="cards">' + ''.join(post_card(q) for q in others) + '</div></div></section>')
            main_html = fill(template(layout + '.html'),
                             eyebrow=m.get('eyebrow', ''),
                             heading=m.get('heading') or m['title'].split(' | ')[0],
                             lede=m.get('lede', ''),
                             image=hero_img,
                             date=fmt_date(post_date(m)) if layout == 'post' else '',
                             read=m.get('read', ''),
                             content=content,
                             extra=extra)
        out = fill(base,
                   title=html.escape(m['title']),
                   description=html.escape(m.get('description', '')),
                   canonical=BASE_URL + ('' if p['url'] == '/' else p['url']),
                   og_image=BASE_URL + '/images/' + (m.get('image') or '3a4833976c') + '.jpg',
                   nav=nav_html(p['url']),
                   body_class='page-' + (p['rel'].split('/')[0]),
                   main=main_html,
                   year=datetime.now().year)
        dest = os.path.join(PUBLIC, p['rel'] + '.html')
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, 'w', encoding='utf-8').write(out)

    for asset in ('site.css', 'site.js'):
        shutil.copy(os.path.join(ROOT, 'assets', asset), os.path.join(PUBLIC, asset))

    urls = sorted(BASE_URL + ('' if p['url'] == '/' else p['url']) for p in pages if p['meta'].get('noindex') != 'true')
    with open(os.path.join(PUBLIC, 'sitemap.xml'), 'w') as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        fh.writelines(f'  <url><loc>{u}</loc></url>\n' for u in urls)
        fh.write('</urlset>\n')
    with open(os.path.join(PUBLIC, 'robots.txt'), 'w') as fh:
        fh.write(f'User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n')
    print(f'built {len(pages)} pages, {len(posts)} posts')


if __name__ == '__main__':
    main()
