import { describe, expect, it } from 'vitest'
import { renderModuleUpdateCatchup } from '../../server/module-update-catchup'
import type { NotificationItem } from './notification-contract'

const urls = { app: 'https://modwerk.app/', settings: 'https://modwerk.app/#account/notifications', unsubscribe: 'https://modwerk.app/#account/unsubscribe/test-token' }
const item: NotificationItem = { id: 'catchup-item', kind: 'module_update', seen: false, created_at: '2026-10-19 10:00:00', thread_id: null, post_id: null, module_id: 'digitakt-euclidean', module_version: '1.1.5', actor: null, actorOfficial: false, title: 'Euclidean', excerpt: null, rating: null, issue_id: null, github_actor: null, url: '#digitakt/module/euclidean' }

describe('personal module update catch-up', () => {
  it('puts personalized versions near the beginning and keeps instrument-specific changelog links', () => {
    const mail = renderModuleUpdateCatchup([item], urls)
    expect(mail.subject).toBe('A few updates from me')
    expect(mail.text).toContain('Euclidean 1.1.5\nhttps://modwerk.app/#digitakt/module/euclidean?tab=changelog')
    expect(mail.html.indexOf('Updates for modules you follow')).toBeLessThan(mail.html.indexOf('BBD Delay is now'))
    expect(mail.html).toContain('/news/octatrack-beta-october.png')
    expect(mail.html).not.toContain('FOLLOWEDMODULEUPDATES')
    expect(mail.text).not.toMatch(/[—–]/)
    expect(mail.text).not.toContain('9% fewer')
  })

  it('uses activity consent and the ordinary signed unsubscribe link rather than news consent', () => {
    const mail = renderModuleUpdateCatchup([item], urls)
    expect(mail.html).toContain('you follow module updates')
    expect(mail.html).toContain(urls.unsubscribe)
    expect(mail.text).toContain('Unsubscribe from activity email: ' + urls.unsubscribe)
    expect(mail.text).not.toContain('opted in to Modwerk news')
    expect(mail.html).not.toContain('opted in to Modwerk news')
  })

  it('escapes names and versions in the module panel', () => {
    const mail = renderModuleUpdateCatchup([{ ...item, title: '<script>alert(1)</script>', module_version: '<b>1</b>' }], urls)
    expect(mail.html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
    expect(mail.html).toContain('&lt;b&gt;1&lt;/b&gt;')
    expect(mail.html).not.toContain('<script>')
  })
})
