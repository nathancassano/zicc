"""Headless MesenCE profiling adapter, adapted from Dragon's tools/mesen_core.py.

Uses the installed audited Windows x64 DLL; one Core instance per process.
MESEN_CORE_DLL can override its location. No game-specific boot code is used.

A load/start/wait_for run is served from tools/run_cache.py when the DLL,
SNES configuration, ROM bytes, script text and wait tag match an earlier
completed run; the ROM is then never loaded. Profiler access or resuming after
a cached result needs a live run: pass cache=False for such callers (calls made
before the run starts switch it to a live, uncached run automatically).
"""

import ctypes as C
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_cache  # noqa: E402
from check_diagnostics import save_log, verbose



DEFAULT_DLL = Path(os.environ.get('MESEN_CORE_DLL', 'D:/dev/dragon/tools/mesen/MesenCore.dll'))
AUDITED_BUILDS = (b'Jul  7 2026, 11:26:41', b'Sep 21 2026, 02:49:10')
CPU_SNES = 0
CONSOLE_MODE = 0x10


class KeyMapping(C.Structure):
    _fields_ = [('buttons', C.c_uint16 * 23), ('CustomKeys', C.c_uint16 * 100)]


class KeyMappingSet(C.Structure):
    _fields_ = [('mappings', KeyMapping * 4), ('TurboSpeed', C.c_uint32)]


class ControllerConfig(C.Structure):
    _fields_ = [('Keys', KeyMappingSet), ('Type', C.c_int32)]


class SnesConfig(C.Structure):
    _fields_ = [
        ('Port1', ControllerConfig), ('Port2', ControllerConfig),
        ('Port1SubPorts', ControllerConfig * 4), ('Port2SubPorts', ControllerConfig * 4),
        ('Region', C.c_int32), ('AllowInvalidInput', C.c_bool),
        ('ColorCorrection', C.c_int32), ('HighResBlendMode', C.c_int32),
        ('DeinterlaceMode', C.c_int32),
        *[(name, C.c_bool) for name in ('HideBgLayer1', 'HideBgLayer2', 'HideBgLayer3',
          'HideBgLayer4', 'HideSprites', 'DisableFrameSkipping', 'ForceFixedResolution', 'RemoveSpriteLimit')],
        ('Overscan', C.c_uint32 * 4), ('InterpolationType', C.c_int32),
        ('ChannelVolumes', C.c_uint32 * 8), ('EnableRandomPowerOnState', C.c_bool),
        ('EnableStrictBoardMappings', C.c_bool), ('RamPowerOnState', C.c_int32),
        ('SpcClockSpeedAdjustment', C.c_int32), ('PpuExtraScanlinesBeforeNmi', C.c_uint32),
        ('PpuExtraScanlinesAfterNmi', C.c_uint32), ('GsuClockSpeed', C.c_uint32),
        ('BsxCustomDate', C.c_int64),
    ]


class EmuConfig(C.Structure):
    _fields_ = [(name, C.c_uint32) for name in ('speed', 'turbo', 'rewind', 'ahead')]


class AddressInfo(C.Structure):
    _fields_ = [('Address', C.c_int32), ('Type', C.c_int32)]


class ProfiledFunction(C.Structure):
    _fields_ = [
        ('ExclusiveCycles', C.c_uint64), ('InclusiveCycles', C.c_uint64),
        ('CallCount', C.c_uint64), ('MinCycles', C.c_uint64), ('MaxCycles', C.c_uint64),
        ('Address', AddressInfo), ('Flags', C.c_int32),
    ]


