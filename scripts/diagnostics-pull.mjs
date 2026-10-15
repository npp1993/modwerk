// Pulls the private Octatrack diagnostics members chose to share, for the owner and the owner's agents.
// It uses a read-only key that opens only GET /api/admin/octatrack/diagnostics; the Worker holds its SHA-256.
// Not part of npm run check. See docs/APP_DEVELOPMENT.md#private-diagnostics.
//
//   npm run diagnostics:pull -- --init   # once: put a key in the macOS Keychain and print the Worker secret
//   npm run diagnostics:pull             # write every retained record to ~/.cache/modwerk-local/diagnostics/latest.json
import { createHash, randomBytes } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { chmodSync, mkdirSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { pathToFileURL } from 'node:url'

const SERVICE = 'modwerk-diagnostics-read'
const API = process.env.MODWERK_API_URL ?? 'https://octamod-community.octamod.workers.dev/api'
const OUT = join(homedir(), '.cache/modwerk-local/diagnostics')
const PAGE = 500
const PROBLEMS = ['sync_failed', 'build_failed', 'browser_error', 'unhandled_rejection']

/** Pages through every retained record, oldest first; `page(since)` answers with the endpoint's JSON. */
export async function pullAll(page, from) {
  const events = new Map()
  let since = from, counts
  for (;;) {
    const body = await page(since)
    counts = body.counts
    for (const entry of body.events) events.set(entry.username + '/' + entry.eventId, entry)
    const last = body.events.at(-1)?.createdAt
    // shortcut: a full page sharing one timestamp ends the pull early; uploads are capped at 120 an hour per member.
    if (body.events.length < PAGE || !last || last === since) break
    since = last
  }
  return { events: [...events.values()], counts }
}

const line = ({ createdAt, username, data }) => [createdAt.slice(0, 16), '@' + username, data.event, data.phase,
  data.error && 'error=' + data.error, data.result && 'result=' + data.result, data.refusal !== undefined && 'refusal=' + data.refusal,
  data.buildKind, data.modules?.map(module => module.id + '@' + module.catalogVersion).join(',')].filter(Boolean).join(' ')

export function summary({ events, counts }) {
  const testers = new Map()
  for (const entry of events) {
    const tester = testers.get(entry.username) ?? { last: '', kinds: {} }
    tester.last = entry.createdAt > tester.last ? entry.createdAt : tester.last
    tester.kinds[entry.data.event] = (tester.kinds[entry.data.event] ?? 0) + 1
    testers.set(entry.username, tester)
  }
  const problems = events.filter(({ data }) => PROBLEMS.includes(data.event) || data.error || (data.result && data.result !== 'ok'))
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  const days = Map.groupBy(counts, row => row.day)
  return [
    `${events.length} records from ${testers.size} members (last 30 days)`,
    ...[...testers].sort((a, b) => b[1].last.localeCompare(a[1].last))
      .map(([name, { last, kinds }]) => `  @${name}  last ${last.slice(0, 16)}  ` + Object.entries(kinds).map(([kind, n]) => kind + ' ' + n).join(', ')),
    '', `Problems (${problems.length}, newest first, up to 30):`, ...problems.slice(0, 30).map(entry => '  ' + line(entry)),
    '', 'Daily USB sync counts (everyone, sharing or not):',
    ...[...days].map(([day, rows]) => '  ' + day + '  ' + rows.map(row => row.event.replace('usb_sync_', '') + ' ' + row.count).join(', ')),
  ].join('\n')
}

function keychainKey() {
  try { return execFileSync('security', ['find-generic-password', '-s', SERVICE, '-w'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim() }
  catch { return '' }
}

async function main() {
  if (process.argv.includes('--init')) {
    let key = keychainKey()
    if (!key) {
      key = randomBytes(32).toString('hex')
      execFileSync('security', ['add-generic-password', '-s', SERVICE, '-a', 'modwerk', '-w', key])
    }
    console.log(`The read key is in the macOS Keychain as "${SERVICE}". Set this Worker secret on octamod-community`)
    console.log('(Cloudflare dashboard: Workers & Pages > octamod-community > Settings > Variables and Secrets, type Secret):')
    console.log('  DIAGNOSTICS_READ_KEY_SHA256 = ' + createHash('sha256').update(key).digest('hex'))
    return
  }
  const key = process.env.MODWERK_DIAGNOSTICS_KEY || keychainKey()
  if (!/^[a-f0-9]{64}$/.test(key)) throw new Error('No read key. Run npm run diagnostics:pull -- --init first.')
  const page = async since => {
    const response = await fetch(API + '/admin/octatrack/diagnostics?since=' + encodeURIComponent(since), { headers: { 'X-Modwerk-Diagnostics': key } })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${body.error ?? 'not JSON'}` + (response.status === 403 ? ' Is DIAGNOSTICS_READ_KEY_SHA256 the hash --init printed, and is the Worker deployed with this change?' : ''))
    return body
  }
  const data = await pullAll(page, new Date(Date.now() - 30 * 86400000).toISOString())
  // Replaced on every pull, so the copy never keeps records the server has expired or a member withdrew.
  mkdirSync(OUT, { recursive: true, mode: 0o700 })
  const file = join(OUT, 'latest.json')
  writeFileSync(file, JSON.stringify({ pulledAt: new Date().toISOString(), ...data }, null, 2), { mode: 0o600 })
  chmodSync(file, 0o600)
  console.log(summary(data) + '\n\nEvery record: ' + file)
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { console.error(error.message); process.exit(1) })
}
