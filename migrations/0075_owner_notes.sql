-- Jannik's one-time notes, remembered per verified account on every browser and device.
CREATE TABLE member_owner_notes (
 user_id TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
 note TEXT NOT NULL,
 seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY (user_id, note)
);
