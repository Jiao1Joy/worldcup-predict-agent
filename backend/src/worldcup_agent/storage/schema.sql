CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  initial_state_json TEXT NOT NULL,
  current_state_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  run_id TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  event_json TEXT NOT NULL,
  PRIMARY KEY (run_id, sequence),
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS checkpoints (
  checkpoint_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  checkpoint_json TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
