/**
 * History Sync Routes
 *
 * Endpoints for fetching full conversation history from WhatsApp using Baileys.
 * Implements checkpoint-based resumable sync with progress tracking.
 */

import { Router, Request, Response } from 'express';
import { WASocket, downloadMediaMessage, proto } from '@whiskeysockets/baileys';
import Long from 'long';
import { BaileysClient } from '../services/baileys_client.js';
import { DatabaseService } from '../services/database.js';
import { SyncCheckpoint, SyncStatus } from '../models/sync_checkpoint.js';
import pino, { Logger } from 'pino';

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
export function createHistoryRouter(config: HistorySyncConfig): Router {
  const router = Router();
  const logger = pino({ level: config.logLevel || 'info' });
  const { baileysClient, database } = config;

  // In-memory tracking of active syncs
  const activeSyncs = new Map<string, SyncCheckpoint>();

  /**
   * POST /history/sync
   * Start or resume history sync for a chat
   */
  router.post('/sync', async (req: Request, res: Response) => {
    try {
      const { chat_jid, resume = false, max_messages = 1000 } = req.body as HistorySyncRequest;

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
      let checkpoint: SyncCheckpoint;
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
      } else {
        // Create new checkpoint
        checkpoint = SyncCheckpoint.create(chat_jid);
        checkpoint.start();
        logger.info(`Starting new sync for ${chat_jid}`);
      }

      // Track active sync
      activeSyncs.set(chat_jid, checkpoint);

      // Start sync in background
      syncHistory(
        chat_jid,
        checkpoint,
        max_messages,
        baileysClient,
        database,
        logger,
        activeSyncs
      ).catch((error) => {
        logger.error({ error, chat_jid }, 'Background sync failed');
        checkpoint.fail(error.message);
        activeSyncs.delete(chat_jid);
      });

      // Return immediate response
      const response: HistorySyncResponse = {
        sync_id: chat_jid,  // Use chat_jid as sync_id for simplicity
        checkpoint: checkpoint.toJSON(),
        status: 'started'
      };

      res.status(202).json(response);
    } catch (error) {
      logger.error({ error }, 'Error starting history sync');
      res.status(500).json({
        error: 'Failed to start history sync',
        message: String(error)
      });
    }
  });

  /**
   * GET /history/sync/:chat_jid/status
   * Get current checkpoint status for a chat with enhanced metrics
   */
  router.get('/sync/:chat_jid/status', async (req: Request, res: Response) => {
    try {
      const { chat_jid } = req.params;

      // Check active sync first
      const activeCheckpoint = activeSyncs.get(chat_jid);
      if (activeCheckpoint) {
        const checkpointData = activeCheckpoint.toJSON();

        // Calculate additional metrics for active syncs
        const oldestMessage = database.getOldestMessage(chat_jid);
        const messagesCount = database.getMessageCount();

        // Estimate completion time based on sync rate
        let estimatedCompletionTime = null;
        let messagesPerSecond = null;

        if (checkpointData.created_at && checkpointData.messages_synced > 0) {
          const elapsedMs = Date.now() - new Date(checkpointData.created_at).getTime();
          messagesPerSecond = checkpointData.messages_synced / (elapsedMs / 1000);

          if (checkpointData.progress_percent && checkpointData.progress_percent > 0) {
            const totalMessages = checkpointData.messages_synced / (checkpointData.progress_percent / 100);
            const remainingMessages = totalMessages - checkpointData.messages_synced;
            const remainingSeconds = remainingMessages / messagesPerSecond;
            estimatedCompletionTime = new Date(Date.now() + remainingSeconds * 1000).toISOString();
          }
        }

        return res.status(200).json({
          checkpoint: checkpointData,
          is_active: activeCheckpoint.isActive(),
          oldest_message_date: oldestMessage?.timestamp?.toISOString() || null,
          messages_per_second: messagesPerSecond ? messagesPerSecond.toFixed(2) : null,
          estimated_completion_time: estimatedCompletionTime,
          error_details: checkpointData.status === 'failed' || checkpointData.status === 'interrupted'
            ? { error_message: checkpointData.error_message }
            : null
        });
      }

      // Otherwise, check database
      const syncStatus = database.getSyncStatus();
      const oldestMessage = database.getOldestMessage(chat_jid);

      res.status(200).json({
        checkpoint: {
          chat_jid,
          messages_synced: syncStatus.messages_synced,
          status: syncStatus.is_syncing ? 'in_progress' : 'not_started',
          last_sync_time: syncStatus.last_sync_time,
          progress_percent: syncStatus.progress_percent
        },
        is_active: syncStatus.is_syncing,
        oldest_message_date: oldestMessage?.timestamp?.toISOString() || null,
        messages_per_second: null,
        estimated_completion_time: null,
        error_details: null
      });
    } catch (error) {
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
  router.post('/sync/:chat_jid/cancel', async (req: Request, res: Response) => {
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
    } catch (error) {
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
  router.post('/sync/:chat_jid/resume', async (req: Request, res: Response) => {
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
      } catch (error) {
        return res.status(400).json({
          error: 'Cannot resume sync',
          message: String(error)
        });
      }

      // Track active sync
      activeSyncs.set(chat_jid, checkpoint);

      // Start sync in background
      syncHistory(
        chat_jid,
        checkpoint,
        max_messages,
        baileysClient,
        database,
        logger,
        activeSyncs
      ).catch((error) => {
        logger.error({ error, chat_jid }, 'Background sync failed on resume');
        checkpoint.fail(error.message);
        activeSyncs.delete(chat_jid);
      });

      res.status(202).json({
        message: 'Sync resumed successfully',
        checkpoint: checkpoint.toJSON()
      });
    } catch (error) {
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
  router.get('/messages', async (req: Request, res: Response) => {
    try {
      const { chat_jid, limit = 100 } = req.query;

      if (!chat_jid) {
        return res.status(400).json({
          error: 'chat_jid query parameter is required'
        });
      }

      const limitNum = Math.min(parseInt(limit as string) || 100, 1000);
      const messages = database.getMessagesByChatJID(chat_jid as string, limitNum);

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
    } catch (error) {
      logger.error({ error }, 'Error querying messages');
      res.status(500).json({
        error: 'Failed to query messages',
        message: String(error)
      });
    }
  });

  /**
   * POST /history/sync/bulk
   * Start history sync for multiple chats
   */
  router.post('/sync/bulk', async (req: Request, res: Response) => {
    try {
      const { chat_jids, max_messages = 1000 } = req.body;

      // Validation
      if (!Array.isArray(chat_jids) || chat_jids.length === 0) {
        return res.status(400).json({
          error: 'chat_jids must be a non-empty array'
        });
      }

      if (chat_jids.length > 50) {
        return res.status(400).json({
          error: 'Maximum 50 chat_jids allowed per bulk request'
        });
      }

      // Validate JID format
      const invalidJids = chat_jids.filter((jid: string) => !jid || !jid.includes('@'));
      if (invalidJids.length > 0) {
        return res.status(400).json({
          error: 'Invalid JID format detected',
          invalid_jids: invalidJids
        });
      }

      // Check WhatsApp connection
      if (!baileysClient.getConnectionState()) {
        return res.status(503).json({
          error: 'WhatsApp is not connected. Please connect first.',
          status: 'disconnected'
        });
      }

      // Queue all sync requests
      const queuedSyncs: string[] = [];
      const failedSyncs: { chat_jid: string; error: string }[] = [];

      for (const chat_jid of chat_jids) {
        try {
          // Check if sync already active
          if (activeSyncs.has(chat_jid)) {
            logger.warn({ chat_jid }, 'Sync already active, skipping');
            continue;
          }

          // Create checkpoint
          const checkpoint = SyncCheckpoint.create(chat_jid);
          checkpoint.start();

          // Track active sync
          activeSyncs.set(chat_jid, checkpoint);
          queuedSyncs.push(chat_jid);

          // Start sync in background (syncs run sequentially due to rate limiting)
          syncHistory(
            chat_jid,
            checkpoint,
            max_messages,
            baileysClient,
            database,
            logger,
            activeSyncs
          ).catch((error) => {
            logger.error({ error, chat_jid }, 'Background sync failed in bulk operation');
            checkpoint.fail(error.message);
            activeSyncs.delete(chat_jid);
          });

        } catch (error) {
          failedSyncs.push({
            chat_jid,
            error: String(error)
          });
        }
      }

      logger.info({
        queued: queuedSyncs.length,
        failed: failedSyncs.length,
        total: chat_jids.length
      }, 'Bulk sync initiated');

      res.status(202).json({
        queued: queuedSyncs.length,
        sync_ids: queuedSyncs,
        failed: failedSyncs,
        message: `Queued ${queuedSyncs.length} of ${chat_jids.length} chats for sync`
      });

    } catch (error) {
      logger.error({ error }, 'Error initiating bulk sync');
      res.status(500).json({
        error: 'Failed to initiate bulk sync',
        message: String(error)
      });
    }
  });

  /**
   * GET /history/sync/bulk/status
   * Get status for multiple sync operations
   */
  router.get('/sync/bulk/status', async (req: Request, res: Response) => {
    try {
      const { sync_ids } = req.query;

      if (!sync_ids) {
        return res.status(400).json({
          error: 'sync_ids query parameter required (comma-separated chat_jids)'
        });
      }

      // Parse sync_ids (can be array or comma-separated string)
      const syncIdArray = Array.isArray(sync_ids)
        ? sync_ids
        : String(sync_ids).split(',');

      const checkpoints: any[] = [];
      let completedCount = 0;
      let inProgressCount = 0;
      let failedCount = 0;
      let totalMessages = 0;

      for (const sync_id of syncIdArray) {
        const chat_jid = String(sync_id).trim();

        // Check active sync first
        const activeCheckpoint = activeSyncs.get(chat_jid);
        if (activeCheckpoint) {
          const checkpointData = activeCheckpoint.toJSON();
          checkpoints.push(checkpointData);

          if (checkpointData.status === 'completed') completedCount++;
          else if (checkpointData.status === 'in_progress') inProgressCount++;
          else if (checkpointData.status === 'failed') failedCount++;

          totalMessages += checkpointData.messages_synced || 0;
        } else {
          // Check database (fallback for completed/old syncs)
          const syncStatus = database.getSyncStatus();
          const checkpointData = {
            chat_jid,
            messages_synced: syncStatus.messages_synced,
            status: syncStatus.is_syncing ? 'in_progress' : 'completed',
            last_sync_time: syncStatus.last_sync_time,
            progress_percent: syncStatus.progress_percent
          };
          checkpoints.push(checkpointData);

          if (checkpointData.status === 'completed') completedCount++;
        }
      }

      const total = syncIdArray.length;
      const overallProgress = total > 0 ? Math.floor((completedCount / total) * 100) : 0;

      res.status(200).json({
        total,
        completed: completedCount,
        in_progress: inProgressCount,
        failed: failedCount,
        progress_percent: overallProgress,
        total_messages_synced: totalMessages,
        checkpoints
      });

    } catch (error) {
      logger.error({ error }, 'Error getting bulk sync status');
      res.status(500).json({
        error: 'Failed to get bulk sync status',
        message: String(error)
      });
    }
  });

  return router;
}

/**
 * Normalize timestamp from various formats to Unix seconds
 * Handles Long type from protobuf, Date objects, and plain numbers
 */
function normalizeTimestamp(ts: Date | number | Long): number {
  if (ts instanceof Date) {
    return Math.floor(ts.getTime() / 1000);
  }
  if (Long.isLong(ts)) {
    return ts.toNumber();
  }
  return ts;
}

/**
 * Extract text content from WhatsApp message protobuf
 * Handles various message types (text, media with captions, etc.)
 */
function extractMessageContent(msg: proto.IWebMessageInfo): string {
  const message = msg.message;
  if (!message) return '';

  // Text messages
  if (message.conversation) return message.conversation;
  if (message.extendedTextMessage?.text) return message.extendedTextMessage.text;

  // Media with captions
  if (message.imageMessage?.caption) return `[Image: ${message.imageMessage.caption}]`;
  if (message.videoMessage?.caption) return `[Video: ${message.videoMessage.caption}]`;
  if (message.documentMessage?.caption) return `[Document: ${message.documentMessage.caption}]`;
  if (message.audioMessage) return '[Audio message]';

  // Other message types
  if (message.stickerMessage) return '[Sticker]';
  if (message.contactMessage) return '[Contact card]';
  if (message.locationMessage) return '[Location]';

  return '[Non-text message]';
}

/**
 * Wait for messaging-history.set event with ON_DEMAND syncType
 * Returns messages and cursor for pagination
 */
function waitForHistoryMessages(
  sock: WASocket,
  timeoutMs: number,
  logger: Logger
): Promise<{ messages: proto.IWebMessageInfo[]; cursor: string | undefined }> {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      sock.ev.off('messaging-history.set', handler);
      reject(new Error(`Timeout waiting for message history (${timeoutMs}ms)`));
    }, timeoutMs);

    const handler = ({ messages, syncType }: any) => {
      // Only process ON_DEMAND sync events (not INITIAL, PUSH_NAME, etc.)
      if (syncType === proto.HistorySync.HistorySyncType.ON_DEMAND) {
        clearTimeout(timeout);
        sock.ev.off('messaging-history.set', handler);

        logger.debug({ messageCount: messages.length }, 'Received ON_DEMAND history messages');

        // Extract cursor from oldest message in batch
        const cursor = messages.length > 0
          ? messages[messages.length - 1].key?.id
          : undefined;

        resolve({ messages, cursor });
      }
      // Ignore other sync types, keep waiting
    };

    sock.ev.on('messaging-history.set', handler);
  });
}

/**
 * Background sync function
 * Fetches messages with checkpointing
 */
/**
 * Classify error type for better handling
 */
function classifyError(error: any): string {
  const errorStr = String(error).toLowerCase();

  if (errorStr.includes('timeout')) {
    return 'TIMEOUT: WhatsApp did not respond within expected time';
  }
  if (errorStr.includes('rate limit') || errorStr.includes('too many requests')) {
    return 'RATE_LIMIT: Too many requests, backing off';
  }
  if (errorStr.includes('socket') || errorStr.includes('not available') || errorStr.includes('connection')) {
    return 'DISCONNECTED: WhatsApp socket not available';
  }
  if (errorStr.includes('invalid') || errorStr.includes('not found')) {
    return 'INVALID_KEY: Message reference not found';
  }

  return `UNKNOWN: ${errorStr}`;
}

async function syncHistory(
  chatJid: string,
  checkpoint: SyncCheckpoint,
  maxMessages: number,
  baileysClient: BaileysClient,
  database: DatabaseService,
  logger: Logger,
  activeSyncs: Map<string, SyncCheckpoint>
): Promise<void> {
  const BATCH_SIZE = 100;
  const CHECKPOINT_INTERVAL = 100;
  const RATE_LIMIT_DELAY_MS = 3000;
  const MAX_RETRIES = 3;

  const startTime = Date.now();

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
      throw new Error('DISCONNECTED: WhatsApp socket not available');
    }

    let messagesFetched = 0;
    let cursor: string | undefined = checkpoint.last_message_id || undefined;
    let retryCount = 0;

    while (messagesFetched < maxMessages && checkpoint.isActive()) {
      try {
        // Fetch batch of messages
        const batch = await fetchMessageBatch(
          sock,
          chatJid,
          BATCH_SIZE,
          cursor,
          logger,
          database
        );

        if (batch.messages.length === 0) {
          logger.info('No more messages to fetch');
          break;
        }

        // Reset retry count on success
        retryCount = 0;

        // Store messages in temp database
        database.storeMessagesInBatch(batch.messages);

        // Update progress
        messagesFetched += batch.messages.length;
        cursor = batch.cursor;

        const lastMessage = batch.messages[batch.messages.length - 1];
        checkpoint.updateProgress(
          lastMessage.id,
          lastMessage.timestamp.getTime(),
          batch.messages.length
        );

        // Calculate and log progress milestones
        const progressPercent = Math.floor((messagesFetched / maxMessages) * 100);
        const elapsedMs = Date.now() - startTime;
        const messagesPerSecond = messagesFetched / (elapsedMs / 1000);
        const remainingMessages = maxMessages - messagesFetched;
        const estimatedCompletionMs = remainingMessages / messagesPerSecond * 1000;

        // Save checkpoint every CHECKPOINT_INTERVAL messages
        if (checkpoint.messages_synced % CHECKPOINT_INTERVAL === 0) {
          database.updateSyncStatus({
            messages_synced: checkpoint.messages_synced,
            progress_percent: progressPercent,
            last_sync_time: new Date()
          });

          logger.info({
            messages_synced: checkpoint.messages_synced,
            progress_percent: progressPercent,
            messages_per_second: messagesPerSecond.toFixed(2),
            estimated_completion_minutes: (estimatedCompletionMs / 60000).toFixed(1)
          }, 'Checkpoint saved');

          // Log progress milestones
          if (progressPercent === 25 || progressPercent === 50 || progressPercent === 75) {
            logger.info({ progress_percent: progressPercent }, `Sync ${progressPercent}% complete`);
          }
        }

        // Rate limiting: 3-second delay between batches to avoid WhatsApp throttling
        await new Promise(resolve => setTimeout(resolve, RATE_LIMIT_DELAY_MS));

      } catch (error) {
        const classifiedError = classifyError(error);
        logger.warn({
          error: classifiedError,
          retry_count: retryCount,
          chat_jid: chatJid
        }, 'Error fetching batch');

        // Exponential backoff retry logic
        if (retryCount < MAX_RETRIES) {
          retryCount++;
          const backoffMs = RATE_LIMIT_DELAY_MS * Math.pow(2, retryCount - 1);

          logger.info({
            retry_count: retryCount,
            backoff_seconds: (backoffMs / 1000).toFixed(1)
          }, 'Retrying after backoff');

          await new Promise(resolve => setTimeout(resolve, backoffMs));
          continue; // Retry the same batch
        } else {
          // All retries exhausted - mark as interrupted
          logger.error({ error: classifiedError, chat_jid: chatJid }, 'All retries exhausted');

          checkpoint.interrupt(classifiedError);
          database.updateSyncStatus({
            is_syncing: false,
            messages_synced: checkpoint.messages_synced
          });
          throw new Error(classifiedError);
        }
      }
    }

    // Sync completed
    const totalElapsedMs = Date.now() - startTime;
    const avgMessagesPerSecond = checkpoint.messages_synced / (totalElapsedMs / 1000);

    checkpoint.complete();
    database.updateSyncStatus({
      is_syncing: false,
      messages_synced: checkpoint.messages_synced,
      progress_percent: 100,
      is_latest: true,
      last_sync_time: new Date()
    });

    logger.info({
      chat_jid: chatJid,
      total_messages: checkpoint.messages_synced,
      elapsed_seconds: (totalElapsedMs / 1000).toFixed(1),
      avg_messages_per_second: avgMessagesPerSecond.toFixed(2)
    }, 'History sync completed successfully');

  } catch (error) {
    const classifiedError = classifyError(error);
    logger.error({ error: classifiedError, chat_jid: chatJid }, 'History sync failed');

    // Mark as failed with classified error
    checkpoint.fail(classifiedError);
    database.updateSyncStatus({
      is_syncing: false,
      messages_synced: checkpoint.messages_synced
    });
  } finally {
    activeSyncs.delete(chatJid);
  }
}

