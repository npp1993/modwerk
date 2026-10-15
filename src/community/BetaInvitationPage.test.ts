// @vitest-environment jsdom
import { act, createElement, type ReactNode } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { BetaInvitationPage } from './BetaInvitationPage'
import { BetaDiscordInvitation } from './BetaDiscordInvitation'
import { BrandName } from '../components/BrandName'
import { CommunityContext, emptySession } from './context'
import { BETA_RISKS_VERSION } from '../config/beta-invitation'
import { DEVELOPMENT_DISCORD_URL } from '../config/development-discord'
import type { Session } from './api'

const mocks = vi.hoisted(() => ({ api: vi.fn(), post: vi.fn(), refresh: vi.fn(async () => {}) }))
vi.mock('./api', () => ({ api: mocks.api, post: mocks.post }))
let root: Root, container: HTMLDivElement
const member: Session = { available: true, admin: false, user: { id: 'member', username: 'member', displayName: 'Member', verified: true } }
const pending = { status: 'pending', testers: 49, limit: 50, risksVersion: BETA_RISKS_VERSION }
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true); vi.clearAllMocks()
  mocks.api.mockResolvedValue(pending); mocks.post.mockResolvedValue({ ...pending, status: 'active', testers: 50 })
  container = document.createElement('div'); document.body.append(container); root = createRoot(container)
})
afterEach(async () => { await act(() => root.unmount()); container.remove(); vi.unstubAllGlobals() })
const render = (session: Session = member, child: ReactNode = createElement(BetaInvitationPage, { campaign: 'public' })) => act(() => root.render(createElement(CommunityContext.Provider, { value: { session, refresh: mocks.refresh, refreshDeveloper: async () => {}, developer: null, catalog: [] }, children: child })))

it('shows the risks to visitors and preserves this invitation as their sign-in destination', async () => {
  await render(emptySession)
  expect(container.textContent).toContain('make your device unusable')
  expect(container.textContent).toContain('Recovery is not guaranteed')
  expect(container.querySelector('a[href^="#account/login"]')?.getAttribute('href')).toBe('#account/login?next=beta%2Fjoin%2Fpublic')
  expect(container.querySelector('.beta-invitation-discord a')?.getAttribute('href')).toBe(DEVELOPMENT_DISCORD_URL)
  expect(mocks.api).not.toHaveBeenCalled(); expect(mocks.post).not.toHaveBeenCalled()
})
it('prompts for Discord on arrival while risk acceptance remains required before joining', async () => {
  await render()
  expect(mocks.post).not.toHaveBeenCalled()
  const discord = container.querySelector<HTMLAnchorElement>('.beta-invitation-discord a')!
  expect(discord.href).toBe(DEVELOPMENT_DISCORD_URL)
  expect(discord.target).toBe('_blank')
  expect(container.textContent).toContain('Join our development Discord')
  discord.addEventListener('click', event => event.preventDefault())
  await act(() => discord.click())
  expect(mocks.post).not.toHaveBeenCalled()
  const checkbox = container.querySelector<HTMLInputElement>('input[type=checkbox]')!
  const submit = container.querySelector<HTMLButtonElement>('button[type=submit]')!
  expect(checkbox.checked).toBe(false); expect(submit.disabled).toBe(true)
  await act(() => checkbox.click())
  expect(submit.disabled).toBe(false)
  await act(() => container.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })))
  expect(mocks.post).toHaveBeenCalledWith('/auth/beta-invitations/public', { acceptRisks: true, risksVersion: BETA_RISKS_VERSION })
  expect(mocks.refresh).toHaveBeenCalledOnce()
  expect(container.querySelector('h1')?.textContent).toBe('You have beta access')
  expect(container.querySelector('a')?.getAttribute('href')).toBe(DEVELOPMENT_DISCORD_URL)
  // The next step after joining is the Octatrack's setup, where the base install guide lives.
  expect([...container.querySelectorAll('a')].find(link => link.textContent === 'Set up your Octatrack')?.getAttribute('href')).toBe('#octatrack/setup')
})
it('shows a full pool with no join action, including when the last place disappears during acceptance', async () => {
  await render()
  await act(() => container.querySelector<HTMLInputElement>('input')!.click())
  mocks.post.mockRejectedValueOnce(new Error('The beta tester pool is full (50 people).'))
  mocks.api.mockResolvedValue({ ...pending, status: 'full', testers: 50 })
  await act(() => container.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })))
  expect(container.textContent).toContain('All 50 beta places are taken')
  expect(container.querySelector('input')).toBeNull()
})
it('prompts existing testers for Discord and records their choice, with branding tied to real access', async () => {
  mocks.api.mockResolvedValue({ show: true })
  const beta = { ...member, user: { ...member.user!, betaTester: true } }
  await render(beta, createElement('div', {}, createElement(BrandName, { session: beta }), createElement(BetaDiscordInvitation)))
  expect(container.querySelector('.brand-beta-badge')?.textContent).toBe('Beta')
  expect(container.textContent).toContain('Join the beta testers on Discord')
  mocks.post.mockResolvedValue({ ok: true })
  await act(() => container.querySelector<HTMLButtonElement>('button')!.click())
  expect(mocks.post).toHaveBeenCalledWith('/auth/beta-discord-invite', {})
  expect(container.querySelector('aside')).toBeNull()
  await render(member, createElement('div', {}, createElement(BrandName, { session: member }), createElement(BetaDiscordInvitation)))
  expect(container.querySelector('.brand-beta-badge')).toBeNull()
  expect(container.querySelector('aside')).toBeNull()
})
