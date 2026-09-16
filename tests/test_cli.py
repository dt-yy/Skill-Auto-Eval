from pathlib import Path
import os, subprocess, sys
ROOT = Path(__file__).parents[1]
def run(*args):
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'))
    return subprocess.run([sys.executable, '-m', 'skill_eval.cli', *args], cwd=ROOT, env=env, capture_output=True, text=True)
def test_help():
    result = run('--help')
    assert result.returncode == 0
    assert 'install' in result.stdout and 'run' in result.stdout
def test_missing_skill():
    result = run('run', '--skill', str(ROOT / 'missing'), '--suite', 'security')
    assert result.returncode == 2
    assert 'does not exist' in result.stderr
