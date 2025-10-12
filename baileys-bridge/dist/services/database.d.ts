import Database from 'better-sqlite3';
export interface DatabaseConfig {
    dataDir?: string;
    dbName?: string;
    logLevel?: string;
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
export declare class DatabaseService {
    private db;
    private logger;
    private dataDir;
    private dbPath;
    constructor(config?: DatabaseConfig);
    /**
     * Ensure data directory exists with secure permissions (700)
     */
    private ensureDataDirectory;
    /**
     * Set database file permissions to 600 (user rw only)
     */
    private setDatabasePermissions;
    /**
     * Create database schema for temporary Baileys storage
     */
    private createSchema;
    /**
     * Close the database connection
     */
    close(): void;
    /**
     * Get the underlying better-sqlite3 database instance
     */
    getDB(): Database.Database;
    /**
     * Store or update a chat
     */
    storeChat(chat: Chat): void;
    /**
     * Store multiple chats in a transaction
     */
    storeChatsInBatch(chats: Chat[]): void;
    /**
     * Get a chat by JID
     */
    getChat(jid: string): Chat | null;
    /**
     * Get all chats
     */
    getAllChats(): Chat[];
    /**
     * Store or update a message
     */
    storeMessage(msg: Message): void;
    /**
     * Store multiple messages in a transaction (much faster for bulk inserts)
     */
    storeMessagesInBatch(messages: Message[]): void;
    /**
     * Get messages for a specific chat
     */
    getMessagesByChatJID(chatJID: string, limit?: number): Message[];
    /**
     * Get all messages (for transferring to Go backend)
     */
    getAllMessages(): Message[];
    /**
     * Get message count
     */
    getMessageCount(): number;
    /**
     * Get chat count
     */
    getChatCount(): number;
    /**
     * Update sync status (partial updates supported)
     */
    updateSyncStatus(status: Partial<SyncStatus>): void;
    /**
     * Get current sync status
     */
    getSyncStatus(): SyncStatus;
    /**
     * Clear all data (used after successful transfer to Go backend)
     */
    clearAllData(): void;
    /**
     * Vacuum database to reclaim space after clearing data
     */
    vacuum(): void;
    /**
     * Get database statistics
     */
    getStats(): {
        messages: number;
        chats: number;
        databaseSize: number;
        syncStatus: SyncStatus;
    };
}
//# sourceMappingURL=database.d.ts.map