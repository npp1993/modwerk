import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { reportTone, type ReportMetadata } from './report-closure'
import { ReportState } from './ReportState'

type Report = ReportMetadata & { status: string }
const open: Report = { status: 'open' }

describe('report state tones', () => {
  it('reads an open report as review, waiting or confirmed, and a closed one as fixed or closed', () => {
    expect(reportTone(open)).toBe('review')
    expect(reportTone({ ...open, triage_state: 'untriaged' })).toBe('review')
    expect(reportTone({ ...open, triage_state: 'investigating' })).toBe('review')
    expect(reportTone({ ...open, triage_state: 'needs_info' })).toBe('waiting')
    expect(reportTone({ ...open, triage_state: 'confirmed' })).toBe('confirmed')
    expect(reportTone({ ...open, triage_state: 'awaiting_verification' })).toBe('confirmed')
    expect(reportTone({ ...open, triage_state: 'needs_info', confirmed_at: '2026-10-12' })).toBe('confirmed')
    expect(reportTone({ ...open, report_kind: 'question', triage_state: 'needs_info', confirmed_at: '2026-10-12' })).toBe('waiting')
    expect(reportTone({ status: 'closed', closure_reason: 'fixed' })).toBe('fixed')
    expect(reportTone({ status: 'closed', closure_reason: 'duplicate' })).toBe('closed')
    expect(reportTone({ status: 'closed' })).toBe('closed')
  })

  it('shows the label with the tone every list shares, and a mark that is not read aloud', () => {
    const waiting = renderToStaticMarkup(createElement(ReportState, { report: { ...open, triage_state: 'needs_info' } }))
    expect(waiting).toContain('class="report-state" data-tone="waiting"')
    expect(waiting).toContain('aria-hidden="true"')
    expect(waiting).toContain('>Waiting for reporter</span>')
    expect(renderToStaticMarkup(createElement(ReportState, { report: open }))).toContain('data-tone="review"')
    expect(renderToStaticMarkup(createElement(ReportState, { report: { ...open, triage_state: 'confirmed' } }))).toContain('>Confirmed bug</span>')
    expect(renderToStaticMarkup(createElement(ReportState, { report: { status: 'closed', closure_reason: 'fixed' } }))).toContain('data-tone="fixed"')
  })
})
