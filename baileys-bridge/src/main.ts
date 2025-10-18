import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
  Browsers,
  proto,
  WAMessage,
  Chat
} from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import pino from 'pino';
import express from 'express';
import qrcode from 'qrcode-terminal';
import {
  storeChat,
  storeMessage,
  updateSyncStatus,
  getSyncStatus,
  getAllMessages,
  clearAllData,
  Message
} from './database.js';
import { BaileysClient } from './services/baileys_client.js';
import { DatabaseService } from './services/database.js';
import { createHistoryRouter } from './routes/history.js';
import { registerPollRoutes } from './routes/polls.js';
import { registerStatusRoutes } from './routes/status.js';
import { registerPrivacyRoutes } from './routes/privacy.js';
import { registerBusinessRoutes } from './routes/business.js';
import { Router } from 'express';

const logger = pino({ level: 'info' });
const app = express();
app.use(express.json());

let sock: ReturnType<typeof makeWASocket> | null = null;
let isConnected = false;

// Parse message for database storage
function parseMessageForDb(msg: WAMessage): Message | null {
  if (!msg.key.id || !msg.key.remoteJid) return null;

  const timestamp = msg.messageTimestamp
    ? new Date(Number(msg.messageTimestamp) * 1000)
    : new Date();

  const content =
    msg.message?.conversation ||
    msg.message?.extendedTextMessage?.text ||
    msg.message?.imageMessage?.caption ||
    msg.message?.videoMessage?.caption ||
    '';

  return {
    id: msg.key.id,
    chat_jid: msg.key.remoteJid,
    sender: msg.key.participant || msg.key.remoteJid,
    content: content || '[Media/System Message]',
    timestamp,
    is_from_me: msg.key.fromMe || false
  };
}

// Connect to WhatsApp
async function connectToWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState('auth_baileys');
  const { version, isLatest } = await fetchLatestBaileysVersion();

  logger.info(`Using Baileys v${version.join('.')}, isLatest: ${isLatest}`);

  sock = makeWASocket({
    version,
    logger,
    printQRInTerminal: false, // We'll handle QR display via API
    auth: state,
    browser: Browsers.macOS('Desktop'),
    syncFullHistory: true, // THE KEY FEATURE!
    getMessage: async (key) => {
      // Required by Baileys for message handling
      return { conversation: '' };
    }
  });

  // Handle QR code
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log('\n📱 Scan this QR code with WhatsApp:');
      qrcode.generate(qr, { small: true });
    }

    if (connection === 'close') {
      const shouldReconnect = (lastDisconnect?.error as Boom)?.output?.statusCode !== DisconnectReason.loggedOut;
      logger.info({ shouldReconnect }, 'Connection closed');
      isConnected = false;

      if (shouldReconnect) {
        setTimeout(connectToWhatsApp, 3000);
      }
    } else if (connection === 'open') {
      logger.info('✅ Connected to WhatsApp!');
      isConnected = true;
    }
  });

  // Save credentials on update
  sock.ev.on('creds.update', saveCreds);

  // THE CRITICAL EVENT: History sync
  sock.ev.on('messaging-history.set', async ({ chats, contacts, messages, isLatest, progress, syncType }) => {
    logger.info(`📥 Receiving history sync: ${chats.length} chats, ${messages.length} messages (progress: ${progress}%, isLatest: ${isLatest}, type: ${syncType})`);

    // Detect ON_DEMAND history sync (from fetchMessageHistory)
    if (syncType === proto.HistorySync.HistorySyncType.ON_DEMAND) {
      logger.info(`🎯 ON-DEMAND history sync - ${messages.length} older messages retrieved`);
    }

    updateSyncStatus({
      is_syncing: true,
      progress_percent: progress || 0,
      is_latest: isLatest || false
    });

    // Store chats
    let chatsStored = 0;
    for (const chat of chats) {
      try {
        storeChat({
          jid: chat.id,
          name: chat.name || undefined,
          last_message_time: chat.conversationTimestamp
            ? new Date(Number(chat.conversationTimestamp) * 1000)
            : undefined
        });
        chatsStored++;
      } catch (error) {
        logger.error({ error, chatId: chat.id }, 'Error storing chat');
      }
    }

    // Store messages
    let messagesStored = 0;
    for (const msg of messages) {
      try {
        const parsed = parseMessageForDb(msg);
        if (parsed) {
          storeMessage(parsed);
          messagesStored++;
        }
      } catch (error) {
        logger.error({ error }, 'Error storing message');
      }
    }

    logger.info(`✅ Stored ${chatsStored} chats, ${messagesStored} messages`);

    // Update status
    const currentStatus = getSyncStatus();
    updateSyncStatus({
      is_syncing: !isLatest,
      last_sync_time: new Date(),
      messages_synced: currentStatus.messages_synced + messagesStored,
      chats_synced: currentStatus.chats_synced + chatsStored,
      progress_percent: progress || 0,
      is_latest: isLatest || false
    });

    if (isLatest) {
      logger.info('🎉 History sync complete!');
    }
  });

  // Real-time message handling
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type === 'notify') {
      for (const msg of messages) {
        const parsed = parseMessageForDb(msg);
        if (parsed) {
          storeMessage(parsed);
          logger.info(`📩 New message from ${parsed.sender}`);
        }
      }
    }
  });
}

// REST API Endpoints

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    connected: isConnected,
    uptime: process.uptime()
  });
});

// Get sync status
app.get('/api/sync/status', (req, res) => {
  const status = getSyncStatus();
  res.json({
    connected: isConnected,
    ...status
  });
});

