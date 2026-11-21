"""Derive the direct-page scratch words each exported integer helper may write.

Follows fall-through, branches, jmp and jsr inside runtime/integers/*.s from each
exported entry. Bit n of a mask is the word at scratch offset 2n. Prints the C table that
src/codegen/dp_homes.inc embeds (helper_clobbers); --check compares it with the source."""
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCES = sorted((ROOT/'runtime/integers').glob('*.s'))
WRITES = {'sta', 'stx', 'sty', 'stz', 'inc', 'dec', 'asl', 'lsr', 'rol', 'ror', 'tsb', 'trb'}
BRANCHES = {'bcc', 'bcs', 'beq', 'bne', 'bmi', 'bpl', 'bvc', 'bvs', 'bra', 'brl', 'jmp', 'jsr'}

def parse():
    aliases, exports, lines, labels, local_labels, anonymous = {}, [], [], {}, {}, {}
    for file_idx, path in enumerate(SOURCES):
        text = path.read_text()
        for m in re.finditer(r'^(\w+)=(__arith_lhs|__arith_rhs)(?:\+(\d+))?$', text, re.M):
            aliases[m[1]] = (m[2], int(m[3] or 0))
        exports.extend(n.strip() for line in re.findall(r'^\.export (.+)$', text, re.M) for n in line.split(','))
        repeats, scope, file_anon = [], '', []
        anonymous[file_idx] = file_anon
        for raw in text.splitlines():
            line = raw.split(';')[0].rstrip()
            m = re.match(r'^(@?\w+)?:', line)
            if m:
                if not m[1]: file_anon.append(len(lines))
                elif m[1].startswith('@'): local_labels[file_idx, scope + m[1]] = len(lines)
                else: scope = m[1]; labels[m[1]] = len(lines)
                line = line[m.end():]
            r = re.match(r'\s*\.repeat\s+(\d+)\s*,\s*(\w+)', line)
            if r: repeats.append((r[2], int(r[1]))); continue
            if re.match(r'\s*\.endrep', line): repeats.pop(); continue
            if line.strip() and not line.strip().startswith('.'):
                lines.append((line.strip(), tuple(repeats), scope, file_idx))
    return aliases, exports, lines, labels, local_labels, anonymous

def words_of(operand, aliases, repeats):
    """Every workspace word the operand can name over all enclosing .repeat values."""
    m = re.match(r'z:(\w+)((?:\+\w+)*)$', operand)
    if not m: return None
    base = m[1]
    if base in aliases: name, offset = aliases[base]
    elif base in ('__arith_lhs', '__arith_rhs'): name, offset = base, 0
    else: return None
    offset += 4 if name == '__arith_rhs' else 0
    combos = [{}]
    for var, count in repeats: combos = [dict(c, **{var: k}) for c in combos for k in range(count)]
    terms = [t for t in m[2].split('+') if t]
    return {(offset + sum(int(t) if t.isdigit() else c[t] for t in terms)) // 2 for c in combos}

def masks():
    aliases, exports, lines, labels, local_labels, anonymous = parse()
    def reach(entry):
        seen, work, mask = set(), [labels[entry]], 0
        while work:
            i = work.pop()
            while i < len(lines) and i not in seen:
                seen.add(i); text, repeats, scope, file_idx = lines[i]
                parts = text.split(None, 1); op = parts[0].lower(); arg = parts[1] if len(parts) > 1 else ''
                if op in WRITES and arg:
                    if arg == 'z:L,x' and scope == 'udiv32_word':
                        # This loop visits X=2 and X=0 only
                        ws = {0, 1}
                    else:
                        ws = words_of(arg, aliases, repeats)
                    if ws is not None: mask |= sum(1 << w for w in ws)
                    elif arg.startswith('z:') or arg.startswith('['): raise SystemExit(f'unknown direct-page write: {text}')
                if op in BRANCHES:
                    target = re.sub(r'^\.loword\((@?\w+)\)$', r'\1', arg)
                    if re.fullmatch(r':\++', target): goal = [a for a in anonymous[file_idx] if a > i][len(target) - 2]
                    elif re.fullmatch(r':-+', target): goal = [a for a in anonymous[file_idx] if a <= i][-(len(target) - 1)]
                    else:
                        if target.startswith('@'):
                            key = (file_idx, scope + target)
                            if key not in local_labels: raise SystemExit(f'unresolved target: {text}')
                            goal = local_labels[key]
                        else:
                            if target not in labels: raise SystemExit(f'unresolved target: {text}')
                            goal = labels[target]
                    work.append(goal)
                    if op in ('bra', 'brl', 'jmp'): break
                if op in ('rts', 'rtl'): break
                i += 1
        return mask
    return {name: reach(name) for name in exports if name.startswith('__')}

def table():
    return ''.join(f'        {{"{n}",0x{m:04X}}},\n' for n, m in sorted(masks().items()))

if __name__ == '__main__':
    if '--check' in sys.argv:
        src = (ROOT/'src/codegen/dp_homes.inc').read_text()
        m = re.search(r'/\* helper-clobbers begin \*/\n(.*?)\s*/\* helper-clobbers end \*/', src, re.S)
        ok = m and m[1].strip() == table().strip()
        print('helper clobber table', 'matches' if ok else 'DIFFERS from', 'runtime/integers/*.s')
        sys.exit(0 if ok else 1)
    print(table(), end='')
