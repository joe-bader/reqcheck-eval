"""Regenerate the README result chart from its exact-value table (stdlib only).

Run from any directory: python3 docs/charts/generate_results.py
"""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / 'README.md'
OUTPUT = Path(__file__).with_name('model-results.svg')
BG, INK, MUTED, GRID = '#0B1120', '#EDF3FC', '#AABBD0', '#28374C'
DEV, TEST, SPEED = '#86B6FF', '#74D7CE', '#8E9FB5'


def render():
    section = README.read_text().split('## Does it work?', 1)[1].split('## How it works', 1)[0]
    rows = []
    for line in section.splitlines():
        if not line.startswith('|'):
            continue
        cells = [c.strip().replace('*', '') for c in line.strip('|').split('|')]
        if len(cells) != 4 or not re.fullmatch(r'0\.\d+', cells[1]):
            continue
        rows.append(dict(model=cells[0], dev=float(cells[1]), test=float(cells[2]),
                         seconds=float(cells[3]) if cells[3] else None,
                         seconds_label=cells[3]))
    assert len(rows) == 6, 'Expected five models and the flag-everything baseline'
    models = sorted((r for r in rows if r['seconds'] is not None), key=lambda r: -r['test'])
    baseline = [r for r in rows if r['seconds'] is None]
    assert len(models) == 5 and len(baseline) == 1
    rows = models + baseline
    assert all(0 <= r['dev'] <= 1 and 0 <= r['test'] <= 1 for r in rows)
    assert all(0 <= r['seconds'] <= 6 for r in models), 'Expand the time axis for new results'
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="830" viewBox="0 0 1160 830" role="img" aria-labelledby="title desc">',
             '<title id="title">Local model results: dev and sealed-test F1, with runtime</title>']
    desc = '; '.join(f"{r['model']}: dev F1 {r['dev']:.2f}, test F1 {r['test']:.2f}, " +
                     (f"{r['seconds_label']} seconds per requirement" if r['seconds'] is not None else 'runtime not reported') for r in rows)
    parts += [f'<desc id="desc">{escape(desc)}. Thirty synthetic requirements per set; small score differences are inconclusive. Kev-9B returns probabilities only.</desc>',
              '<metadata>Source: README.md, Does it work? exact-value table; supporting experiment records: results/LOG.md. Regenerate with docs/charts/generate_results.py. F1 is a score on a 0–1 scale, not a percent accuracy. Time values are the README dev-run summary; no confidence intervals are supplied.</metadata>',
              '<style>text {font-family: Lato, "DejaVu Sans", sans-serif;}</style>']

    def rect(x, y, w, h, fill, stroke=None):
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"' +
                     (f' stroke="{stroke}" stroke-width="1.5"' if stroke else '') + '/>')

    def text(x, y, value, size=18, color=INK, weight=400, anchor='start'):
        parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')

    def line(x1, y1, x2, y2, color=GRID, dash=False):
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1"' +
                     (' stroke-dasharray="4 6"' if dash else '') + '/>')

    rect(0, 0, 1160, 830, BG)
    text(42, 40, 'REQCHECK / EVALUATION', 12, DEV, 700)
    text(42, 81, 'Local model results', 32, INK, 700)
    text(42, 112, 'Dev and sealed test sets · RTX 3080 / 10 GB', 18, MUTED)
    text(42, 175, 'Model', 20, INK, 700)
    text(42, 201, 'Ordered by test F1', 16, MUTED)
    text(285, 175, 'F1 score', 20, INK, 700)
    text(285, 201, 'Higher is better', 16, MUTED)
    text(850, 175, 'Time per requirement', 20, INK, 700)
    text(850, 201, 'Seconds · lower is better', 16, MUTED)
    rect(285, 219, 24, 12, BG, DEV)
    text(318, 231, 'Dev', 16, MUTED)
    rect(386, 219, 24, 12, TEST)
    text(419, 231, 'Sealed test', 16, MUTED)
    # Both quantitative axes begin at zero; F1 retains its full 0–1 range.
    for i in range(6):
        x = 285 + 430 * i / 5
        line(x, 248, x, 711, GRID if i else MUTED)
        text(x, 739, f'{i / 5:.1f}', 15, MUTED, anchor='middle')
    for i in range(4):
        x = 850 + 230 * i / 3
        line(x, 248, x, 711, GRID if i else MUTED)
        text(x, 739, str(i * 2), 15, MUTED, anchor='middle')
    line(285, 711, 715, 711, MUTED)
    line(850, 711, 1080, 711, MUTED)
    line(42, 629, 1118, 629, GRID, True)
    for i, r in enumerate(rows):
        y = 275 + i * 75 if i < 5 else 675
        label = r['model'].split(' (', 1)[0]
        if i == 5:
            label = 'Flag everything'
        text(42, y + 1, label, 19, INK, 700)
        note = ('System 1 · probabilities only' if label == 'Kev-9B' else
                'Largest model' if label.startswith('qwen3.6') else
                'Baseline' if i == 5 else '')
        if note:
            text(42, y + 25, note, 14, MUTED)
        for metric, offset, color, filled in [('dev', -16, DEV, False), ('test', 7, TEST, True)]:
            width = r[metric] * 430
            rect(285, y + offset, width, 14, color if filled else BG, None if filled else color)
            text(285 + width + 9, y + offset + 13, f'{r[metric]:.2f}', 16, color, 700)
        if r['seconds'] is not None:
            width = r['seconds'] / 6 * 230
            rect(850, y - 3, width, 17, SPEED)
            text(850 + width + 9, y + 12, r['seconds_label'], 16, INK, 700)
        else:
            rect(861, y - 14, 132, 33, BG)
            text(870, y + 8, 'Not reported', 16, MUTED)
    text(42, 784, '30 synthetic requirements per set. Small score differences are inconclusive.', 17, MUTED)
    text(42, 811, 'Source: README result table and results/LOG.md · Dev labels: author; test labels: Claude.', 15, MUTED)
    OUTPUT.write_text('\n'.join(parts + ['</svg>']) + '\n')
    print(f'Wrote {OUTPUT.relative_to(ROOT)} from {len(rows)} README rows.')


if __name__ == '__main__':
    render()