// Trigger manual history sync (if supported)
app.post('/api/sync/trigger', async (req, res) => {
  if (!sock || !isConnected) {
    return res.status(503).json({
      success: false,
      message: 'Not connected to WhatsApp'
    });
  }

  // Note: syncFullHistory runs automatically on connect
  // This endpoint mainly returns current status
  const status = getSyncStatus();
  res.json({
    success: true,
    message: 'History sync is automatic on connect. Check /api/sync/status for progress.',
    status
  });
});

// Get all synced messages (for transfer to Go DB)
app.get('/api/messages', (req, res) => {
  try {
    const messages = getAllMessages();
    res.json({
      success: true,
      count: messages.length,
      messages
    });
  } catch (error) {
    logger.error({ error }, 'Error fetching messages');
    res.status(500).json({
      success: false,
      message: 'Failed to fetch messages',
      error: String(error)
    });
  }
});

// Clear all data (after successful sync to Go)
app.post('/api/clear', (req, res) => {
  try {
    clearAllData();
    logger.info('🧹 Cleared all temporary data');
    res.json({
      success: true,
      message: 'All data cleared successfully'
    });
  } catch (error) {
    logger.error({ error }, 'Error clearing data');
    res.status(500).json({
      success: false,
      message: 'Failed to clear data',
      error: String(error)
    });
  }
});

// Deep History Fetch Endpoint - Fetch messages from 2010-2015 era
app.post('/api/history/fetch-older', async (req, res) => {
  if (!sock || !isConnected) {
    return res.status(503).json({
      success: false,
      message: 'Not connected to WhatsApp'
    });
  }

  const {
    chat_jid,
    oldest_message_id,
    oldest_timestamp_ms,
    from_me = false,
    count = 100
  } = req.body;

  // Validation
  if (!chat_jid || !oldest_message_id || !oldest_timestamp_ms) {
    return res.status(400).json({
      success: false,
      message: 'Required: chat_jid, oldest_message_id, oldest_timestamp_ms'
    });
  }

  try {
    // Build message key
    const messageKey = {
      remoteJid: chat_jid,
      id: oldest_message_id,
      fromMe: from_me
    };

    // Request older messages from WhatsApp
    logger.info({
      chat_jid,
      oldest_message_id,
      oldest_timestamp_ms,
      count
    }, '📥 Requesting older messages via fetchMessageHistory');

    const requestId = await sock.fetchMessageHistory(
      count,
      messageKey,
      oldest_timestamp_ms
    );

    logger.info({ requestId }, '✓ History fetch request sent');

    res.json({
      success: true,
      message: `Requested ${count} older messages for ${chat_jid}`,
      request_id: requestId,
      info: 'Messages will arrive via messaging-history.set event with syncType=ON_DEMAND'
    });

  } catch (error) {
    logger.error({ error }, 'Error requesting older messages');
    res.status(500).json({
      success: false,
      message: 'Failed to request older messages',
      error: String(error)
    });
  }
});

// Register poll routes
const pollRouter = Router();
registerPollRoutes(pollRouter, () => sock);
app.use('/api', pollRouter);

// Register status routes
const statusRouter = Router();
registerStatusRoutes(statusRouter, () => sock);
app.use('/api', statusRouter);

// Register privacy routes
const privacyRouter = Router();
registerPrivacyRoutes(privacyRouter, () => sock);
app.use('/api', privacyRouter);

// Register business routes
const businessRouter = Router();
registerBusinessRoutes(businessRouter, () => sock);
app.use('/api', businessRouter);

// Initialize database service for history sync
const databaseService = new DatabaseService({
  dataDir: 'data',
  dbName: 'baileys_temp.db',
  logLevel: 'info'
});

// Create a simple adapter to make legacy sock compatible with BaileysClient interface
const legacyBaileysAdapter = {
  getSocket: () => sock,
  getConnectionState: () => isConnected,
  connect: async () => { /* Using legacy connection */ },
  disconnect: () => { /* Using legacy connection */ },
  close: () => { /* Using legacy connection */ }
};

// Register history routes with Go database path for cursor initialization
const historyRouter = createHistoryRouter({
  baileysClient: legacyBaileysAdapter as any, // Cast to bypass TypeScript type checking
  database: databaseService,
  logLevel: 'info',
  goDbPath: '../whatsapp-bridge/store/messages.db' // Path to Go database for reading oldest messages
});
app.use('/history', historyRouter);

// Start server
const PORT = 8081;
app.listen(PORT, () => {
  logger.info(`🚀 Baileys bridge running on port ${PORT}`);
  logger.info(`   Health: http://localhost:${PORT}/health`);
  logger.info(`   Sync Status: http://localhost:${PORT}/api/sync/status`);
  logger.info(`   Messages: http://localhost:${PORT}/api/messages`);
  logger.info(`   History Sync: http://localhost:${PORT}/history/sync`);
  logger.info(`   Bulk Sync: http://localhost:${PORT}/history/sync/bulk`);

  // Connect to WhatsApp (legacy connection)
  connectToWhatsApp().catch(error => {
    logger.error({ error }, 'Failed to connect to WhatsApp (legacy)');
  });

  // Note: BaileysClient NOT connected here to avoid conflict with legacy sock
  // The history router will use the legacy sock via a wrapper
  // TODO: Refactor to use only BaileysClient for all routes
});

// Graceful shutdown
process.on('SIGINT', () => {
  logger.info('Shutting down gracefully...');
  if (sock) {
    sock.end(undefined);
  }
  databaseService.close();
  process.exit(0);
});
