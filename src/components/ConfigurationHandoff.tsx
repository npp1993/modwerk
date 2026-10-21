import { useSetWords } from '../community/beta-ui'
import { Icon } from './Icon'

/** JSON contains the configuration, never firmware; it can be imported on another device. */
export function ConfigurationHandoff({ onExport, exported, canExport = true }: { onExport: () => void; exported: boolean; canExport?: boolean }) {
  const w = useSetWords()
  return <section className="configuration-section" aria-label="Continue on a computer">
    <h2>Continue on a computer</h2>
    <p>Browse, edit and share your {w.set} here. To prepare firmware or install it, export the JSON and import it on a computer. It is saved in this browser; it does not sync between devices.</p>
    <button type="button" className="button button-quiet" disabled={!canExport} onClick={onExport}><Icon name="download" size={16} />Export {w.set} JSON</button>
    {exported && <p role="status">JSON export requested. Import the file on your computer to continue.</p>}
  </section>
}
