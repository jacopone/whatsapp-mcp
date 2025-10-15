import Database from 'better-sqlite3';
import { existsSync, mkdirSync } from 'fs';
import { join, dirname } from 'path';

const DATA_DIR = join(process.cwd(), 'data');
const DB_PATH = join(DATA_DIR, 'baileys_temp.db');

// Ensure data directory exists
if (!existsSync(DATA_DIR)) {
  mkdirSync(DATA_DIR, { recursive: true });
}

// Initialize database
const db: Database.Database = new Database(DB_PATH);

// Create tables
db.exec(`
  CREATE TABLE IF NOT EXISTS chats (
    jid TEXT PRIMARY KEY,
    name TEXT,
    last_message_time TEXT
  );

  CREATE TABLE IF NOT EXISTS messages (
    id TEXT NOT NULL,
    chat_jid TEXT NOT NULL,
    sender TEXT,
    content TEXT,
    timestamp TEXT,
    is_from_me INTEGER,
    PRIMARY KEY (id, chat_jid),
    FOREIGN KEY (chat_jid) REFERENCES chats(jid)
  );

  CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
  CREATE INDEX IF NOT EXISTS idx_messages_chat_jid ON messages(chat_jid);
  CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender);

  CREATE TABLE IF NOT EXISTS sync_status (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    is_syncing INTEGER DEFAULT 0,
    last_sync_time TEXT,
    messages_synced INTEGER DEFAULT 0,
    chats_synced INTEGER DEFAULT 0,
    progress_percent INTEGER DEFAULT 0,
    is_latest INTEGER DEFAULT 0
  );

  INSERT OR IGNORE INTO sync_status (id, is_syncing) VALUES (1, 0);
`);

export interface Chat {
  jid: string;
  name?: string;
  last_message_time?: Date;
}

export interface Message {
  id: string;
  chat_jid: string;
  sender?: string;
  content?: string;
  timestamp: Date;
  is_from_me: boolean;
}

export interface SyncStatus {
  is_syncing: boolean;
  last_sync_time?: Date;
  messages_synced: number;
  chats_synced: number;
  progress_percent: number;
  is_latest: boolean;
}

// Store chat
export function storeChat(chat: Chat): void {
  const stmt = db.prepare(`
    INSERT OR REPLACE INTO chats (jid, name, last_message_time)
    VALUES (?, ?, ?)
  `);

  stmt.run(
    chat.jid,
    chat.name || null,
    chat.last_message_time?.toISOString() || null
  );
}

// Store message
export function storeMessage(msg: Message): void {
  // Ensure chat exists first (for foreign key constraint)
  const chatStmt = db.prepare(`
    INSERT OR IGNORE INTO chats (jid, name, last_message_time)
    VALUES (?, ?, ?)
  `);
  chatStmt.run(msg.chat_jid, null, msg.timestamp.toISOString());

  // Now store the message
  const stmt = db.prepare(`
    INSERT OR REPLACE INTO messages (id, chat_jid, sender, content, timestamp, is_from_me)
    VALUES (?, ?, ?, ?, ?, ?)
  `);

  stmt.run(
    msg.id,
    msg.chat_jid,
    msg.sender || null,
    msg.content || null,
    msg.timestamp.toISOString(),
    msg.is_from_me ? 1 : 0
  );
}

// Update sync status
export function updateSyncStatus(status: Partial<SyncStatus>): void {
  const fields: string[] = [];
  const values: any[] = [];

  if (status.is_syncing !== undefined) {
    fields.push('is_syncing = ?');
    values.push(status.is_syncing ? 1 : 0);
  }
  if (status.last_sync_time !== undefined) {
    fields.push('last_sync_time = ?');
    values.push(status.last_sync_time.toISOString());
  }
  if (status.messages_synced !== undefined) {
    fields.push('messages_synced = ?');
    values.push(status.messages_synced);
  }
  if (status.chats_synced !== undefined) {
    fields.push('chats_synced = ?');
    values.push(status.chats_synced);
  }
  if (status.progress_percent !== undefined) {
    fields.push('progress_percent = ?');
    values.push(status.progress_percent);
  }
  if (status.is_latest !== undefined) {
    fields.push('is_latest = ?');
    values.push(status.is_latest ? 1 : 0);
  }

  if (fields.length > 0) {
    const stmt = db.prepare(`UPDATE sync_status SET ${fields.join(', ')} WHERE id = 1`);
    stmt.run(...values);
  }
}

// Get sync status
export function getSyncStatus(): SyncStatus {
  const stmt = db.prepare('SELECT * FROM sync_status WHERE id = 1');
  const row: any = stmt.get();

  return {
    is_syncing: row.is_syncing === 1,
    last_sync_time: row.last_sync_time ? new Date(row.last_sync_time) : undefined,
    messages_synced: row.messages_synced || 0,
    chats_synced: row.chats_synced || 0,
    progress_percent: row.progress_percent || 0,
    is_latest: row.is_latest === 1
  };
}

// Get all messages (for sync to Go DB)
export function getAllMessages(): Message[] {
  const stmt = db.prepare('SELECT * FROM messages ORDER BY timestamp ASC');
  const rows: any[] = stmt.all();

  return rows.map(row => ({
    id: row.id,
    chat_jid: row.chat_jid,
    sender: row.sender,
    content: row.content,
    timestamp: new Date(row.timestamp),
    is_from_me: row.is_from_me === 1
  }));
}

// Clear all data (after successful sync to Go)
export function clearAllData(): void {
  db.exec('DELETE FROM messages; DELETE FROM chats;');
  updateSyncStatus({
    is_syncing: false,
    messages_synced: 0,
    chats_synced: 0,
    progress_percent: 0,
    is_latest: false
  });
}

export default db;
