// Pulls the private Octatrack diagnostics members chose to share, for the owner and the owner's agents.
// It uses a read-only key that opens only GET /api/admin/octatrack/diagnostics; the Worker holds its SHA-256.
// Not part of npm run check. See docs/APP_DEVELOPMENT.md#private-diagnostics.
//
//   npm run diagnostics:pull -- --init   # once: put a key in the macOS Keychain and print the Worker secret
//   npm run diagnostics:pull             # write every retained record to ~/.cache/modwerk-local/diagnostics/latest.json
import { createHash, randomBytes } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { chmodSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const ROOT = new URL('..', import.meta.url)
const SERVICE = 'modwerk-diagnostics-read'
const API = process.env.MODWERK_API_URL ?? 'https://octamod-community.octamod.workers.dev/api'
const OUT = join(homedir(), '.cache/modwerk-local/diagnostics')
const PAGE = 500
const PROBLEMS = ['sync_failed', 'build_failed', 'browser_error', 'unhandled_rejection', 'unresponsive']

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

/** This computer's local time, as Discord shows it. */
export const when = iso => new Date(iso).toLocaleString('sv-SE', { dateStyle: 'short', timeStyle: 'short' })
const line = ({ createdAt, username, data }) => [when(createdAt), '@' + username, data.event, data.phase,
  data.error && 'error=' + data.error, data.result && 'result=' + data.result, data.refusal !== undefined && 'refusal=' + data.refusal,
  data.buildKind, data.area && 'area=' + data.area, data.kind && 'type=' + data.kind, data.reason && 'reason=' + data.reason,
  data.live?.cpu && 'cpu ' + data.live.cpu.map(percent).join('/'), data.modules?.map(module => module.id + '@' + module.catalogVersion).join(',')].filter(Boolean).join(' ')
function percent(permille) { return (permille / 10).toFixed(1) + '%' }
/** An incident from the unit's own log (diag.c): when in its session, what, and what the unit was doing. */
const incident = r => `#${r.seq} start ${r.boot} +${Math.floor(r.second / 60)}m${r.second % 60}s ${r.kind}` +
  (r.kind === 'freeze' ? (r.a ? ` ${(r.a * 16 / 44100).toFixed(1)} s` : ' until a restart') : r.kind === 'hot' ? ` (${r.a} half-seconds at 90 %+)` : r.kind === 'crash' ? ` pc 0x${r.a.toString(16)}` : r.kind === 'stall' ? ` reason ${r.a}` : '') +
  (r.kind === 'crash' || r.kind === 'stall' ? '' : `, cpu ${percent(r.cpu)} T1-4 ${percent(r.dsp1to4)} T5-8 ${percent(r.dsp5to8)}, ${r.playing ? 'playing' : 'stopped'} at ${(r.tempo24 / 24).toFixed(1)} BPM, screen 0x${r.screen.toString(16)}` +
    `, keys ${r.keys.filter(k => k !== 255).map(k => k.toString(16)).join(' ') || '-'}, fx ${r.fx.map(f => f.toString(16)).join(' ')}, machines ${r.machines.join(' ')}`)

/** Each member's records in order: the bases, restarts, the last finished self-test and the event counts. */
export function members(events) {
  const found = new Map()
  for (const { username, createdAt, data } of [...events].sort((a, b) => a.createdAt.localeCompare(b.createdAt))) {
    const member = found.get(username) ?? { last: '', kinds: {}, bases: [], restarts: [], active: '', selftest: undefined }
    member.last = createdAt
    member.kinds[data.event] = (member.kinds[data.event] ?? 0) + 1
    if (data.base && member.bases.at(-1) !== data.base) member.bases.push(data.base)
    // A plain reconnect keeps the running set's identity; only a restart brings the unit back on the bare base.
    if (data.event === 'connected' && data.active === data.base && member.active && member.active !== data.base) member.restarts.push(createdAt)
    if (data.active) member.active = data.active
    if (data.event === 'load' && data.live) member.live = { ...data.live, at: createdAt }
    // The unit's log arrives in pieces and can arrive twice: keep each record once, by its start and seq.
    for (const r of data.log?.incidents ?? []) (member.incidents ??= new Map()).set(r.boot + '/' + r.seq, r)
    for (const r of data.log?.loads ?? []) (member.loads ??= new Map()).set(r.boot + '/' + r.seq, r)
    if (data.event === 'selftest' && data.reading?.state >= 2) {
      member.selftest = data.reading
      // Peaks are measured only while DSP modules run; a test without them leaves zeros.
      if (data.reading.ran && data.reading.cpu >= (member.peak?.cpu ?? 0)) member.peak = { ...data.reading, at: createdAt }
    }
    found.set(username, member)
  }
  return found
}

/** Site reports by the Modwerk username their body links to, from `gh issue list --json number,title,state,body`. */
export function reportsByMember(issues) {
  const found = new Map()
  for (const issue of issues) {
    const name = issue.body?.match(/modwerk\.app\/forum\/profile\/([A-Za-z0-9_]+)\//)?.[1]
    if (name) found.set(name, [...found.get(name) ?? [], issue])
  }
  return found
}

export function summary({ events, counts }, { base = '', reports = new Map() } = {}) {
  const found = members(events)
  const problems = events.filter(({ data }) => PROBLEMS.includes(data.event) || data.error || (data.result && data.result !== 'ok'))
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  const days = Map.groupBy(counts, row => row.day)
  const baseName = hash => hash.slice(0, 8) + (!base ? '' : hash === base ? ' (the site’s current base)' : ' (older than the site’s ' + base.slice(0, 8) + ')')
  return [
    `${events.length} records from ${found.size} members (last 30 days; times are this computer's)`,
    ...[...found].sort((a, b) => b[1].last.localeCompare(a[1].last)).flatMap(([name, member]) => [
      '', `@${name}  last ${when(member.last)}` + (member.bases.length ? '  base ' + member.bases.map(baseName).join(' → ') : ''),
      ...(reports.get(name) ?? []).map(issue => `  report #${issue.number} ${issue.state.toLowerCase()}: ${issue.title}`),
      ...member.restarts.length ? [`  restarts ${member.restarts.length}: ${member.restarts.map(when).join(', ')} (came back on the bare base)`] : [],
      ...member.selftest ? [`  last self-test ${member.selftest.state === 2 ? 'passed' : 'failed (bits ' + member.selftest.failed + ')'}` + (member.selftest.ran ? '' : ', no DSP module ran')] : [],
      ...member.peak ? [`  highest self-test peaks ${when(member.peak.at)}: CPU ${percent(member.peak.cpu)}, DSP T1-4 ${percent(member.peak.tracks1to4)}, T5-8 ${percent(member.peak.tracks5to8)}`] : [],
      ...member.live ? [`  live load ${when(member.live.at)}: CPU ${member.live.cpu?.map(percent).join(' mean, ') ?? '-'} peak, T1-4 ${member.live.dsp1to4?.map(percent).join('/') ?? '-'}, T5-8 ${member.live.dsp5to8?.map(percent).join('/') ?? '-'} (${member.live.samples} readings)`] : [],
      ...member.loads?.size ? [`  unit's load log: ${member.loads.size} five-minute records, CPU peak ${percent(Math.max(...[...member.loads.values()].map(r => r.cpu[1])))}, mean ${percent([...member.loads.values()].reduce((a, r) => a + r.cpu[0], 0) / member.loads.size)}`] : [],
      ...[...member.incidents?.values() ?? []].filter(r => r.kind !== 'start').sort((a, b) => a.boot - b.boot || a.seq - b.seq).slice(-12).map(r => '  unit: ' + incident(r)),
      '  ' + Object.entries(member.kinds).map(([kind, n]) => kind + ' ' + n).join(', '),
    ]),
    '', 'Self-test peaks are measured only while DSP modules run. Live load comes from the site while connected; the unit\'s log covers the time without it. Screen codes are stock input layers, keys stock key codes.',
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
  const from = new Date(Date.now() - 30 * 86400000).toISOString()
  const data = await pullAll(page, from)
  // Replaced on every pull, so the copy never keeps records the server has expired or a member withdrew.
  mkdirSync(OUT, { recursive: true, mode: 0o700 })
  const file = join(OUT, 'latest.json')
  writeFileSync(file, JSON.stringify({ pulledAt: new Date().toISOString(), ...data }, null, 2), { mode: 0o600 })
  chmodSync(file, 0o600)
  const base = JSON.parse(readFileSync(new URL('sdk/machines/octatrack/base-binding.json', ROOT), 'utf8')).identity
  let reports = new Map(), note = ''
  try {
    reports = reportsByMember(JSON.parse(execFileSync('gh', ['issue', 'list', '--label', 'issue-report', '--state', 'all', '--limit', '300',
      '--search', 'created:>=' + from.slice(0, 10), '--json', 'number,title,state,body'], { cwd: fileURLToPath(ROOT), encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] })))
  } catch (error) { note = '\n\nGitHub reports not matched: ' + (error.stderr?.toString().trim() || error.message) }
  console.log(summary(data, { base, reports }) + note + '\n\nEvery record: ' + file)
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { console.error(error.message); process.exit(1) })
}
