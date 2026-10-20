// SPDX-License-Identifier: GPL-3.0-or-later
import { RECOVERY_FAQ, type RecoveryMachine } from './recovery-faq'

// How to get back to stock, ticked before a firmware file can be saved, as on elekloader's own page.
// The FAQ opens in a new tab, so the build in this one is kept.
export function RecoveryNotice({ machine, steps, checked, onChange }: { machine: RecoveryMachine; steps?: string; checked: boolean; onChange: (checked: boolean) => void }) {
  // Digitakt and Digitone builds come from elekloader, which changes only the main OS.
  const octatrack = machine === 'octatrack'
  return <div className="recovery-notice">
    <h3>Before you flash: how to get back to stock</h3>
    <p>{octatrack ? 'Your original OS file is the way back.' : 'Only the main OS changes and the bootloader is never touched, so your stock OS file is the way back.'} If the custom OS does not start: {steps ? steps.trim().replace(/\.$/, '') + '.' : 'see the guide linked below.'}</p>
    <p>{octatrack ? 'Flash it from the CompactFlash card like any OS update.' : 'Flash it like any OS update, with Elektron Transfer or your own SysEx tool.'} <a href={'#faq/' + RECOVERY_FAQ[machine]} target="_blank" rel="noreferrer">How to recover, in the FAQ ↗</a></p>
    <label className="risk-accept"><input type="checkbox" checked={checked} onChange={event => onChange(event.target.checked)} /><span>I know how to get my unit back to stock</span></label>
  </div>
}
