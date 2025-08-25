# scan_tree.py
# 사용법 예:
#   python scan_tree.py . --out tree.txt --csv files.csv --max-depth 6 --ext .py,.html,.css,.js,.json
#   python scan_tree.py "C:\path\to\project"

import os
import sys
import argparse
import csv
from datetime import datetime

DEFAULT_EXCLUDES = {
    '.git', '.hg', '.svn', '.idea', '.vscode', '.DS_Store',
    '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache',
    'node_modules', '.venv', 'venv', 'env',
    'dist', 'build', '.next', '.parcel-cache', '.cache'
}

def human_size(n: int) -> str:
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    s = float(n)
    for u in units:
        if s < 1024.0:
            return f"{s:.1f}{u}"
        s /= 1024.0
    return f"{s:.1f}PB"

def should_skip_dir(dirname: str, extra_excludes: set) -> bool:
    name = os.path.basename(dirname.rstrip(os.sep))
    return name in DEFAULT_EXCLUDES or name in extra_excludes

def parse_exts(ext_str: str):
    if not ext_str:
        return None
    exts = []
    for e in ext_str.split(','):
        e = e.strip()
        if not e:
            continue
        if not e.startswith('.'):
            e = '.' + e
        exts.append(e.lower())
    return set(exts)

def scan(root: str, max_depth: int, include_exts: set, extra_excludes: set):
    root = os.path.abspath(root)
    tree_lines = []
    rows = []  # for CSV
    total_files = 0
    total_dirs = 0

    # prefix stack for pretty tree
    prefix_stack = []

    def walk(dir_path: str, depth: int):
        nonlocal total_files, total_dirs
        try:
            items = sorted(os.listdir(dir_path))
        except PermissionError:
            tree_lines.append(''.join(prefix_stack) + '[DENIED] ' + os.path.basename(dir_path))
            return

        # 분리
        dirs = [d for d in items if os.path.isdir(os.path.join(dir_path, d))]
        files = [f for f in items if os.path.isfile(os.path.join(dir_path, f))]

        for i, d in enumerate(dirs):
            full = os.path.join(dir_path, d)
            is_last = (i == len(dirs) - 1) and (len(files) == 0)
            if should_skip_dir(full, extra_excludes):
                continue
            connector = '└─ ' if is_last else '├─ '
            tree_lines.append(''.join(prefix_stack) + connector + d + '/')
            total_dirs += 1
            if depth < max_depth:
                prefix_stack.append('   ' if is_last else '│  ')
                walk(full, depth + 1)
                prefix_stack.pop()

        for j, f in enumerate(files):
            full = os.path.join(dir_path, f)
            if include_exts and os.path.splitext(f)[1].lower() not in include_exts:
                continue
            is_last_file = (j == len(files) - 1)
            connector = '└─ ' if is_last_file else '├─ '

            try:
                st = os.stat(full)
                size = st.st_size
                mtime = datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            except OSError:
                size = 0
                mtime = ''
            tree_lines.append(''.join(prefix_stack) + connector + f + f"  ({human_size(size)})")
            rows.append([full, os.path.relpath(full, root), os.path.splitext(f)[1].lower(), size, mtime])
            total_files += 1

    # 루트 출력
    tree_lines.append(os.path.basename(root) + '/')
    walk(root, depth=0)

    summary = f"\n[Summary] dirs={total_dirs}, files={total_files}, root={root}"
    return tree_lines, rows, summary

def main():
    p = argparse.ArgumentParser(description="Project tree scanner")
    p.add_argument('root', help='scan base directory (e.g., . or C:\\path\\project)')
    p.add_argument('--out', help='write tree text to this file (e.g., tree.txt)')
    p.add_argument('--csv', help='write file list to this CSV (columns: abs_path, rel_path, ext, size, mtime)')
    p.add_argument('--max-depth', type=int, default=8, help='max directory depth to traverse (default: 8)')
    p.add_argument('--ext', help='comma separated extensions to include (e.g., .py,.html,.css,.js)')
    p.add_argument('--exclude', help='comma separated dir names to additionally exclude')
    args = p.parse_args()

    include_exts = parse_exts(args.ext)
    extra_excludes = set([x.strip() for x in args.exclude.split(',')]) if args.exclude else set()

    lines, rows, summary = scan(args.root, args.max_depth, include_exts, extra_excludes)

    # 콘솔 출력
    print('\n'.join(lines))
    print(summary)

    # 파일로 저장
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            f.write('\n')
            f.write(summary)
        print(f"[Saved] tree → {args.out}")

    if args.csv:
        with open(args.csv, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            w.writerow(['abs_path', 'rel_path', 'ext', 'size', 'mtime'])
            w.writerows(rows)
        print(f"[Saved] file list → {args.csv}")

if __name__ == '__main__':
    sys.exit(main())
