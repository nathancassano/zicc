"""Select interrupt addressing modes from final assembly and WRAM placement."""
import re


FUNCTION = re.compile(r'^; allocation function \d+ begin\n.*?^; allocation function \d+ end$', re.M | re.S)
MEMORY = set('adc and asl bit cmp cpx cpy dec eor inc lda ldx ldy lsr ora rol ror sbc sta stx sty stz trb tsb'.split())
LONG_TO_ABSOLUTE = set('adc and cmp eor lda ora sbc sta'.split())


def objects(inputs, promoted):
    """Collect defined C objects in pinned/promoted WRAM and direct page."""
    exports = {}
    locals_by_unit = {}
    for source, _, ident, _, asm, _ in inputs:
        if source.suffix != '.c':
            continue
        for match in re.finditer(
                r'^\.segment "(\w+)"[^\n]*\n(?:; allocation object (\w+) \w+\n)?'
                r'(?:\.export(?:zp)? (\w+)\n)?__zicc_object_size_(\w+) = (\d+)$', asm, re.M):
            segment, candidate, exported, symbol, size = match.groups()
            symbol = '_' + symbol
            if candidate:
                storage = f'NEAR_{segment}_{ident}_{candidate}'
                if storage not in promoted:
                    continue
            elif segment not in {'ZEROPAGE', 'LORAM_BSS', 'LORAM_DATA'}:
                continue
            record = (segment == 'ZEROPAGE', int(size))
            locals_by_unit.setdefault(ident, {})[symbol] = record
            if exported:
                exports[symbol] = record
    return exports, locals_by_unit


def select(text, known, library_nmi, low_has_slack):
    def rewrite(match):
        body = match[0]
        if not re.search(r'^\.export __vector_\w+ := ', body, re.M):
            return body
        lines = body.splitlines()
        bank_ok = dp_ok = True
        a_width = i_width = 2
        mmio = {}
        dp_to_absolute = {}
        dma = set()
        wide_reads = set()
        for index, line in enumerate(lines):
            directive = line.strip()
            if directive in {'.a8', '.a16'}:
                a_width = 1 if directive == '.a8' else 2
            if directive in {'.i8', '.i16'}:
                i_width = 1 if directive == '.i8' else 2
            instruction = re.fullmatch(r'    ([a-z]{3})(?: +([^;]+?))?\s*(?:;.*)?', line)
            if not instruction:
                continue
            op, operand = instruction.groups()
            operand = operand or ''
            if op in {'jsr', 'jsl', 'mvn', 'mvp', 'tcd', 'pei'}:
                bank_ok = dp_ok = False
            if op not in MEMORY or operand in {'', 'a'} or operand.startswith('#'):
                continue
            width = i_width if op in {'ldx', 'ldy', 'stx', 'sty', 'cpx', 'cpy'} else a_width
            if re.fullmatch(r'\d+,s', operand):
                continue
            absolute = re.fullmatch(r'a:\.loword\((_\w+)(?:\+\$([0-9a-fA-F]+))?\)', operand)
            direct = re.fullmatch(r'z:(_\w+)(?:\+\$([0-9a-fA-F]+))?', operand)
            long_address = re.fullmatch(r'f:\$([0-9a-fA-F]{6})', operand)
            if absolute or direct:
                symbol, offset = (absolute or direct).groups()
                record = known.get(symbol)
                end = int(offset or '0', 16) + width
                # Byte reads may load a word and consume only its low byte
                # Their extra bus access must also stay inside the mirror
                wide_read = (absolute and record and not record[0] and op == 'lda'
                             and width == 2 and end == record[1] + 1 and low_has_slack)
                if wide_read:
                    wide_reads.add((symbol, end))
                if record and (end <= record[1] or wide_read):
                    if direct and record[0]:
                        dp_to_absolute[index] = f'    {op} a:.loword({operand[2:]})'
                    elif absolute:
                        continue
                    else:
                        dp_ok = False
                elif direct:
                    dp_ok = False
                else:
                    bank_ok = False
            elif long_address:
                address = int(long_address[1], 16)
                if op not in LONG_TO_ABSOLUTE or address >> 16 not in {0x00, 0x80}:
                    continue
                address &= 0xffff
                # Shortening the operand changes the last byte fetched before
                # a read. Only narrow reads independent of CPU open bus
                windows = (((0x2100, 0x2200), (0x4200, 0x4220), (0x4300, 0x4380)) if op == 'sta'
                           else ((0x2134, 0x2137), (0x2138, 0x2140), (0x4213, 0x4220)))
                if any(lo <= address and address + width <= hi for lo, hi in windows):
                    mmio[index] = f'    {op} a:${address:04X}'
                    if 0x4300 <= address < 0x4380:
                        dma.add(index)
            elif operand.startswith('f:'):
                continue
            else:
                # Unresolved indexed/indirect addressing can depend on both
                # registers. Numeric scratch operands depend only on D
                dp_ok = False
                if not operand.startswith('z:'):
                    bank_ok = False
        bank = bank_ok and bool(mmio)
        reset_dp = library_nmi and '.segment "NMI_END"' in lines
        direct_page = dp_ok and len(dma) * (1 if bank else 2) > len(dp_to_absolute) + 4 * reset_dp
        if not (bank or direct_page):
            return body
        if bank:
            lines[lines.index('    lda #$7E')] = '    lda #$80'
            for index, line in mmio.items():
                lines[index] = line
            lines[-1:-1] = [f'.assert {symbol} + {end} <= $7E2000, lderror, "interrupt read exceeds low WRAM"'
                            for symbol, end in sorted(wide_reads)]
        if direct_page:
            lines[lines.index('    pea $0000')] = '    pea $4300'
            for index, line in dp_to_absolute.items():
                lines[index] = line
            for index in dma:
                op, address = mmio[index].split(' a:$')
                lines[index] = f'{op} z:${int(address, 16) - 0x4300:02X}'
            if reset_dp:
                lines[lines.index('.segment "NMI_END"'):lines.index('.segment "NMI_END"')] = ['    pea $0000', '    pld']
        return '\n'.join(lines)
    return FUNCTION.sub(rewrite, text)
