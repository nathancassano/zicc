"""Track whether the accumulator holds 8 or 16 bits after the compiler chooses addresses."""
import re

from interrupt_addressing import FUNCTION


def bridge(body):
    interrupt = '\n.export __vector_' in body
    if interrupt and '    rep #$30\n    pha\n    phx\n' not in body:
        return body
    lines = body.splitlines()
    code = [(i, line.strip()) for i, line in enumerate(lines)
            if line.strip() and not line.lstrip().startswith(';')]
    ops = [line for _, line in code]
    if any(re.match(r'(?:ldx|stx|tax|txa|txy|tyx|tsx|txs|inx|dex|cpx|mvn|mvp|jsr|jsl|jml|plp|xce)\b', op)
           or re.search(r',\s*x\b', op)
           or re.match(r'(?:sep|rep) #(?!\$20$|\$30$)', op)
           or op == 'sep #$30' or op in ('.i8', '.byte', '.word')
           or (not interrupt and op in ('phx', 'plx')) for op in ops):
        return body
    labels = {op.split()[0]: i for i, op in enumerate(ops) if ' = *' in op}
    local_labels = [i for i, op in enumerate(ops) if op == ':']

    def high_dead(start, different_n=False):
        pending = [(start, True, different_n)]
        seen = set()
        while pending:
            i, a8, different_n = pending.pop()
            while i < len(ops) and (i, a8, different_n) not in seen:
                seen.add((i, a8, different_n))
                op = ops[i]
                if op in ('rep #$20', 'sep #$20'):
                    a8 = op.startswith('sep')
                elif op == 'rti' or (not a8 and (op.startswith('lda ') or op == 'pla')):
                    break
                elif op.startswith('jmp .loword('):
                    target = labels.get(op[12:-1])
                    if target is None:
                        return False
                    i = target
                    continue
                elif match := re.fullmatch(r'b(?:cc|cs|eq|ne|mi|pl|vc|vs) (\w+|:\+)', op):
                    if different_n and op.startswith(('bmi ', 'bpl ')):
                        return False
                    target = (next((j for j in local_labels if j > i), None)
                              if match[1] == ':+' else labels.get(match[1]))
                    if target is None:
                        return False
                    pending.append((target, a8, different_n))
                elif a8 and op.startswith('lda '):
                    different_n = False
                elif (op.startswith(('stz ', '.segment ')) or ' = *' in op or
                      op in (':', '.a8', '.a16', 'plb', 'pld', 'ply', 'plx') or
                      (a8 and op.startswith('sta '))):
                    pass
                else:
                    return False
                i += 1
            else:
                if i >= len(ops):
                    return False
        return True

    def word_copy(i):
        return (i + 1 < len(ops) and
                re.fullmatch(r'lda (?:#|[az]:)[^,]+', ops[i]) and
                re.fullmatch(r'sta [az]:[^,]+', ops[i + 1]))

    def masked_wram_byte(i):
        # This prologue is selected only after the allocator proves the
        # absolute symbol operands are in the low WRAM mirror
        return ('    phb\n    sep #$20\n.a8\n    lda #$80\n' in body and
                ops[i+1:i+4] == ['and #$00FF', 'sep #$20', '.a8'] and
                re.fullmatch(r'lda a:\.loword\(_\w+(?:\+\$[\dA-F]{4})?\)', ops[i]) and
                i+4 < len(ops) and ops[i+4].startswith('sta '))

    bridged_loads = set()
    for i, op in enumerate(ops):
        if op != 'rep #$20' or i == 0 or not ops[i-1].startswith(('sta ', 'stz ')) or ops[i+1:i+2] != ['.a16']:
            continue
        j = i + 2
        while word_copy(j):
            j += 2
        if j == i + 2:
            continue
        # A trailing immediate can move into A8 with equivalent N/Z
        imm = re.fullmatch(r'lda #\$00([0-7][0-9A-F])', ops[j]) if j < len(ops) else None
        masked = masked_wram_byte(j)
        sep = j + (2 if masked else bool(imm))
        if ops[sep:sep+2] != ['sep #$20', '.a8'] or sep+2 >= len(ops):
            continue
        if not imm and not masked and not ops[sep+2].startswith('lda '):
            continue
        if not high_dead(sep+2, different_n=bool(masked)):
            continue
        for k in range(i+2, j, 2):
            lines[code[k][0]] = '    ldx' + ops[k][3:]
            lines[code[k+1][0]] = '    stx' + ops[k+1][3:]
        if imm:
            lines[code[j][0]] = '    lda #$' + imm[1]
        if masked:
            lines[code[j+1][0]] = ''
            bridged_loads.add(j)
        for k in (i, i+1, sep, sep+1):
            lines[code[k][0]] = ''
    for i in range(len(ops)):
        if i in bridged_loads or not masked_wram_byte(i) or not high_dead(i+4, different_n=True):
            continue
        lines[code[i][0]] = '    sep #$20\n.a8\n    ' + ops[i]
        for k in (i+1, i+2, i+3):
            lines[code[k][0]] = ''
    return '\n'.join(lines)


