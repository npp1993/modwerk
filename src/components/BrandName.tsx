import type { Session } from '../community/api'
import { hasBetaAccess } from '../community/beta-access'

export function BrandName({ session }: { session: Session }) {
  return <span className="brand-name">Modwerk{hasBetaAccess(session) && <span className="brand-beta-badge">Beta</span>}</span>
}
