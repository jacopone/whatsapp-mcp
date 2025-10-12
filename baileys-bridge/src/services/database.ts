import Database from 'better-sqlite3';
import { existsSync, mkdirSync, chmodSync } from 'fs';
import { join } from 'path';
import pino, { Logger } from 'pino';

export interface DatabaseConfig {
  dataDir?: string;      // Directory for database file (default: data/)
  dbName?: string;       // Database filename (default: baileys_temp.db)
  logLevel?: string;     // Log level (default: info)
}

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

/**
 * DatabaseService provides SQLite database operations for Baileys bridge
 * This is a temporary database used only during history sync, then transferred to Go backend
 */
export class DatabaseService {
  private db: Database.Database;
  private logger: Logger;
  private dataDir: string;
  private dbPath: string;

  constructor(config: DatabaseConfig = {}) {
    // Set defaults
    this.dataDir = config.dataDir || join(process.cwd(), 'data');
    const dbName = config.dbName || 'baileys_temp.db';
    this.dbPath = join(this.dataDir, dbName);

    // Create logger
    this.logger = pino({ level: config.logLevel || 'info' });

    // Ensure data directory exists with secure permissions
    this.ensureDataDirectory();

    // Initialize database
    this.db = new Database(this.dbPath);

    // Set secure file permissions (600 - user read/write only)
    this.setDatabasePermissions();

    // Enable foreign keys
    this.db.pragma('foreign_keys = ON');

    // Create schema
    this.createSchema();

    this.logger.info(`Database initialized at ${this.dbPath}`);
  }

  /**
   * Ensure data directory exists with secure permissions (700)
   */
  private ensureDataDirectory(): void {
    if (!existsSync(this.dataDir)) {
      mkdirSync(this.dataDir, { recursive: true, mode: 0o700 });
      this.logger.info(`Created data directory: ${this.dataDir}`);
    }

    // Set permissions to 700 (user rwx only)
    try {
      chmodSync(this.dataDir, 0o700);
    } catch (error) {
      this.logger.warn({ error }, 'Failed to set data directory permissions');
    }
  }

  /**
   * Set database file permissions to 600 (user rw only)
   */
  private setDatabasePermissions(): void {
    try {
      if (existsSync(this.dbPath)) {
        chmodSync(this.dbPath, 0o600);
        this.logger.debug('Set database file permissions to 600');
      }
    } catch (error) {
      this.logger.warn({ error }, 'Failed to set database file permissions');
    }
  }

  /**
   * Create database schema for temporary Baileys storage
   */
  private createSchema(): void {
    this.db.exec(`
      -- Chats table (temporary storage during sync)
      CREATE TABLE IF NOT EXISTS chats (
        jid TEXT PRIMARY KEY,
        name TEXT,
        last_message_time TEXT
      );

      -- Messages table (temporary storage during sync)
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

      -- Indexes for performance
      CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
      CREATE INDEX IF NOT EXISTS idx_messages_chat_jid ON messages(chat_jid);
      CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender);

      -- Sync status tracking (singleton table)
      CREATE TABLE IF NOT EXISTS sync_status (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        is_syncing INTEGER DEFAULT 0,
        last_sync_time TEXT,
        messages_synced INTEGER DEFAULT 0,
        chats_synced INTEGER DEFAULT 0,
        progress_percent INTEGER DEFAULT 0,
        is_latest INTEGER DEFAULT 0
      );

      -- Initialize sync status row
      INSERT OR IGNORE INTO sync_status (id, is_syncing) VALUES (1, 0);
    `);
  }

  /**
   * Close the database connection
   */
  close(): void {
    if (this.db) {
      this.db.close();
      this.logger.info('Database connection closed');
    }
  }

  /**
   * Get the underlying better-sqlite3 database instance
   */
  getDB(): Database.Database {
    return this.db;
  }

  // === Chat Operations ===

