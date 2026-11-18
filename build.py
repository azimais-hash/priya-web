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
    ('/reclamation', 'Reclamation'),
    ('/for-organisations', 'Organisations'),
    ('/south-asian-midlife', 'South Asian Midlife'),
    ('/mindfully-priya-coaching', 'About'),
    ('/reconnection', 'The Reconnection'),
    ('/blog', 'Insights'),
]


# Every link that still depends on an external service lives here, so swapping
# Wix for Cal.com, Stripe and Tally is one edit rather than thirty.
# Tokens are written in content as {{LINK:NAME}}.
LINKS = {
    # Booking: Cal.com (hello@mindfullypriya.com). The 30 minute type is the
    # complimentary call every page routes to; the 15 minute one is a quick chat.
    'BOOK_DISCOVERY': 'https://cal.com/mindfullypriya/30min',
    'BOOK_DISCOVERY_CALL': 'https://cal.com/mindfullypriya/30min',
    # Lowry Legal clients' free hour. Paste the dedicated 60-minute booking link
    # here when it exists; until then every button jumps to the booking section.
    'LOWRY_BOOKING': '#book',
    'BOOK_SHORT': 'https://cal.com/mindfullypriya/15min',
    # Paid sessions are arranged on the call and invoiced, so they route to the
    # same call rather than a checkout.
    'BOOK_CLARITY': 'https://cal.com/mindfullypriya/30min',
    'BOOK_CAREER_RESET': 'https://cal.com/mindfullypriya/30min',
    # Forms (Tally). Programme places are taken by enquiry, no payment on the site.
    'FORM_RECONNECTION': 'https://tally.so/r/yPoRo4',
    'FORM_PROGRAMME': 'https://tally.so/r/yPoRo4',
}


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


# The mailbox the approvals job reads (NOTIFY_SMTP_USER in /root/priya-site/.env).
REVIEW_TO = os.environ.get('REVIEW_TO', 'horizon.esg@gmail.com')
# Draft PAGES (as opposed to articles) are swapped in by hand, so their verdict
# goes to a person rather than the automated approvals mailbox.
PAGE_REVIEW_TO = os.environ.get('PAGE_REVIEW_TO', 'azim.khan@ais-consulting.co.uk')


def hero_extra(m):
    """Optional hero calls to action and a one-line proof strip, from front matter."""
    links = []
    if m.get('cta1'):
        links.append(f'<a class="btn btn-accent" href="{m.get("cta1_href", "")}">{html.escape(m["cta1"])}</a>')
    if m.get('cta2'):
        links.append(f'<a class="btn-link" href="{m.get("cta2_href", "")}">{html.escape(m["cta2"])}</a>')
    out = f'<p class="lede">{m["lede2"]}</p>' if m.get('lede2') else ''
    out += f'<div class="actions">{"".join(links)}</div>' if links else ''
    if m.get('proof'):
        out += f'<p class="hero-proof">{html.escape(m["proof"])}</p>'
    for key, val in LINKS.items():
        out = out.replace('{{LINK:' + key + '}}', val)
    return out


REVIEW_JS = """<script>
(function () {
  var f = document.getElementById('rv-form');
  if (!f) return;
  var st = f.querySelector('.rv-status'), msg = f.querySelector('#rv-msg');
  function send(verdict, text, done) {
    st.textContent = 'Sending...';
    fetch('/api/review', {method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({page: f.dataset.page, verdict: verdict, message: text,
        company_website: f.elements['company_website'].value})})
      .then(function (r) { return r.json().then(function (j) { if (!r.ok || !j.ok) throw j; }); })
      .then(function () { st.textContent = done; })
      .catch(function () {
        st.textContent = 'That did not send from the page, so your email app is opening with it filled in. Please press Send there.';
        var base = verdict === 'approve' ? f.dataset.approve : f.dataset.mailto;
        location.href = base + encodeURIComponent(text);
      });
  }
  document.querySelector('[data-rv="changes"]').addEventListener('click', function () {
    f.hidden = false; msg.focus();
  });
  document.querySelector('[data-rv="approve"]').addEventListener('click', function () {
    f.hidden = false; send('approve', '', 'Thank you, your approval has been sent to Azim.');
  });
  f.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!msg.value.trim()) { st.textContent = 'Please write what you would like changed.'; msg.focus(); return; }
    send('changes', msg.value, 'Thank you, your changes have been sent to Azim.');
  });
})();
</script>"""


