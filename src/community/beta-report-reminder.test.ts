import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { expect, it } from 'vitest'
import { BetaReportReminder } from './BugReportNotice'
import { CommunityContext, emptySession } from './context'
import { DEVELOPMENT_DISCORD_URL } from '../config/development-discord'
import type { Session } from './api'

const render = (session: Session) => renderToStaticMarkup(createElement(CommunityContext.Provider, { value: { session, refresh: async () => {}, refreshDeveloper: async () => {}, developer: null, catalog: [] } }, createElement(BetaReportReminder)))
const user = { id: 'm1', username: 'tester_1', displayName: 'Tester', verified: true }

it('reminds beta testers in the site’s report forms to report on Discord instead, and nobody else', () => {
  const html = render({ available: true, admin: false, user: { ...user, betaTester: true } })
  expect(html).toContain('#beta-testers on Discord')
  expect(html).toContain(`href="${DEVELOPMENT_DISCORD_URL}"`)
  expect(html).toContain('not through this form')
  expect(render({ available: true, admin: false, user })).toBe('')
  expect(render({ available: true, admin: true, user })).toBe('')
  expect(render(emptySession)).toBe('')
})
