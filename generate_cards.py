#!/usr/bin/env python3
"""Build self-contained SVGs for GitHub README image tags. Run STATIC=1 for screenshots."""
import base64
import calendar
import datetime as dt
import html
import json
import os
from collections import defaultdict
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'cards'
OUT.mkdir(exist_ok=True)
CONF = json.loads((ROOT / 'profile.json').read_text(encoding='utf-8'))
DATA_FILE = ROOT / 'data' / 'contributions.json'
DATA = json.loads(DATA_FILE.read_text(encoding='utf-8')) if DATA_FILE.exists() else {'days': []}
DAYS = {str(d['date']): max(0, int(d['count'])) for d in DATA.get('days', [])}
STATIC = os.getenv('STATIC', '0') == '1'
C = CONF['colors']
FG, MUTED, BG, PANEL, ACCENT, SECOND = (C[k] for k in ('text', 'muted', 'background', 'panel', 'accent', 'secondary'))
USER = CONF['username']


def esc(value):
    return html.escape(str(value), quote=True)


def font_css():
    """Subset local TTF and embed WOFF for reliable GitHub SVG-as-image text."""
    path = Path(CONF.get('font_file', '/usr/share/fonts/truetype/lato/Lato-Bold.ttf'))
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise FileNotFoundError(f'Missing font: {path}. Add a licensed .ttf you may embed.')
    # Text to subset, including all project names and labels used by the cards.
    corpus = json.dumps(CONF, ensure_ascii=False) + 'JanFebMarAprMayJunJulAugSepOctNovDec0123456789 • +–/:%()#@—↑'
    with TemporaryDirectory() as temp:
        dst = Path(temp) / 'subset.woff'
        args = ['pyftsubset', str(path), f'--text={corpus}', '--flavor=woff', f'--output-file={dst}', '--layout-features=*']
        p = run(args, capture_output=True, text=True)
        if p.returncode:
            raise RuntimeError('pyftsubset failed: ' + p.stderr[-800:])
        data = base64.b64encode(dst.read_bytes()).decode('ascii')
    return f"@font-face{{font-family:CardFont;src:url(data:font/woff;base64,{data}) format('woff');font-weight:100 900;}}"

FONT = font_css()


def svg(w, h, parts, delay=0):
    # Animation primitives remain in final positions when motion is disabled.
    motion = '' if STATIC else f'''
    @keyframes reveal{{from{{opacity:0;transform:translateY(17px)}}to{{opacity:1;transform:translateY(0)}}}}
    @keyframes trace{{from{{stroke-dashoffset:1400}}to{{stroke-dashoffset:0}}}}
    @keyframes glow{{0%,100%{{opacity:.45}}50%{{opacity:.85}}}}
    .entrance{{animation:reveal .85s both;animation-delay:{delay:.2f}s}}
    .pulse{{animation:glow 4s ease-in-out infinite;animation-delay:{delay:.2f}s}}
    .trace{{stroke-dasharray:1400;animation:trace 2s ease both;animation-delay:{delay+.3:.2f}s}}
    @media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation:none!important;transition:none!important}}}}
    '''
    style = f'''<style>{FONT}text{{font-family:CardFont,Arial,sans-serif}}{motion}</style>'''
    defs = f'''<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{ACCENT}"/><stop offset="1" stop-color="{SECOND}"/></linearGradient><linearGradient id="shade" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{PANEL}"/><stop offset="1" stop-color="{BG}"/></linearGradient></defs>'''
    body = f'<rect width="{w}" height="{h}" rx="24" fill="{BG}"/><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="23" fill="none" stroke="{ACCENT}" stroke-opacity=".29"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">{style}{defs}{body}<g class="entrance">{parts}</g></svg>'


def label(x, y, s, size=18, fill=None, weight=500, extra=''):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill or FG}" {extra}>{esc(s)}</text>'


def dot(x, y, radius=4, color=None):
    return f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{color or ACCENT}"/>'


def write(name, w, h, parts, delay):
    (OUT / name).write_text(svg(w,h,parts,delay), encoding='utf-8')


def image_data(path):
    p = ROOT / path
    if not p.is_file():
        return ''
    mime = {'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp'}.get(p.suffix.lower().lstrip('.'))
    return f'data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}' if mime else ''


def build_hero():
    p = f'<circle cx="750" cy="-50" r="250" fill="{ACCENT}" opacity=".07"/><circle cx="810" cy="300" r="150" fill="{SECOND}" opacity=".08"/>'
    p += f'<rect x="34" y="32" width="165" height="29" rx="14" fill="{ACCENT}" fill-opacity=".12"/>' + label(49,52,'✦  SOFTWARE DEVELOPER',12,ACCENT,700)
    p += label(36,137, CONF['name'], 53, FG, 800)
    p += label(38,183,CONF['tagline'],21,MUTED,500)
    p += f'<rect x="36" y="216" width="105" height="5" rx="3" fill="url(#g)"/>'
    portrait = image_data(CONF.get('portrait', ''))
    if portrait:
        p += '<defs><clipPath id="avatar"><circle cx="790" cy="134" r="86"/></clipPath></defs>'
        p += f'<image href="{portrait}" x="704" y="48" width="172" height="172" preserveAspectRatio="xMidYMid slice" clip-path="url(#avatar)"/>'
        p += f'<circle cx="790" cy="134" r="87" fill="none" stroke="{ACCENT}" stroke-width="3"/>'
    else:
        p += '<circle cx="795" cy="132" r="82" fill="url(#g)" opacity=".16"/>' + label(759,148,'</>',45,ACCENT,800)
    write('hero.svg', 960, 270, p, 0)


