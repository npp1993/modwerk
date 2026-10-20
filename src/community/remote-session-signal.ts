// SPDX-License-Identifier: GPL-3.0-or-later OR Elastic-2.0
// Copyright (c) 2026 Jannik Aßfalg (repeat98)
// Whether a remote debug request is waiting for this member. The bell's minute poll carries it (server/notifications.ts),
// so the session dialog and its USB code load only for a member who has one.
import { useSyncExternalStore } from 'react'

let due = false, seen = false
const listeners = new Set<() => void>()
export function noteRemoteSessionDue(value: boolean | undefined) {
  if (!!value === due) return
  due = !!value; seen ||= due
  for (const listener of listeners) listener()
}
const subscribe = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
/** True from the first request of this visit on, so a running session's banner stays mounted after the flag clears. */
export function useRemoteSessionSeen() { return useSyncExternalStore(subscribe, () => seen, () => false) }
/** True while the server reports a waiting request or a running session. */
export function useRemoteSessionDue() { return useSyncExternalStore(subscribe, () => due, () => false) }