def across_edges(body):
    lines = body.splitlines()
    indexed = [(i, line.strip()) for i, line in enumerate(lines)
               if line.strip() and not line.lstrip().startswith(';')]
    ops = [op for _, op in indexed]
    labels = {re.split(r'[: ]', op, 1)[0]: i for i, op in enumerate(ops)
              if op.endswith(' = *') or (op.endswith(':') and op != ':')}
    local = [i for i, op in enumerate(ops) if op == ':']
    branches = {}
    jumps = {}
    for i, op in enumerate(ops):
        if match := re.fullmatch(r'b(?:cc|cs|eq|ne|mi|pl|vc|vs) (\w+|:\+|:-)', op):
            operand = match[1]
            if operand == ':+':
                target = next((j for j in local if j > i), None)
            elif operand == ':-':
                target = next((j for j in reversed(local) if j < i), None)
            else:
                target = labels.get(operand)
            if target is None:
                return body
            branches[i] = target
        elif match := re.fullmatch(r'jmp \.loword\((\w+)\)', op):
            if match[1] not in labels:
                return body
            jumps[i] = labels[match[1]]
        elif match := re.fullmatch(r'br[al] (\w+)', op):
            if match[1] not in labels:
                return body
            jumps[i] = labels[match[1]]
        elif re.match(r'(?:b(?:cc|cs|eq|ne|mi|pl|vc|vs|ra|rl)|jmp|jml|plp|xce)\b', op):
            return body

    def reaches_a8(i):
        seen = set()
        while i < len(ops) and i not in seen:
            seen.add(i)
            op = ops[i]
            if i in jumps:
                i = jumps[i]
                continue
            if not (op.startswith('.') or op == ':' or op.endswith(' = *')):
                return op == 'sep #$20'
            i += 1
        return False

    removed = set()
    restore = set()
    for i, op in enumerate(ops):
        if op != 'rep #$20' or ops[i+1:i+2] != ['.a16']:
            continue
        edge = i + 2
        if edge in jumps and reaches_a8(jumps[edge]):
            removed.add(i)
        elif edge in branches:
            taken = reaches_a8(branches[edge])
            fallthrough = reaches_a8(edge+1)
            # A named taken edge that needs a restore may have other users
            local_taken = ops[edge].endswith(' :+')
            if (taken or fallthrough) and (taken or local_taken):
                removed.add(i)
                if not fallthrough:
                    if ops[edge+1] == ':' or ops[edge+1].endswith((':', ' = *')):
                        removed.remove(i)
                        continue
                    restore.add(edge+1)
                if not taken:
                    target = branches[edge]
                    if list(branches.values()).count(target) != 1:
                        return body
                    restore.add(target+1)

    # Follow both branch edges and apply the proposed restores before removing
    # a SEP. Any reachable A16 predecessor keeps the shared entry switch
    incoming = {}
    pending = [(0, False)]
    while pending:
        i, a8 = pending.pop()
        if i >= len(ops):
            return body
        modes = incoming.setdefault(i, set())
        if a8 in modes:
            continue
        modes.add(a8)
        if i in restore:
            a8 = False
        op = ops[i]
        if op in ('rep #$20', 'rep #$30') and i not in removed:
            a8 = False
        elif op == 'sep #$20':
            a8 = True
        if op in ('rti', 'rts', 'rtl'):
            continue
        if i in branches:
            pending.append((branches[i], a8))
        pending.append((jumps.get(i, i+1), a8))

    # Verify runtime width still agrees with the original assembly at each
    # ordinary instruction. Only control transfers may carry either width
    lexical_a8 = False
    for i, op in enumerate(ops):
        if op in ('.a8', '.a16'):
            lexical_a8 = op == '.a8'
        elif (i not in branches and i not in jumps and
              op not in (':', 'rep #$20', 'rep #$30', 'sep #$20', 'rti') and
              not op.startswith('.') and not op.endswith((':', ' = *'))):
            modes = {False} if i in restore else incoming.get(i, {lexical_a8})
            if modes != {lexical_a8}:
                return body
    for i, op in enumerate(ops):
        line = indexed[i][0]
        if i in removed or (op == 'sep #$20' and incoming.get(i) == {True} and i not in restore):
            lines[line] = ''
        if i in restore:
            lines[line] = '    rep #$20\n' + lines[line]
    return '\n'.join(lines)


def select(text):
    return FUNCTION.sub(lambda match: across_edges(bridge(match[0])), text)