def build_tiles():
    for i, tile in enumerate(CONF['tiles'][:3]):
        p = f'<rect x="18" y="19" width="45" height="45" rx="14" fill="{ACCENT}" fill-opacity=".15"/>'
        p += label(30,50,tile.get('icon','↗'),25,ACCENT,800)
        p += label(20,105,tile['title'],25,FG,800)
        p += label(20,135,tile['subtitle'],14,MUTED)
        p += label(287,44,'↗',23,SECOND,800)
        write(f'tile-{i+1}.svg', 314, 164, p, 0.45 + .14*i)


def stats(days):
    today = dt.date.today()
    active = sum(v>0 for v in days.values())
    busiest_date, peak = max(days.items(), key=lambda item:item[1], default=('—',0))
    current = today if days.get(today.isoformat(),0) else today-dt.timedelta(days=1)
    streak = 0
    while days.get(current.isoformat(),0)>0:
        streak += 1
        current -= dt.timedelta(days=1)
    return active, busiest_date, peak, streak


def build_monthly():
    now = dt.date.today()
    months = []
    for offset in range(11,-1,-1):
        y = now.year + (now.month-1-offset)//12
        m = (now.month-1-offset)%12 + 1
        months.append((y,m))
    totals = defaultdict(int)
    for day, count in DAYS.items():
        try:
            d=dt.date.fromisoformat(day)
            totals[(d.year,d.month)] += count
        except ValueError:
            pass
    heights = [totals[key] for key in months]
    high = max(heights, default=0) or 1
    active, busiest, peak, streak = stats(DAYS)
    p = label(32,48,'CONTRIBUTION PULSE',21,FG,800)
    for i, (value, (year,month)) in enumerate(zip(heights, months)):
        x=47+i*75
        h=round(148*value/high) if value else 2
        p += f'<rect x="{x}" y="{254-h}" width="37" height="{h}" rx="7" fill="url(#g)"/>'
        p += label(x+18,274,calendar.month_abbr[month],13,MUTED,500,'text-anchor="middle"')
        p += label(x+18,248-h,str(value),12,FG,600,'text-anchor="middle"')
    p += f'<line x1="30" y1="256" x2="930" y2="256" stroke="{MUTED}" stroke-opacity=".22"/>'
    for i,(big,small) in enumerate([(str(streak),'CURRENT STREAK'),(str(active),'ACTIVE DAYS'),(f'{peak} · {busiest[5:] if busiest != "—" else "—"}','BUSIEST DAY')]):
        x=47+i*305
        p += label(x,334,big,27,ACCENT,800) + label(x,359,small,13,MUTED,700)
    write('monthly.svg',960,394,p,1.05)


def build_repos():
    for stale in OUT.glob('repo-*.svg'):
        stale.unlink()
    for i,repo in enumerate(CONF['featured_repos']):
        p = label(30,48,'FEATURED PROJECT  /  '+f'{i+1:02}',13,ACCENT,800)
        p += label(30,99,repo['name'],31,FG,800)
        p += label(30,137,repo.get('description',''),17,MUTED)
        p += f'<rect x="30" y="158" width="900" height="1" fill="{MUTED}" opacity=".2"/>'
        p += label(30,189, repo.get('stack',''),15,SECOND,600)
        p += label(901,189,'↗',25,ACCENT,700,'text-anchor="end"')
        write(f'repo-{i+1}.svg',960,216,p,1.55+i*.18)


def build_graph():
    today = dt.date.today()
    end = today - dt.timedelta(days=(today.weekday()+1)%7) + dt.timedelta(days=6)
    start = end-dt.timedelta(weeks=52,days=6)
    p=label(32,47,'THE CONTRIBUTION GRID',21,FG,800)
    p+=label(928,46,'LAST 53 WEEKS',13,MUTED,700,'text-anchor="end"')
    peak = max(DAYS.values(),default=0)
    for week in range(53):
        for wd in range(7):
            day=start+dt.timedelta(days=week*7+wd)
            count=DAYS.get(day.isoformat(),0) if day <= today else 0
            level = (min(4, 1+int((count-1)*4/max(1,peak))) if count else 0)
            opacity = [0.10,.30,.50,.73,1.0][level]
            x,y=35+week*17, 79+wd*17
            p += f'<rect x="{x}" y="{y}" width="13" height="13" rx="3" fill="{ACCENT}" fill-opacity="{opacity}"/>'
    p+=label(35,226,'Less',13,MUTED)
    for n,opacity in enumerate([.10,.30,.50,.73,1]):
        p+=f'<rect x="{75+n*18}" y="215" width="13" height="13" rx="2" fill="{ACCENT}" fill-opacity="{opacity}"/>'
    p+=label(176,226,'More',13,MUTED)
    write('graph.svg',960,255,p,2.2)


def update_readme():
    path = ROOT / 'README.md'
    readme = path.read_text(encoding='utf-8')
    start, end = '<!-- FEATURED REPOS START -->', '<!-- FEATURED REPOS END -->'
    blocks = []
    for i, repo in enumerate(CONF['featured_repos']):
        url = html.escape(repo.get('url', f'https://github.com/{USER}/{repo["name"]}'), quote=True)
        blocks.append(f'<a href="{url}"><img src="cards/repo-{i+1}.svg" width="100%" alt="Featured project {html.escape(repo["name"], quote=True)}" /></a>')
    if start not in readme or end not in readme:
        raise ValueError('README.md must contain FEATURED REPOS markers')
    readme = readme.split(start)[0] + start + '\n' + '\n\n'.join(blocks) + '\n' + end + readme.split(end,1)[1]
    path.write_text(readme,encoding='utf-8')


if __name__ == '__main__':
    build_hero(); build_tiles(); build_monthly(); build_repos(); build_graph(); update_readme()
    print('Generated', len(list(OUT.glob('*.svg'))), 'SVG cards', '(STATIC)' if STATIC else '(animated)')
