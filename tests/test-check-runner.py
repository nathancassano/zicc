"""Exercise runner scheduling, failure reporting and inherited MSVC setup."""
import contextlib
import importlib.util
import io
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('runner', ROOT / 'tools/run-checks.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
ARITH_SPEC = importlib.util.spec_from_file_location('arithmetic', ROOT / 'tests/check-small-integers.py')
arithmetic = importlib.util.module_from_spec(ARITH_SPEC)
ARITH_SPEC.loader.exec_module(arithmetic)
COMPILER_SPEC = importlib.util.spec_from_file_location('compiler_check', ROOT / 'tests/check-compiler.py')
compiler_check = importlib.util.module_from_spec(COMPILER_SPEC)
COMPILER_SPEC.loader.exec_module(compiler_check)
PARTS = [name for name, _ in compiler_check.PARTS] + ['cases']


def manifests(command, *args, **kwargs):
    # --list-parts and --list-batches answered like the real suites
    if '--list-parts' in command:
        if 'tests/check-frames.py' in command:return SimpleNamespace(stdout=json.dumps(['abi','guards']))
        if 'tests/check-strength.py' in command:return SimpleNamespace(stdout=json.dumps(['core','affine-loops','dp-counters','loop-unroll']))
        if 'tests/check-banked-rom.py' in command:return SimpleNamespace(stdout=json.dumps(['packing','abi-1','assets']))
        return SimpleNamespace(stdout=json.dumps(PARTS))
    if '--list-workers' in command:return SimpleNamespace(stdout=json.dumps([dict(index=0),dict(index=1)]))
    return SimpleNamespace(stdout=json.dumps(arithmetic.batch_plan()))


class RunnerTests(unittest.TestCase):
    def test_child_failure_retains_log_and_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            result = runner.run_suite('failure', [sys.executable, '-c',
                'import sys; print("diagnostic", flush=True); sys.exit(7)'],
                os.environ.copy(), Path(directory), time.perf_counter())
            self.assertEqual(result['exit_code'], 7)
            self.assertIn('diagnostic', (Path(directory) / 'failure.log').read_text())

    def test_missing_executable_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            result = runner.run_suite('missing', [str(Path(directory) / 'missing.exe')],
                os.environ.copy(), Path(directory), time.perf_counter())
            self.assertNotEqual(result['exit_code'], 0)
            self.assertTrue(result['error'])

    def test_split_suite_transcript_keeps_jobs_and_isolates_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            results = [runner.run_suite(f'part-{code}', [sys.executable, '-c',
                       f'import sys; print("message {code}"); sys.exit({code})'],
                       os.environ.copy(), output, time.perf_counter(), suite='suite')
                       for code in (0, 7)]
            self.assertEqual({path.name for path in output.iterdir()},
                             {'suite.log', 'part-7.failure.log'})
            transcript = (output / 'suite.log').read_bytes()
            for code, row in zip((0, 7), results):
                offset = row['log_offset']
                self.assertIn(f'message {code}'.encode(), transcript[offset:offset + row['log_length']])
            self.assertIn('message 7', (output / 'part-7.failure.log').read_text())

    def test_cache_counts_and_optional_traces_include_subprocess_events(self):
        command = [sys.executable, '-c',
                   'import sys; sys.path.insert(0, "tools"); import run_cache, host_cache; '
                   'from pathlib import Path; run_cache.record("hit", "rom", "abc"); '
                   'run_cache.record("hit", "other rom"); host_cache.record("miss", Path("fixture.c"))']
        for trace in (False, True):
            with self.subTest(trace=trace), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'run'
                argv = ['run-checks.py', '--suite', 'relax', '--output', str(output)]
                if trace:
                    argv.append('--cache-trace')
                tasks = [dict(name='relax', suite='relax', command=command)]
                with patch.object(sys, 'argv', argv), \
                        patch.object(runner, 'msvc_environment', return_value=(os.environ.copy(), 0)), \
                        patch.object(runner, 'plan_tasks', return_value=(tasks, {})), \
                        patch.object(runner, 'sha256', return_value='test-hash'), \
                        patch.object(runner, 'STATE', Path(directory) / 'state.json'), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(runner.main(), 0)
                summary = json.loads((output / 'summary.json').read_text())
                self.assertEqual(summary['tasks'][0]['cache'], {'hit': 2, 'host-miss': 1})
                database = output / 'cache-events.sqlite3'
                self.assertEqual(database.exists(), trace)
                if trace:
                    with contextlib.closing(sqlite3.connect(database)) as connection:
                        self.assertEqual(connection.execute('SELECT kind, digest, label FROM events').fetchall(),
                                         [('hit', 'abc', 'rom'), ('hit', '', 'other rom'),
                                          ('host-miss', '', 'fixture.c')])

    def test_inherited_msvc_does_not_initialize_again(self):
        with patch.dict(os.environ, {'VSCMD_ARG_TGT_ARCH': 'x64'}), \
                patch.object(runner.subprocess, 'run') as run:
            env, count = runner.msvc_environment()
            self.assertEqual(env['VSCMD_ARG_TGT_ARCH'], 'x64')
            self.assertEqual(count, 0)
            run.assert_not_called()

    def test_bounded_concurrency_completes_after_failure_and_sets_up_once(self):
        active = maximum = 0
        lock = threading.Lock()
        completed = []

        def fake_suite(name, command, env, output, started, *, suite=None):
            nonlocal active, maximum
            with lock:
                if name == 'small-integers-collect':
                    self.assertEqual(sum(n.startswith('small-integers-') for n in completed), 50)
                active += 1
                maximum = max(maximum, active)
            begin = time.perf_counter() - started
            time.sleep(0.01)
            with lock:
                active -= 1
                completed.append(name)
            return dict(name=name, exit_code=int(name == 'compiler-cases'), command=command,
                        start_seconds=begin, seconds=0.01, log='test.log')

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'run'
            argv = ['run-checks.py', '--jobs', '2', '--output', str(output)]
            with patch.object(sys, 'argv', argv), \
                    patch.object(runner, 'msvc_environment', return_value=({}, 1)) as setup, \
                    patch.object(runner, 'run_suite', side_effect=fake_suite), \
                    patch.object(runner.subprocess, 'run', side_effect=manifests), \
                    patch.object(runner, 'STATE', Path(directory) / 'state.json'), \
                    patch.object(runner, 'sha256', return_value='test-hash'), \
                    contextlib.redirect_stdout(io.StringIO()):
                # Whole suites and arithmetic batches must share the same pool
                self.assertEqual(runner.main(), 1)
            setup.assert_called_once()
            self.assertEqual(maximum, 2)
            summary = json.loads((output / 'summary.json').read_text())
            self.assertEqual([r['name'] for r in summary['suites']],
                             [name for name, _ in runner.SUITES])
            self.assertEqual(sum(r['exit_code'] != 0 for r in summary['suites']), 1)
            # 25 whole suites, one job per compiler part and 50 arithmetic batches
            self.assertEqual(len(PARTS), len(set(PARTS)))
            self.assertEqual(sum('batch' in r for r in summary['tasks']),50)
            self.assertEqual(len({r['name'] for r in summary['tasks']}),len(summary['tasks']))
            compiler = next(row for row in summary['suites'] if row['name'] == 'compiler')
            self.assertEqual((compiler['part_count'], compiler['exit_code']), (len(PARTS), 1))
            small = next(row for row in summary['suites'] if row['name'] == 'small-integers')
            self.assertEqual(small['batch_count'], 50)
            self.assertTrue(all('--expect-widths' in task['command']
                                for task in summary['tasks'] if task['suite'] == 'small-integers'))

    def test_failed_batch_does_not_collect_stale_results(self):
        calls = []

        def fake_suite(name, command, env, output, started, *, suite=None):
            calls.append(name)
            return dict(name=name, command=command, exit_code=int(name.endswith('-00')),
                        start_seconds=0, seconds=0.01, log='test.log')

        manifest = [dict(kind='word', batch=i, cases=1) for i in range(2)]
        with tempfile.TemporaryDirectory() as directory:
            argv = ['run-checks.py', '--suite', 'small-integers', '--jobs', '2',
                    '--output', str(Path(directory)/'run')]
            with patch.object(sys, 'argv', argv), \
                    patch.object(runner, 'msvc_environment', return_value=({}, 1)), \
                    patch.object(runner, 'run_suite', side_effect=fake_suite), \
                    patch.object(runner, 'sha256', return_value='test-hash'), \
                    patch.object(runner, 'STATE', Path(directory) / 'state.json'), \
                    patch.object(runner.subprocess, 'run', return_value=SimpleNamespace(stdout=json.dumps(manifest))), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(), 1)
            self.assertEqual(set(calls), {'small-integers-word-00', 'small-integers-word-01'})

    def run_main(self, directory, argv, fake_suite, run_number):
        output = Path(directory) / f'run{run_number}'
        with patch.object(sys, 'argv', ['run-checks.py', *argv, '--output', str(output)]), \
                patch.object(runner, 'msvc_environment', return_value=({}, 1)), \
                patch.object(runner, 'run_suite', side_effect=fake_suite), \
                patch.object(runner.subprocess, 'run', side_effect=manifests), \
                patch.object(runner, 'STATE', Path(directory) / 'state.json'), \
                contextlib.redirect_stdout(io.StringIO()):
            code = runner.main()
        return code, json.loads((output / 'summary.json').read_text())

    def test_compiler_parts_are_isolated_jobs(self):
        seen = {}

        def fake_suite(name, command, env, output, started, *, suite=None):
            seen[name] = (command, env)
            return dict(name=name, command=command, exit_code=0, start_seconds=0, seconds=0.01, log='test.log')

        with tempfile.TemporaryDirectory() as directory:
            code, summary = self.run_main(directory, ['--suite', 'compiler', '--jobs', '3'], fake_suite, 1)
        self.assertEqual(code, 0)
        self.assertEqual({r['part'] for r in summary['tasks']},set(PARTS))
        ordinary=[(command,env) for command,env in seen.values() if 'ZICC_COMPILER_CHECK_OUT' in env]
        outputs={env['ZICC_COMPILER_CHECK_OUT'] for _,env in ordinary}
        self.assertEqual(len(outputs),len(ordinary))
        self.assertEqual(len({env['ZICC_CACHE_EVENT_DB'] for _,env in seen.values()}), 1)
        self.assertEqual({env['ZICC_CACHE_EVENT_JOB'] for _,env in seen.values()}, set(seen))
        self.assertTrue(any(name.endswith('-setup') for name in seen))
        self.assertTrue(any(name.endswith('-collect') for name in seen))
        self.assertEqual(summary['suites'][0]['part_count'], len(PARTS))

    def test_changed_skips_only_suites_that_last_passed_unchanged(self):
        calls, failing = [], {'relax'}

        def fake_suite(name, command, env, output, started, *, suite=None):
            calls.append((name, env['ZICC_RUN_CACHE']))
            return dict(name=name, command=command, exit_code=int(name in failing),
                        start_seconds=0, seconds=0.01, log='test.log')

        with tempfile.TemporaryDirectory() as directory:
            suites = ['--suite', 'relax', '--suite', 'decimal', '--jobs', '1']
            self.assertEqual(self.run_main(directory, suites + ['--no-cache'], fake_suite, 1)[0], 1)
            self.assertEqual(sorted(calls), [('decimal', '0'), ('relax', '0')])
            calls.clear();failing.clear()
            # decimal passed with these inputs; relax failed, so it runs again
            code, summary = self.run_main(directory, suites + ['--changed'], fake_suite, 2)
            self.assertEqual((code, calls), (0, [('relax', '1')]))
            calls.clear()
            self.assertEqual(self.run_main(directory, suites + ['--changed'], fake_suite, 3)[0], 0)
            self.assertEqual(calls, [])
            with patch.object(runner, 'global_fingerprint', return_value='new compiler'):
                self.run_main(directory, suites + ['--changed'], fake_suite, 4)
            self.assertEqual(sorted(name for name, _ in calls), ['decimal', 'relax'])

    def test_changed_selects_suites_that_read_edited_fixture(self):
        def fake_suite(name, command, env, output, started, *, suite=None):
            return dict(name=name, command=command, exit_code=0, start_seconds=0,
                        seconds=0.01, log='test.log')

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tests').mkdir()
            for name in ('check-compiler.py', 'check-strength.py', 'check-affine-loops.py',
                         'check-multidimensional.py', 'check-decimal.py', 'multidimensional_cases.c'):
                shutil.copyfile(ROOT / 'tests' / name, root / 'tests' / name)
            (root / 'build').mkdir()
            (root / 'build/zicc.exe').write_bytes(b'compiler fingerprint fixture')
            (root / 'linker').mkdir()
            linker = root / 'linker/lorom32.cfg'
            linker.write_text('# original')
            fixture = root / 'tests/multidimensional_cases.c'
            suites = ['--suite', 'compiler', '--suite', 'strength', '--suite', 'decimal', '--jobs', '1']
            with patch.object(runner, 'ROOT', root):
                self.assertEqual(self.run_main(directory, suites, fake_suite, 1)[0], 0)
                with fixture.open('a') as stream:
                    stream.write('\n/* fixture-only edit */\n')
                code, summary = self.run_main(directory, suites + ['--changed'], fake_suite, 2)
                self.assertEqual(code, 0)
                self.assertEqual({row['name'] for row in summary['suites']}, {'compiler', 'strength'})
                linker.write_text('# changed')
                code, summary = self.run_main(directory, suites + ['--changed'], fake_suite, 3)
                self.assertEqual(code, 0)
                self.assertEqual({row['name'] for row in summary['suites']}, {'compiler', 'strength', 'decimal'})

    def test_manifest_covers_every_vector_and_partial_tail(self):
        plan = arithmetic.batch_plan()
        self.assertEqual(len(plan), 50)
        self.assertEqual(len({(p['kind'], p['batch']) for p in plan}), 50)
        self.assertEqual(sum(p['cases'] for p in plan), 200873)
        for kind in ('byte', 'signed-byte', 'word'):
            self.assertEqual(sum(p['cases'] for p in plan if p['kind'] == kind),
                             len(arithmetic.vectors(kind)))
        self.assertEqual(plan[-1], dict(kind='word', batch=17, cases=169))

    def test_collector_requires_complete_counts_and_preserves_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            compiler, runtime = root/'compiler', root/'runtime'
            compiler.write_bytes(b'compiler'); runtime.write_bytes(b'runtime')
            args = SimpleNamespace(compiler=compiler, runtime_object=runtime,
                                   output=root, expect_widths=True)
            plan = [dict(kind='word', batch=0, cases=2), dict(kind='word', batch=1, cases=3)]
            with self.assertRaises(FileNotFoundError):
                arithmetic.collect_results(args, plan)
            for item in reversed(plan):
                folder = root/'word'/str(item['batch']); folder.mkdir(parents=True)
                data = dict(cases=item['cases'], compiler_sha256=hashlib.sha256(b'compiler').hexdigest(),
                            runtime_sha256=hashlib.sha256(b'runtime').hexdigest(), poisoned_high_words=True)
                (folder/'results.json').write_text(json.dumps(data))
            tail = root/'word/1/results.json'
            good = tail.read_text(); bad = json.loads(good); bad['cases'] = 2
            tail.write_text(json.dumps(bad))
            with self.assertRaises(AssertionError):
                arithmetic.collect_results(args, plan)
            self.assertFalse((root/'results.json').exists())
            tail.write_text(good)
            arithmetic.collect_results(args, plan)
            result = json.loads((root/'results.json').read_text())['word']
            self.assertEqual(result['cases'], 5)
            self.assertEqual([b['cases'] for b in result['batches']], [2, 3])


