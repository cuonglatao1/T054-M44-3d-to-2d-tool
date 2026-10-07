"""Tech lead: aggregate pilot results (out/pilot/*.json from every reviewer) into a manual-vs-tool comparison.

  python scripts/pilot_report.py [--dir out/pilot]

Writes out/pilot/pilot_summary.md and pilot_summary.csv.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TYPES = ['OFFSET', 'SCALE', 'ROTATE', 'CLASS_SWAP', 'DELETE']
MODE_TEXT = {'tay': 'Review tay', 'tool': 'Có tool M44'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default=str(ROOT / 'out' / 'pilot'))
    args = ap.parse_args()
    d = Path(args.dir)
    runs = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(d.glob('*_*_*.json'))]
    if not runs:
        raise SystemExit(f'Chưa có kết quả nào trong {d}')

    with open(d / 'pilot_summary.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(['nguoi', 'bo', 'che_do', 'phut', 'loi_sua_duoc', 'tong_loi', 'ti_le', 'loi_moi_phut',
                    'cuboid_lam_hong', 'cuboid_dung_ban_dau'])
        for r in runs:
            w.writerow([r['name'], r['set'], r['mode'], r['minutes'], r['fixed'], r['injected'], r['fixed_rate'],
                        round(r['fixed'] / r['minutes'], 2), r['damaged'], r['correct_at_start']])

    agg = defaultdict(lambda: defaultdict(float))
    by_type = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for r in runs:
        a = agg[r['mode']]
        a['n'] += 1
        for k in ('fixed', 'injected', 'minutes', 'damaged', 'correct_at_start'):
            a[k] += r[k]
        for t in TYPES:
            by_type[r['mode']][t][0] += r['fixed_by_type'].get(t, 0)
            by_type[r['mode']][t][1] += r['total_by_type'].get(t, 0)

    lines = ['# Kết quả pilot M44', '', f'{len(runs)} lượt review, {len({r["name"] for r in runs})} người.', '',
             '| Chế độ | Lượt | Lỗi sửa được | Tỉ lệ | Lỗi / phút | Phút trung bình | Cuboid đúng bị làm hỏng |',
             '|---|---|---|---|---|---|---|']
    for mode in ('tay', 'tool'):
        a = agg.get(mode)
        if not a:
            continue
        lines.append(f"| {MODE_TEXT[mode]} | {a['n']:.0f} | {a['fixed']:.0f}/{a['injected']:.0f} | "
                     f"{a['fixed'] / a['injected']:.0%} | {a['fixed'] / a['minutes']:.2f} | "
                     f"{a['minutes'] / a['n']:.1f} | {a['damaged']:.0f}/{a['correct_at_start']:.0f} "
                     f"({a['damaged'] / a['correct_at_start']:.1%}) |")
    if 'tay' in agg and 'tool' in agg:
        t, m = agg['tool'], agg['tay']
        speed = (t['fixed'] / t['minutes']) / (m['fixed'] / m['minutes']) if m['fixed'] else float('inf')
        lines += ['', f"**Có tool: sửa được {t['fixed'] / t['injected']:.0%} lỗi so với {m['fixed'] / m['injected']:.0%} "
                      f"khi làm tay; số lỗi sửa được mỗi phút gấp {speed:.1f} lần.**"]
    lines += ['', '## Theo loại lỗi', '', '| Loại | Review tay | Có tool |', '|---|---|---|']
    for ty in TYPES:
        cells = []
        for mode in ('tay', 'tool'):
            f, n = by_type[mode][ty]
            cells.append(f'{f}/{n}' + (f' ({f / n:.0%})' if n else ''))
        lines.append(f'| {ty} | {cells[0]} | {cells[1]} |')
    lines += ['', '## Từng lượt', '', '| Người | Bộ | Chế độ | Phút | Sửa được | Làm hỏng |', '|---|---|---|---|---|---|']
    for r in sorted(runs, key=lambda r: (r['name'], r['mode'])):
        lines.append(f"| {r['name']} | {r['set']} | {MODE_TEXT[r['mode']]} | {r['minutes']:g} | "
                     f"{r['fixed']}/{r['injected']} | {r['damaged']} |")
    (d / 'pilot_summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    print(f'\n→ {d / "pilot_summary.md"}, {d / "pilot_summary.csv"}')


if __name__ == '__main__':
    main()
