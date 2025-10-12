/**
 * History Sync Routes
 *
 * Endpoints for fetching full conversation history from WhatsApp using Baileys.
 * Implements checkpoint-based resumable sync with progress tracking.
 */
import { Router } from 'express';
import { SyncCheckpoint, SyncStatus } from '../models/sync_checkpoint.js';
import pino from 'pino';
/**
 * Create history sync router
 */
export function createHistoryRouter(config) {
    const router = Router();
    const logger = pino({ level: config.logLevel || 'info' });
    const { baileysClient, database } = config;
    // In-memory tracking of active syncs
    const activeSyncs = new Map();
    /**
     * POST /history/sync
     * Start or resume history sync for a chat
     */
    router.post('/sync', async (req, res) => {
        try {
            const { chat_jid, resume = false, max_messages = 1000 } = req.body;
            // Validation
            if (!chat_jid || !chat_jid.includes('@')) {
                return res.status(400).json({
                    error: 'Invalid chat_jid. Must be a valid WhatsApp JID (e.g., 1234567890@s.whatsapp.net)'
                });
            }
            if (max_messages < 1 || max_messages > 10000) {
                return res.status(400).json({
                    error: 'max_messages must be between 1 and 10000'
                });
            }
            // Check if WhatsApp is connected
            if (!baileysClient.getConnectionState()) {
                return res.status(503).json({
                    error: 'WhatsApp is not connected. Please connect first.',
                    status: 'disconnected'
                });
            }
            // Load or create checkpoint
            let checkpoint;
            const existingCheckpoint = database.getSyncStatus();
            if (resume && existingCheckpoint.is_syncing) {
                // Resume from existing checkpoint
                checkpoint = new SyncCheckpoint({
                    chat_jid,
                    last_message_id: existingCheckpoint.last_sync_time ? 'placeholder' : null,
                    last_timestamp: existingCheckpoint.last_sync_time
                        ? new Date(existingCheckpoint.last_sync_time).getTime()
                        : null,
                    messages_synced: existingCheckpoint.messages_synced,
                    status: SyncStatus.IN_PROGRESS
                });
                logger.info(`Resuming sync for ${chat_jid}, ${checkpoint.messages_synced} already synced`);
            }
            else {
                // Create new checkpoint
                checkpoint = SyncCheckpoint.create(chat_jid);
                checkpoint.start();
                logger.info(`Starting new sync for ${chat_jid}`);
            }
            // Track active sync
            activeSyncs.set(chat_jid, checkpoint);
            // Start sync in background
            syncHistory(chat_jid, checkpoint, max_messages, baileysClient, database, logger, activeSyncs).catch((error) => {
                logger.error({ error, chat_jid }, 'Background sync failed');
                checkpoint.fail(error.message);
                activeSyncs.delete(chat_jid);
            });
            // Return immediate response
            const response = {
                sync_id: chat_jid, // Use chat_jid as sync_id for simplicity
                checkpoint: checkpoint.toJSON(),
                status: 'started'
            };
            res.status(202).json(response);
        }
        catch (error) {
            logger.error({ error }, 'Error starting history sync');
            res.status(500).json({
                error: 'Failed to start history sync',
                message: String(error)
            });
        }
    });
    /**
     * GET /history/sync/:chat_jid/status
     * Get current checkpoint status for a chat
     */
    router.get('/sync/:chat_jid/status', async (req, res) => {
        try {
            const { chat_jid } = req.params;
            // Check active sync first
            const activeCheckpoint = activeSyncs.get(chat_jid);
            if (activeCheckpoint) {
                return res.status(200).json({
                    checkpoint: activeCheckpoint.toJSON(),
                    is_active: activeCheckpoint.isActive()
                });
            }
            // Otherwise, check database
            const syncStatus = database.getSyncStatus();
            res.status(200).json({
                checkpoint: {
                    chat_jid,
                    messages_synced: syncStatus.messages_synced,
                    status: syncStatus.is_syncing ? 'in_progress' : 'not_started',
                    last_sync_time: syncStatus.last_sync_time,
                    progress_percent: syncStatus.progress_percent
                },
                is_active: syncStatus.is_syncing
            });
        }
        catch (error) {
            logger.error({ error }, 'Error getting sync status');
            res.status(500).json({
                error: 'Failed to get sync status',
                message: String(error)
            });
        }
    });
    /**
     * POST /history/sync/:chat_jid/cancel
     * Cancel ongoing sync for a chat
     */
    router.post('/sync/:chat_jid/cancel', async (req, res) => {
        try {
            const { chat_jid } = req.params;
            const checkpoint = activeSyncs.get(chat_jid);
            if (!checkpoint) {
                return res.status(404).json({
                    error: 'No active sync found for this chat'
                });
            }
            if (!checkpoint.isActive()) {
                return res.status(400).json({
                    error: `Cannot cancel sync with status: ${checkpoint.status}`
                });
            }
            checkpoint.cancel();
            activeSyncs.delete(chat_jid);
            logger.info({ chat_jid }, 'Sync cancelled by user');
            res.status(200).json({
                message: 'Sync cancelled successfully',
                checkpoint: checkpoint.toJSON()
            });
        }
        catch (error) {
            logger.error({ error }, 'Error cancelling sync');
            res.status(500).json({
                error: 'Failed to cancel sync',
                message: String(error)
            });
        }
    });
    /**
     * POST /history/sync/:chat_jid/resume
     * Resume interrupted/failed sync
     */
    router.post('/sync/:chat_jid/resume', async (req, res) => {
        try {
            const { chat_jid } = req.params;
            const { max_messages = 1000 } = req.body;
            // Check if there's an active sync
            if (activeSyncs.has(chat_jid)) {
                return res.status(409).json({
                    error: 'Sync is already active for this chat'
                });
            }
            // Get sync status from database
            const syncStatus = database.getSyncStatus();
            // Create checkpoint from database state
            const checkpoint = new SyncCheckpoint({
                chat_jid,
                messages_synced: syncStatus.messages_synced,
                status: SyncStatus.INTERRUPTED
            });
            // Attempt resume
            try {
                checkpoint.resume();
            }
            catch (error) {
                return res.status(400).json({
                    error: 'Cannot resume sync',
                    message: String(error)
                });
            }
            // Track active sync
            activeSyncs.set(chat_jid, checkpoint);
            // Start sync in background
            syncHistory(chat_jid, checkpoint, max_messages, baileysClient, database, logger, activeSyncs).catch((error) => {
                logger.error({ error, chat_jid }, 'Background sync failed on resume');
                checkpoint.fail(error.message);
                activeSyncs.delete(chat_jid);
            });
            res.status(202).json({
                message: 'Sync resumed successfully',
                checkpoint: checkpoint.toJSON()
            });
        }
        catch (error) {
            logger.error({ error }, 'Error resuming sync');
            res.status(500).json({
                error: 'Failed to resume sync',
                message: String(error)
            });
        }
    });
    /**
     * GET /history/messages
     * Query messages from temp database
     */
    router.get('/messages', async (req, res) => {
        try {
            const { chat_jid, limit = 100 } = req.query;
            if (!chat_jid) {
                return res.status(400).json({
                    error: 'chat_jid query parameter is required'
                });
            }
            const limitNum = Math.min(parseInt(limit) || 100, 1000);
            const messages = database.getMessagesByChatJID(chat_jid, limitNum);
            res.status(200).json({
                chat_jid,
                count: messages.length,
                messages: messages.map(msg => ({
                    id: msg.id,
                    chat_jid: msg.chat_jid,
                    sender: msg.sender,
                    content: msg.content,
                    timestamp: msg.timestamp.toISOString(),
                    is_from_me: msg.is_from_me
                }))
            });
        }
        catch (error) {
            logger.error({ error }, 'Error querying messages');
            res.status(500).json({
                error: 'Failed to query messages',
                message: String(error)
            });
        }
    });
    return router;
}
/**
 * Background sync function
 * Fetches messages with checkpointing
 */
