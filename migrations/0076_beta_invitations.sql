-- A beta invitation is an explicit campaign action, independent of mail consent and staff roles.
ALTER TABLE news_campaigns ADD COLUMN beta_invitation INTEGER NOT NULL DEFAULT 0 CHECK(beta_invitation IN (0,1));
CREATE TABLE member_beta_invitations (
  -- 'public' is the separately enabled site invitation; other ids name a news campaign.
  campaign_id TEXT NOT NULL,
  user_id TEXT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
  state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','accepted','revoked')),
  risks_version TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  accepted_at TEXT,
  PRIMARY KEY(campaign_id,user_id)
);
CREATE INDEX member_beta_invitations_user ON member_beta_invitations(user_id);
CREATE TRIGGER delete_beta_campaign_invitations AFTER DELETE ON news_campaigns BEGIN
  DELETE FROM member_beta_invitations WHERE campaign_id=OLD.id;
END;
CREATE TABLE beta_invitation_settings (
  id INTEGER PRIMARY KEY CHECK(id=1),
  public_enabled INTEGER NOT NULL DEFAULT 0 CHECK(public_enabled IN (0,1))
);
INSERT INTO beta_invitation_settings(id) VALUES(1);
CREATE TABLE member_beta_discord_invites (
  user_id TEXT PRIMARY KEY REFERENCES auth_users(id) ON DELETE CASCADE,
  handled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Enforce the pool even when two different admission paths race or an operator writes directly.
CREATE TRIGGER beta_pool_update BEFORE UPDATE OF beta_tester ON users
WHEN NEW.beta_tester=1 AND OLD.beta_tester=0 AND (SELECT COUNT(*) FROM users WHERE beta_tester=1)>=50
BEGIN SELECT RAISE(ABORT,'The beta tester pool is full.'); END;
CREATE TRIGGER beta_pool_insert BEFORE INSERT ON users
WHEN NEW.beta_tester=1 AND (SELECT COUNT(*) FROM users WHERE beta_tester=1)>=50
BEGIN SELECT RAISE(ABORT,'The beta tester pool is full.'); END;
