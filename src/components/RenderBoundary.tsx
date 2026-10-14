import { Component, type ReactNode } from 'react'

type Props = { children: ReactNode; fallback: ReactNode | ((error: unknown) => ReactNode); resetKey?: string }

/** Keep a failed view from unmounting its surrounding navigation and workspace. Key by route to reset, or pass a changing resetKey to reset without remounting the children. */
export class RenderBoundary extends Component<Props, { failed: boolean; error?: unknown }> {
  state: { failed: boolean; error?: unknown } = { failed: false }
  static getDerivedStateFromError(error: unknown) { return { failed: true, error } }
  componentDidUpdate(previous: Props) { if (this.state.failed && previous.resetKey !== this.props.resetKey) this.setState({ failed: false, error: undefined }) }
  render() {
    const { fallback } = this.props
    return this.state.failed ? typeof fallback === 'function' ? fallback(this.state.error) : fallback : this.props.children
  }
}
