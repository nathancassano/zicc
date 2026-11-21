"""Keep raw check transcripts for failures or explicit diagnostics."""
import os


def verbose():
    return os.environ.get('ZICC_VERBOSE_LOGS') == '1'


def save_log(path, text, *, failed=False):
    if failed or verbose():
        path.write_text(text, encoding='utf-8', errors='backslashreplace')