  /**
   * Store or update a chat
   */
  storeChat(chat: Chat): void {
    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO chats (jid, name, last_message_time)
      VALUES (?, ?, ?)
    `);

    stmt.run(
      chat.jid,
      chat.name || null,
      chat.last_message_time?.toISOString() || null
    );
  }

  /**
   * Store multiple chats in a transaction
   */
  storeChatsInBatch(chats: Chat[]): void {
    const insert = this.db.prepare(`
      INSERT OR REPLACE INTO chats (jid, name, last_message_time)
      VALUES (?, ?, ?)
    `);

    const transaction = this.db.transaction((chats: Chat[]) => {
      for (const chat of chats) {
        insert.run(
          chat.jid,
          chat.name || null,
          chat.last_message_time?.toISOString() || null
        );
      }
    });

    transaction(chats);
  }

  /**
   * Get a chat by JID
   */
  getChat(jid: string): Chat | null {
    const stmt = this.db.prepare('SELECT * FROM chats WHERE jid = ?');
    const row: any = stmt.get(jid);

    if (!row) return null;

    return {
      jid: row.jid,
      name: row.name,
      last_message_time: row.last_message_time ? new Date(row.last_message_time) : undefined
    };
  }

  /**
   * Get all chats
   */
  getAllChats(): Chat[] {
    const stmt = this.db.prepare('SELECT * FROM chats ORDER BY last_message_time DESC');
    const rows: any[] = stmt.all();

    return rows.map(row => ({
      jid: row.jid,
      name: row.name,
      last_message_time: row.last_message_time ? new Date(row.last_message_time) : undefined
    }));
  }

  // === Message Operations ===

  /**
   * Store or update a message
   */
  storeMessage(msg: Message): void {
    const stmt = this.db.prepare(`
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

  /**
   * Store multiple messages in a transaction (much faster for bulk inserts)
   */
  storeMessagesInBatch(messages: Message[]): void {
    const insert = this.db.prepare(`
      INSERT OR REPLACE INTO messages (id, chat_jid, sender, content, timestamp, is_from_me)
      VALUES (?, ?, ?, ?, ?, ?)
    `);

    const transaction = this.db.transaction((messages: Message[]) => {
      for (const msg of messages) {
        insert.run(
          msg.id,
          msg.chat_jid,
          msg.sender || null,
          msg.content || null,
          msg.timestamp.toISOString(),
          msg.is_from_me ? 1 : 0
        );
      }
    });

    transaction(messages);
  }

  /**
   * Get messages for a specific chat
   */
  getMessagesByChatJID(chatJID: string, limit: number = 100): Message[] {
    const stmt = this.db.prepare(`
      SELECT * FROM messages
      WHERE chat_jid = ?
      ORDER BY timestamp DESC
      LIMIT ?
    `);
    const rows: any[] = stmt.all(chatJID, limit);

    return rows.map(row => ({
      id: row.id,
      chat_jid: row.chat_jid,
      sender: row.sender,
      content: row.content,
      timestamp: new Date(row.timestamp),
      is_from_me: row.is_from_me === 1
    }));
  }

  /**
   * Get all messages (for transferring to Go backend)
   */
  getAllMessages(): Message[] {
    const stmt = this.db.prepare('SELECT * FROM messages ORDER BY timestamp ASC');
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

  /**
   * Get message count
   */
  getMessageCount(): number {
    const stmt = this.db.prepare('SELECT COUNT(*) as count FROM messages');
    const result: any = stmt.get();
    return result.count || 0;
  }

  /**
   * Get chat count
   */
  getChatCount(): number {
    const stmt = this.db.prepare('SELECT COUNT(*) as count FROM chats');
    const result: any = stmt.get();
    return result.count || 0;
  }

  // === Sync Status Operations ===

  /**
   * Update sync status (partial updates supported)
   */
  updateSyncStatus(status: Partial<SyncStatus>): void {
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
      const stmt = this.db.prepare(`UPDATE sync_status SET ${fields.join(', ')} WHERE id = 1`);
      stmt.run(...values);
    }
  }

  /**
   * Get current sync status
   */
  getSyncStatus(): SyncStatus {
    const stmt = this.db.prepare('SELECT * FROM sync_status WHERE id = 1');
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

  // === Data Management ===

  /**
   * Clear all data (used after successful transfer to Go backend)
   */
  clearAllData(): void {
    this.db.exec('DELETE FROM messages; DELETE FROM chats;');
    this.updateSyncStatus({
      is_syncing: false,
      messages_synced: 0,
      chats_synced: 0,
      progress_percent: 0,
      is_latest: false
    });
    this.logger.info('Cleared all temporary data');
  }

  /**
   * Vacuum database to reclaim space after clearing data
   */
  vacuum(): void {
    this.db.exec('VACUUM');
    this.logger.info('Database vacuumed');
  }

  /**
   * Get database statistics
   */
  getStats(): {
    messages: number;
    chats: number;
    databaseSize: number;
    syncStatus: SyncStatus;
  } {
    const pageCount = this.db.pragma('page_count', { simple: true }) as number;
    const pageSize = this.db.pragma('page_size', { simple: true }) as number;

    return {
      messages: this.getMessageCount(),
      chats: this.getChatCount(),
      databaseSize: pageCount * pageSize,
      syncStatus: this.getSyncStatus()
    };
  }
}