class DependencyTests(unittest.TestCase):
    def test_released_work_precedes_ready_queue_and_uses_duration(self):
        order=[];rows=[]
        tasks=[dict(name='known-short',suite='x',command=[]),
               dict(name='setup',suite='x',command=[]),
               dict(name='known-long',suite='x',command=[]),
               dict(name='worker',suite='x',command=[],requires=['setup']),
               dict(name='collect',suite='x',command=[],requires=['worker'])]
        def execute(task):
            order.append(task['name'])
            return dict(name=task['name'],exit_code=0,start_seconds=0,seconds=1)
        with patch.object(runner,'previous_durations',return_value={'known-short':1,'known-long':10}):
            runner.schedule(tasks,1,execute,{},lambda t,r:rows.append(r))
        self.assertEqual(order,['setup','worker','collect','known-long','known-short'])

    def test_failed_setup_blocks_descendants_and_finishes_other_work(self):
        calls=[];rows=[]
        tasks=[dict(name='setup',command=[]),dict(name='worker',command=[],requires=['setup']),
               dict(name='collect',command=[],requires=['worker']),dict(name='other',command=[])]
        def execute(task):
            calls.append(task['name'])
            return dict(name=task['name'],exit_code=int(task['name']=='setup'),start_seconds=0,seconds=1)
        with patch.object(runner,'previous_durations',return_value={}):
            result=runner.schedule(tasks,2,execute,{},lambda t,r:rows.append(r))
        self.assertEqual(set(calls),{'setup','other'})
        self.assertEqual(len(rows),4)
        self.assertEqual(result['collect']['exit_code'],1)

    def test_cache_classifier_and_png_stdout(self):
        sys.path.insert(0,str(ROOT/'tools'))
        import run_cache
        self.assertTrue(run_cache.cacheable_script('local function require_value(x) end'))
        self.assertFalse(run_cache.cacheable_script('require("module")'))
        self.assertFalse(run_cache.cacheable_script('io.open("file")'))
        self.assertFalse(run_cache.cacheable_script('os.time()'))
        self.assertFalse(run_cache.cacheable_script('emu.takeScreenshot()'))
        self.assertTrue(run_cache.cacheable_script("local png=emu.takeScreenshot();print('PNG '..png:gsub('.',f))"))

    def test_screenshot_bytes_are_replayed_from_cached_stdout(self):
        import run_cache
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory);exe=out/'Mesen.exe';exe.write_bytes(b'emulator')
            rom=out/'fixture.sfc';rom.write_bytes(b'rom')
            lua=out/'fixture.lua';lua.write_text("local png=emu.takeScreenshot();print('PNG '..png:gsub('.',f))")
            png=b'\x89PNG\r\n\x1a\n'
            stdout='PNG '+png.hex()+'\nPASS\n'
            command=[exe,'--testRunner',rom,lua]
            with patch.dict(os.environ,{'ZICC_RUN_CACHE_DIR':str(out/'cache'),'ZICC_RUN_CACHE':'1'}), \
                 patch.object(compiler_check.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=stdout,stderr='')) as launch:
                first=compiler_check.run(command)
                replay=compiler_check.run(command)
            self.assertEqual(launch.call_count,1)
            self.assertEqual(first.stdout,replay.stdout)
            self.assertEqual(bytes.fromhex(replay.stdout.splitlines()[0][4:]),png)

    def test_host_cache_tracks_transitive_headers_and_flags(self):
        sys.path.insert(0,str(ROOT/'tools'))
        import host_cache
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'tools').mkdir();(root/'tools/msvc.cmd').write_text('cl %*')
            compiler=root/'cl.exe';compiler.write_bytes(b'compiler-version')
            source=root/'host.c';source.write_text('#include "header.h"')
            header=root/'header.h';header.write_text('original')
            target=root/'host.exe'
            command=[root/'tools/msvc.cmd',source,'/Fe'+str(target),'/O2']
            with patch.object(host_cache,'ROOT',root),patch.object(host_cache.shutil,'which',return_value=str(compiler)):
                plan=host_cache.prepare(command,root)
                self.assertNotIn('hit',plan)
                plan['dependency'].write_text(json.dumps({'Data':{'Includes':[str(header)]}}))
                target.write_bytes(b'executable')
                host_cache.store(plan,SimpleNamespace(returncode=0,stdout='compiled',stderr=''))
                target.unlink()
                self.assertIn('hit',host_cache.prepare(command,root))
                self.assertEqual(target.read_bytes(),b'executable')
                header.write_text('changed')
                changed=host_cache.prepare(command,root)
                self.assertNotIn('hit',changed);changed['dependency'].unlink()
                flags=host_cache.prepare(command+['/DCHANGED'],root)
                self.assertNotIn('hit',flags);flags['dependency'].unlink()


class DecimalQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('decimal_check',ROOT/'tests/check-decimal-assembly.py')
        cls.decimal=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.decimal)

    def test_manifest_preserves_numeric_vectors_and_hexval_range(self):
        d=self.decimal;plan=d.worker_plan()
        self.assertEqual(len({tuple(item.values()) for item in plan}),len(plan))
        for name in d.FUNCTIONS:
            count=65536 if name=='hexval' else (len(d.numeric.make_cases(name,{'fixture_rom':0x808000})) if name in d.BATCH_SIZES else 1)
            size=d.BATCH_SIZES.get(name,count)
            batches=[p['batch'] for p in plan if p['mode']=='reference' and p['region']=='ntsc' and p['name']==name]
            self.assertEqual(batches,list(range((count+size-1)//size)))
            self.assertEqual(sum(min(size,count-b*size) for b in batches),count)

    def test_collector_refuses_prior_setup_report(self):
        d=self.decimal;item=dict(mode='reference',region='ntsc',name='hexval',batch=0)
        with tempfile.TemporaryDirectory() as directory,patch.object(d,'OUT',Path(directory)), \
             patch.object(d,'worker_plan',return_value=[item]),patch.object(d,'fixture_hashes',return_value={}):
            (d.OUT/'setup.json').write_text(json.dumps(dict(run_id='new',fixtures={})))
            home=d.worker_home(**item);home.mkdir(parents=True)
            (home/'report.json').write_text(json.dumps(dict(run_id='old',worker=item)))
            with self.assertRaisesRegex(AssertionError,'stale decimal worker'):d.collect()
            self.assertFalse((d.OUT/'results.json').exists())


if __name__ == '__main__':
    unittest.main()
