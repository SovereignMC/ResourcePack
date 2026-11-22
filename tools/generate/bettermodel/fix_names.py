#!/usr/bin/env python3
"""Rename generated BetterModel files whose paths are not valid resource locations.

With pack.use-obfuscation false, BetterModel names the per-pixel player limb models
(assets/<ns>/models/player_limb/<base64 hash>.json) with mixed case, which vanilla rejects
(allowed: a-z 0-9 _ . - /). This renames every such file to <sha1(stem)[:16]><ext>, rewrites
every JSON string that references the old id, and fails on any collision.

    python3 tools/generate/bettermodel/fix_names.py [namespace] [--pack-dir .]
"""
import argparse, hashlib, json, os, re, sys

VALID = re.compile(r'^[a-z0-9_.\-/]+$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('namespace', nargs='?', default=os.environ.get('BETTERMODEL_NAMESPACE', 'bettermodel'))
    ap.add_argument('--pack-dir', default='.')
    args = ap.parse_args()
    ns = args.namespace
    base = os.path.join(args.pack_dir, 'assets', ns)
    if not os.path.isdir(base):
        sys.exit(f'missing {base}')

    renames = {}   # old abs path -> new abs path
    refmap = {}    # old "ns:path" ref -> new ref
    taken = set()
    allfiles = []
    for d, _, fs in os.walk(base):
        for f in fs:
            p = os.path.join(d, f)
            allfiles.append(p)
            taken.add(p)
    for p in sorted(allfiles):
        rel = os.path.relpath(p, base).replace(os.sep, '/')
        if VALID.match(rel):
            continue
        d, f = os.path.split(p)
        stem, ext = os.path.splitext(f)
        new = os.path.join(d, hashlib.sha1(rel.encode()).hexdigest()[:16] + ext.lower())
        if new in taken or new in renames.values():
            sys.exit(f'name collision renaming {p} -> {new}')
        renames[p] = new
        parts = rel.split('/')
        if parts[0] in ('models', 'textures'):
            old_ref = f'{ns}:' + '/'.join(parts[1:]).rsplit('.', 1)[0]
            new_ref = f'{ns}:' + os.path.relpath(new, os.path.join(base, parts[0])).replace(os.sep, '/').rsplit('.', 1)[0]
            refmap[old_ref] = new_ref
        # items/<x> files are addressed by path only; nothing references them.

    if not renames:
        print('[bettermodel] fix_names: no invalid names')
        return
    for old, new in renames.items():
        os.rename(old, new)

    pat = re.compile(r'"((?:[^"\\]|\\.)*)"')
    rewritten = 0
    for d, _, fs in os.walk(base):
        for f in fs:
            if not f.endswith(('.json', '.mcmeta')):
                continue
            p = os.path.join(d, f)
            with open(p, encoding='utf-8') as fh:
                s = fh.read()
            s2 = pat.sub(lambda m: '"%s"' % refmap.get(m.group(1), m.group(1)), s)
            if s2 != s:
                with open(p, 'w', encoding='utf-8') as fh:
                    fh.write(s2)
                rewritten += 1
    print(f'[bettermodel] fix_names: renamed {len(renames)} file(s), rewrote references in {rewritten} JSON file(s)')


main()