class Core:
    def __init__(self, home, dll=DEFAULT_DLL, *, level=0, symbols=None, boot=False, cache=True):
        self.cache = cache and run_cache.enabled()
        self.dll_sha256 = run_cache.file_sha256(dll)
        self._pending = None  # (rom, script_path, script) of a deferred load
        self._cached_log = None
        self._started = False
        self.boot_level = level
        self.boot_symbols = symbols
        self.boot_enabled = boot
        self.boot_report = {'mode': 'legacy', 'level': 0}
        self.dll = C.CDLL(str(Path(dll).resolve()))
        self._bind('InitDll', None)()
        version = self._bind('GetMesenVersion', C.c_uint32)()
        date = self._bind('GetMesenBuildDate', C.c_char_p)()
        if version != 0x020201 or date not in AUDITED_BUILDS or C.sizeof(C.c_void_p) != 8:
            raise RuntimeError(f'Unaudited MesenCE build: {version:#x}, {date!r}')
        self.version = f'{version:#x} {date.decode()}'
        home = Path(home)
        home.mkdir(parents=True, exist_ok=True)
        self._bind('InitializeEmu', None, C.c_char_p, C.c_void_p, C.c_void_p,
                  C.c_bool, C.c_bool, C.c_bool, C.c_bool)(str(home).encode(), None, None, True, True, True, True)
        # Unthrottled; emulated timing is unaffected
        self._bind('SetEmulationConfig', None, EmuConfig)(EmuConfig(0, 300, 100, 0))
        self._configure_snes()
        self.script_id = None
        self._log_buffer = C.create_string_buffer(1 << 22)

    def _bind(self, name, result, *types):
        fn = getattr(self.dll, name)
        fn.restype, fn.argtypes = result, types
        return fn

    def bind(self, name, result, *types):
        # Callers' raw DLL access: SetSnesConfig is recorded as part of the
        # cache key; any other function may change state the key cannot see
        fn = self._bind(name, result, *types)
        if name == 'SetSnesConfig':
            def configure(config):
                self.config_bytes = bytes(config)
                return fn(config)
            return configure
        self._go_live('raw DLL call ' + name)
        return fn

    def _go_live(self, reason):
        if self._cached_log is not None:
            raise RuntimeError(f'{reason} after a cached emulator result; construct Core(..., cache=False)')
        self.cache = False
        if self._pending:
            rom, script_path, script = self._pending
            self._pending = None
            self._load(rom, script_path, script)
            if self._started:
                self._start()

    def _configure_snes(self):
        # SetSnesConfig's installed x64 setter copies 0x2730 bytes by value
        setter = self._bind('SetSnesConfig', None, SnesConfig)
        code = C.string_at(C.cast(setter, C.c_void_p), 20)
        if (C.sizeof(SnesConfig) != 10032 or SnesConfig.ChannelVolumes.offset != 9968 or
                code[14:20] != bytes.fromhex('41 b8 30 27 00 00')):
            raise RuntimeError('Unaudited SNES configuration ABI')
        config = SnesConfig()
        config.Port1.Type = 1  # SnesController; otherwise the headless core has no controller
        config.DisableFrameSkipping = True
        config.EnableRandomPowerOnState = False
        config.RamPowerOnState = 1  # AllZeros, so repeated runs match
        config.GsuClockSpeed = 100
        config.BsxCustomDate = -1
        for i in range(8):
            config.ChannelVolumes[i] = 100
        setter(config)
        self.config_bytes = bytes(config)

    def load(self, rom, script_path, script):
        self._cached_log = None
        self._started = False
        self._pending = None
        if self.cache and run_cache.cacheable_script(script):
            self._pending = (rom, script_path, script)
            return
        if self.cache:
            run_cache.record('bypass', f'{Path(rom).name} (script not cacheable)')
        self._load(rom, script_path, script)

    def _load(self, rom, script_path, script):
        # Console mode creates the debugger before LoadRom starts the CPU,
        # allowing the core to carry the pre-load pause to the first instruction
        self._bind('SetEmulationFlag', None, C.c_uint32, C.c_bool)(CONSOLE_MODE, True)
        self._bind('Pause', None)()
        if not self._bind('LoadRom', C.c_bool, C.c_char_p, C.c_char_p)(str(Path(rom).resolve()).encode(), None):
            raise RuntimeError('Core could not load ROM')
        self.script_id = self._bind('LoadScript', C.c_int32, C.c_char_p, C.c_char_p, C.c_char_p, C.c_int32)(
            b'profile', str(script_path).encode(), script.encode(), -1)

    def log(self):
        if self._cached_log is not None:
            return self._cached_log
        if self._pending:
            return ''
        C.memset(self._log_buffer, 0, len(self._log_buffer))
        self._bind('GetScriptLog', None, C.c_int32, C.c_void_p, C.c_uint32)(
            self.script_id, self._log_buffer, len(self._log_buffer))
        return self._log_buffer.value.decode(errors='replace')

    def start(self):
        self._started = True
        if not self._pending:
            self._start()

    def _start(self):
        self._bind('Resume', None)()
        self._bind('ResumeExecution', None)()

    def resume(self):
        self._go_live('resume')
        self._bind('ResumeExecution', None)()

    def stopped(self):
        if self._cached_log is not None:
            return True
        self._go_live('stopped')
        return self._bind('IsExecutionStopped', C.c_bool)()

    def wait_for(self, tag, timeout):
        digest = None
        if self._pending:
            rom, script_path, script = self._pending
            digest = run_cache.key(kind='core', startup='paused', dll=self.dll_sha256, config=self.config_bytes.hex(),
                                   rom=run_cache.file_sha256(rom), script=script, tag=tag)
            entry = run_cache.get(digest, Path(rom).name)
            if entry is not None:
                self._pending = None
                self._cached_log = entry['log']
                return self._cached_log
            self._pending = None
            self._load(rom, script_path, script)
            if self._started:
                self._start()
        text = self._wait_for(tag, timeout)
        if digest:
            run_cache.put(digest, dict(log=text, rom=str(rom), tag=tag))
        return text

    def _wait_for(self, tag, timeout):
        # The Lua script logs tag and then breaks execution
        deadline = time.monotonic() + timeout
        while True:
            text = self.log()
            if tag in text and self._bind('IsExecutionStopped', C.c_bool)():
                return text
            if 'profile:' in text or 'error' in text.lower():
                raise RuntimeError('Lua failed: ' + text[-2000:])
            if time.monotonic() > deadline:
                raise RuntimeError('Timed out: ' + text[-2000:])
            time.sleep(0.02)

    def reset_profiler(self, cpu=CPU_SNES):
        self._go_live('reset_profiler')
        self._bind('ResetProfiler', None, C.c_int32)(cpu)

    def profiler_data(self, cpu=CPU_SNES):
        entries = (ProfiledFunction * 100000)()
        count = C.c_uint32(len(entries))
        self._go_live('profiler_data')
        self._bind('GetProfilerData', None, C.c_int32, C.c_void_p, C.POINTER(C.c_uint32))(
            cpu, entries, C.byref(count))
        return list(entries[:count.value])

    def close(self):
        self._bind('Stop', None)()
        self._bind('Release', None)()

    def close_with_log(self, path):
        """Close from a finally block, saving the transcript on failure or request."""
        failed = sys.exc_info()[0] is not None
        try:
            if failed or verbose():
                save_log(path, self.log(), failed=failed)
        finally:
            self.close()
