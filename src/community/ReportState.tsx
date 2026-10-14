import type { ComponentProps } from 'react'
import { Icon, type IconName } from '../components/Icon'
import { reportStatusLabel, reportTone, type ReportMetadata, type ReportTone } from './report-closure'

// The same marks as the library card: a speech bubble for a report to review, a question mark while the reporter is
// asked for details, a warning for a confirmed bug.
const ICONS: Record<ReportTone, IconName> = { review: 'message', waiting: 'help', confirmed: 'warn', fixed: 'check', closed: 'close' }

/** A report's state as a colored chip: its label, its mark and its tone. Use it wherever a report's state is shown. */
export function ReportState({ report, ...rest }: { report: ReportMetadata & { status: string } } & Omit<ComponentProps<'span'>, 'children' | 'className'>) {
  const tone = reportTone(report)
  return <span {...rest} className="report-state" data-tone={tone}><Icon name={ICONS[tone]} size={14} />{reportStatusLabel(report)}</span>
}
