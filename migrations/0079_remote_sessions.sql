-- Remote debug sessions (server/remote-sessions.ts): an administrator asks a member, the member accepts in a dialog,
-- and their browser relays read-only USB requests to their Octatrack for a limited time. The record says who asked,
-- why, when it ran and how it ended, with request counts; the bytes read are never stored.
CREATE TABLE remote_sessions (
 id TEXT PRIMARY KEY,
 member_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 requested_by TEXT NOT NULL,
 requester_name TEXT NOT NULL,
 reason TEXT NOT NULL,
 scope TEXT NOT NULL CHECK(scope IN ('read')),
 minutes INTEGER NOT NULL CHECK(minutes BETWEEN 5 AND 60),
 status TEXT NOT NULL CHECK(status IN ('pending','declined','active','ended','expired')),
 consent_version TEXT,
 created_at TEXT NOT NULL,
 expires_at TEXT NOT NULL,
 answered_at TEXT,
 ends_at TEXT,
 ended_at TEXT,
 ended_by TEXT CHECK(ended_by IN ('member','operator','time')),
 summary_json TEXT
);
CREATE INDEX remote_sessions_member ON remote_sessions(member_id,status);
-- One-time tickets that open a session's WebSocket: browsers cannot send a bearer token on a WebSocket.
CREATE TABLE remote_session_tickets (
 token_hash TEXT PRIMARY KEY,
 session_id TEXT NOT NULL REFERENCES remote_sessions(id) ON DELETE CASCADE,
 side TEXT NOT NULL CHECK(side IN ('member','operator')),
 expires INTEGER NOT NULL
);
