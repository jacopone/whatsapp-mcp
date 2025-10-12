/**
 * History Sync Routes
 *
 * Endpoints for fetching full conversation history from WhatsApp using Baileys.
 * Implements checkpoint-based resumable sync with progress tracking.
 */
import { Router } from 'express';
import { BaileysClient } from '../services/baileys_client.js';
import { DatabaseService } from '../services/database.js';
export interface HistorySyncRequest {
    chat_jid: string;
    resume?: boolean;
    max_messages?: number;
}
export interface HistorySyncResponse {
    sync_id: string;
    checkpoint: Record<string, any>;
    status: string;
}
export interface HistorySyncConfig {
    baileysClient: BaileysClient;
    database: DatabaseService;
    logLevel?: string;
}
/**
 * Create history sync router
 */
export declare function createHistoryRouter(config: HistorySyncConfig): Router;
//# sourceMappingURL=history.d.ts.map