def review_bar(page):
    """Approval banner shown only on unpublished drafts."""
    slug = page['rel'].split('/')[-1]
    if not page['rel'].startswith('post/'):
        live = page['meta'].get('replaces', '')
        approve = (f'mailto:{PAGE_REVIEW_TO}?subject=APPROVED%20page%20{slug}'
                   f'&body=Please%20make%20this%20page%20live.')
        changes = (f'mailto:{PAGE_REVIEW_TO}?subject=Changes%20to%20page%20{slug}'
                   f'&body=What%20I%27d%20like%20changed%3A%0A%0A')
        return (f'<div class="review-bar"><div class="wrap review-inner">'
                f'<div><p class="review-tag">Draft page for review</p>'
                f'<p class="review-note">Nobody can find this page. It is not linked '
                f'anywhere and it is hidden from Google. When you approve it, it '
                + (f'replaces the live page at {html.escape(live)}.' if live else
                   f'goes live at /{slug}, still hidden from Google and the menus.')
                + '</p></div>'
                f'<div class="review-actions">'
                f'<button class="btn btn-accent" type="button" data-rv="approve">Approve</button>'
                f'<button class="btn" type="button" data-rv="changes">Ask for changes</button>'
                f'</div></div>'
                f'<form class="wrap review-form" id="rv-form" hidden data-page="{slug}" '
                f'data-mailto="{changes}" data-approve="{approve}">'
                f'<label for="rv-msg">What would you like changed?</label>'
                f'<textarea id="rv-msg" rows="8"></textarea>'
                f'<input class="hp" name="company_website" tabindex="-1" autocomplete="off" aria-hidden="true">'
                f'<p class="rv-status" role="status"></p>'
                f'<button class="btn btn-accent" type="submit">Send to Azim</button>'
                f'</form></div>' + REVIEW_JS)
    title = page['meta'].get('heading') or page['meta']['title']
    approve = (f'mailto:{REVIEW_TO}?subject=APPROVE%20{slug}'
               f'&body=Publish%20this%20one.%20(Sent%20from%20the%20preview%20page.)')
    changes = (f'mailto:{REVIEW_TO}?subject=CHANGES%20{slug}'
               f'&body=What%20I%27d%20like%20changed%20(you%20can%20attach%20a%20photo%20for%20the%20cover)%3A%0A%0A')
    return (f'<div class="review-bar"><div class="wrap review-inner">'
            f'<div><p class="review-tag">Draft for review</p>'
            f'<p class="review-note">Nobody can find this page. It is not linked '
            f'anywhere, and it is hidden from Google. Approving publishes it to '
            f'the Insights page at this same address. Ask for changes and they are '
            f'made for you, then you get an email to check them.</p></div>'
            f'<div class="review-actions">'
            f'<a class="btn btn-accent" href="{approve}">Approve and publish</a>'
            f'<a class="btn" href="{changes}">Send back for changes</a>'
            f'</div></div></div>')


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

    # Drafts only exist on preview links; the live site never builds them,
    # so a draft merged to main stays unpublished until "draft: true" is removed.
    if os.environ.get('VERCEL_ENV') == 'production':
        pages = [p for p in pages if p['meta'].get('draft') != 'true']

    posts = sorted((p for p in pages if p['rel'].startswith('post/')
                    and p['meta'].get('draft') != 'true'),
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
        for key, val in LINKS.items():
            body = body.replace('{{LINK:' + key + '}}', val)
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
                             hero_extra=hero_extra(m),
                             date=fmt_date(post_date(m)) if layout == 'post' else '',
                             read=m.get('read', ''),
                             content=content,
                             extra=extra)
        if m.get('draft') == 'true':
            main_html = review_bar(p) + main_html
        out = fill(base,
                   robots=('<meta name="robots" content="noindex, nofollow">'
                           if m.get('draft') == 'true' or m.get('hidden') == 'true' else
                           '<meta name="robots" content="noindex, follow">'
                           if m.get('noindex') == 'true' else ''),
                   analytics='<script defer src="/_vercel/insights/script.js"></script>',
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

    wanted = {os.path.join(PUBLIC, p['rel'] + '.html') for p in pages}
    for dirpath, _, files in os.walk(PUBLIC):
        for f in files:
            path = os.path.join(dirpath, f)
            if f.endswith('.html') and path not in wanted:
                os.remove(path)

    for asset in ('site.css', 'site.js'):
        shutil.copy(os.path.join(ROOT, 'assets', asset), os.path.join(PUBLIC, asset))

    urls = sorted(BASE_URL + ('' if p['url'] == '/' else p['url']) for p in pages
                  if p['meta'].get('noindex') != 'true' and p['meta'].get('draft') != 'true'
                  and p['meta'].get('hidden') != 'true')
    with open(os.path.join(PUBLIC, 'sitemap.xml'), 'w') as fh:
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        fh.writelines(f'  <url><loc>{u}</loc></url>\n' for u in urls)
        fh.write('</urlset>\n')
    with open(os.path.join(PUBLIC, 'robots.txt'), 'w') as fh:
        fh.write(f'User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n')
    print(f'built {len(pages)} pages, {len(posts)} posts')


if __name__ == '__main__':
    main()