/**
 * Fetch a batch of messages from Baileys using on-demand history sync
 *
 * This uses Baileys' fetchMessageHistory() function which requests
 * older messages from WhatsApp on-demand.
 */
async function fetchMessageBatch(
  sock: WASocket,
  chatJid: string,
  count: number,
  oldestMessageId: string | undefined,
  logger: Logger,
  database: DatabaseService
): Promise<{ messages: any[]; cursor: string | undefined }> {
  try {
    // Get the oldest message from database to use as cursor
    const oldestMessage = database.getOldestMessage(chatJid);

    if (!oldestMessage) {
      logger.warn({ chatJid }, 'No messages in database - cannot fetch older history without starting point');
      return { messages: [], cursor: undefined };
    }

    // Construct WAMessageKey for the oldest message
    const messageKey = {
      remoteJid: chatJid,
      id: oldestMessage.id,
      fromMe: oldestMessage.is_from_me
    };

    // Normalize timestamp to Unix seconds (fetchMessageHistory expects seconds, not milliseconds)
    const timestamp = normalizeTimestamp(oldestMessage.timestamp);

    logger.info({
      chatJid,
      oldestMessageId: oldestMessage.id,
      timestamp,
      count: Math.min(count, 50) // Cap at 50 per Baileys limitations
    }, 'Requesting message history from WhatsApp');

    // Request message history (returns immediately, messages arrive via event)
    await sock.fetchMessageHistory(
      Math.min(count, 50), // WhatsApp limits to 50 messages per request
      messageKey,
      timestamp
    );

    // Wait for messages to arrive via messaging-history.set event
    const { messages, cursor } = await waitForHistoryMessages(sock, 30000, logger);

    // Transform protobuf messages to our Message format
    const transformedMessages = messages.map((msg: proto.IWebMessageInfo) => {
      const messageTimestamp = msg.messageTimestamp;
      const timestampSeconds = Long.isLong(messageTimestamp)
        ? messageTimestamp.toNumber()
        : (typeof messageTimestamp === 'number' ? messageTimestamp : 0);

      return {
        id: msg.key?.id || '',
        chat_jid: chatJid,
        sender: msg.key?.participant || msg.key?.remoteJid || '',
        content: extractMessageContent(msg),
        timestamp: new Date(timestampSeconds * 1000), // Convert seconds to milliseconds
        is_from_me: msg.key?.fromMe || false
      };
    });

    logger.info({
      chatJid,
      messagesReceived: transformedMessages.length,
      cursor
    }, 'Successfully fetched message batch');

    return { messages: transformedMessages, cursor };

  } catch (error) {
    logger.error({ error, chat_jid: chatJid }, 'Error fetching message batch');
    throw error;
  }
}