async function syncHistory(chatJid, checkpoint, maxMessages, baileysClient, database, logger, activeSyncs) {
    const BATCH_SIZE = 100;
    const CHECKPOINT_INTERVAL = 100;
    try {
        logger.info({ chatJid, maxMessages }, 'Starting history sync');
        // Update sync status
        database.updateSyncStatus({
            is_syncing: true,
            messages_synced: checkpoint.messages_synced,
            progress_percent: 0
        });
        const sock = baileysClient.getSocket();
        if (!sock) {
            throw new Error('WhatsApp socket not available');
        }
        let messagesFetched = 0;
        let cursor = checkpoint.last_message_id || undefined;
        while (messagesFetched < maxMessages && checkpoint.isActive()) {
            try {
                // Fetch batch of messages
                const batch = await fetchMessageBatch(sock, chatJid, BATCH_SIZE, cursor, logger);
                if (batch.messages.length === 0) {
                    logger.info('No more messages to fetch');
                    break;
                }
                // Store messages in temp database
                database.storeMessagesInBatch(batch.messages);
                // Update progress
                messagesFetched += batch.messages.length;
                cursor = batch.cursor;
                const lastMessage = batch.messages[batch.messages.length - 1];
                checkpoint.updateProgress(lastMessage.id, lastMessage.timestamp.getTime(), batch.messages.length);
                // Save checkpoint every CHECKPOINT_INTERVAL messages
                if (checkpoint.messages_synced % CHECKPOINT_INTERVAL === 0) {
                    database.updateSyncStatus({
                        messages_synced: checkpoint.messages_synced,
                        progress_percent: Math.floor((messagesFetched / maxMessages) * 100),
                        last_sync_time: new Date()
                    });
                    logger.info({ messages_synced: checkpoint.messages_synced, progress: `${Math.floor((messagesFetched / maxMessages) * 100)}%` }, 'Checkpoint saved');
                }
                // Small delay to avoid rate limiting
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            catch (error) {
                logger.warn({ error }, 'Error fetching batch, will retry');
                // Network error - mark as interrupted
                checkpoint.interrupt(`Network error: ${error}`);
                database.updateSyncStatus({
                    is_syncing: false,
                    messages_synced: checkpoint.messages_synced
                });
                throw error;
            }
        }
        // Sync completed
        checkpoint.complete();
        database.updateSyncStatus({
            is_syncing: false,
            messages_synced: checkpoint.messages_synced,
            progress_percent: 100,
            is_latest: true,
            last_sync_time: new Date()
        });
        logger.info({ chat_jid: chatJid, total_messages: checkpoint.messages_synced }, 'History sync completed');
    }
    catch (error) {
        logger.error({ error, chat_jid: chatJid }, 'History sync failed');
        // Mark as failed
        checkpoint.fail(String(error));
        database.updateSyncStatus({
            is_syncing: false,
            messages_synced: checkpoint.messages_synced
        });
    }
    finally {
        activeSyncs.delete(chatJid);
    }
}
/**
 * Fetch a batch of messages from Baileys
 *
 * Note: Baileys' message history sync works through events, not direct fetching.
 * In production, this would:
 * 1. Listen to 'messaging-history.set' events (when syncFullHistory is enabled)
 * 2. Or query from Baileys' message store if using store
 * 3. For now, we use a simplified approach with loadMessagesFromWA if available
 */
async function fetchMessageBatch(sock, chatJid, count, cursor, logger) {
    try {
        // Baileys provides messages through message store or history events
        // For explicit fetching, we need to use the chat's message history
        // This is a placeholder implementation
        // In production, you would:
        // 1. Use sock's message store to query messages
        // 2. Or rely on the syncFullHistory events
        // 3. Or implement a custom message fetching strategy
        logger.warn('Message fetching is placeholder - implement based on Baileys store');
        // Return empty batch for now (to be implemented with actual Baileys integration)
        // The actual implementation depends on how you set up Baileys' message store
        return { messages: [], cursor: undefined };
        // Example of what the implementation might look like:
        // const store = getMessageStore();  // Your message store implementation
        // const messages = await store.loadMessages(chatJid, count, cursor);
        // return { messages: convertMessages(messages), cursor: getNextCursor(messages) };
    }
    catch (error) {
        logger.error({ error, chat_jid: chatJid }, 'Error fetching messages');
        throw error;
    }
}
//# sourceMappingURL=history.js.map