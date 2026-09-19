"""One-off: turn the scraped Wix pages in _source/*.txt into content/*.md drafts."""
import glob, os, re
SKIP_IMG = {'2174360aba', '9e78da3320', '0fdef75120', '01c3aff52f', '6ea5b4a88f', '11062b_9e78'}
have = {os.path.splitext(f)[0] for f in os.listdir('public/images')}
for f in sorted(glob.glob('_source/*.txt')):
    txt = open(f).read()
    head, _, imgs = txt.partition('\nIMAGES\n')
    lines = head.split('\n')
    url = lines[0][4:]; title = lines[1][6:]; desc = lines[2][5:]
    body = lines[4:]
    # drop Wix chrome: nav + site banner at top, footer at bottom
    start = next((i for i, l in enumerate(body) if l.startswith("h1: You've built a life")), -1) + 1
    out, seen = [], set()
    for l in body[start:]:
        if l.startswith('span: bottom of page') or l.startswith('h2: Recent Posts'): break
        tag, _, t = l.partition(': ')
        t = t.replace('​', '').strip()
        if not t or t in ('top of page',): continue
        t = t.replace('https://www.mindfullypriya.com', '').replace('https://mindfullypriya.com', '')
        if tag == 'a':
            m = re.match(r'\[(.*)\]\((.*)\)$', t)
            out.append(f'[{m.group(1)}]({m.group(2) or "/"}){{.btn}}' if m else t); continue
        if tag[0] == 'h' and tag[1:].isdigit(): out.append('#' * min(int(tag[1:]), 4) + ' ' + t)
        elif tag == 'li': out.append('- ' + t)
        else: out.append(t)
    md, prev = [], ''
    for o in out:
        if o.startswith('- ') and prev.startswith('- '): md[-1] += '\n' + o
        else: md.append(o)
        prev = o
    ids = []
    for l in imgs.split('\n'):
        m = re.search(r'(?:dddd96|11062b)_([0-9a-f]{10})', l)
        if m and m.group(1) in have and m.group(1) not in SKIP_IMG and m.group(1) not in ids:
            ids.append(m.group(1))
    slug = url.strip('/').strip() or 'index'
    path = 'content/' + slug + '.md'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fm = f'---\ntitle: {title}\ndescription: {desc[:300]}\nimages: {" ".join(ids)}\n---\n\n'
    open(path, 'w').write(fm + '\n\n'.join(md) + '\n')
    print(path, len(md), ids)
