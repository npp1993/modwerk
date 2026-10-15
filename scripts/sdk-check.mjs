import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { resolve, dirname } from 'node:path'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const python = process.platform === 'win32' ? 'python' : 'python3'
// Repository text is UTF-8, including on Windows hosts with an ANSI locale.
execFileSync(python, ['-X', 'utf8', '-B', '-m', 'unittest', 'discover', '-s', 'sdk/tests', '-v'], { cwd: root, stdio: 'inherit', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1', PYTHONUTF8: '1' } })
// Shared Octatrack host checks (no firmware, a few seconds): here, on every pull request, so a change that breaks them
// fails itself instead of every later module pull request (they ran only in module-pr.yml's octatrack-source before).
if (process.platform !== 'win32') {
  execFileSync('sh', ['sdk/runtime/upload/tests/run_host.sh'], { cwd: root, stdio: 'inherit' })
  execFileSync(python, ['-B', 'sdk/machines/octatrack/elekloader/test_recipe.py'], { cwd: root, stdio: 'inherit', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } })
}
