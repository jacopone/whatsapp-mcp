import Database from 'better-sqlite3';
declare const db: Database.Database;
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
export declare function storeChat(chat: Chat): void;
export declare function storeMessage(msg: Message): void;
export declare function updateSyncStatus(status: Partial<SyncStatus>): void;
export declare function getSyncStatus(): SyncStatus;
export declare function getAllMessages(): Message[];
export declare function clearAllData(): void;
export default db;
//# sourceMappingURL=database.d.ts.map