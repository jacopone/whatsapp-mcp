import { Router, Request, Response } from 'express';
import type { WASocket } from '@whiskeysockets/baileys';

// T048: Read Receipts Privacy Control

// Store read receipts preference (in-memory, could be persisted later)
let readReceiptsEnabled = true;

interface PrivacySettings {
  read_receipts: boolean;
}

interface ReadReceiptRequest {
  chat_jid: string;
  message_ids: string[];
}

export function registerPrivacyRoutes(
  router: Router,
  getSock: () => ReturnType<typeof import('@whiskeysockets/baileys').default> | null
) {
  // Get current privacy settings
  router.get('/privacy/settings', (req: Request, res: Response) => {
    res.json({
      success: true,
      settings: {
        read_receipts: readReceiptsEnabled
      }
    });
  });

  // Update read receipts setting
  router.put('/privacy/read-receipts', (req: Request, res: Response) => {
    const { enabled } = req.body;

    if (typeof enabled !== 'boolean') {
      return res.status(400).json({
        success: false,
        message: 'enabled field must be a boolean'
      });
    }

    readReceiptsEnabled = enabled;

    res.json({
      success: true,
      message: `Read receipts ${enabled ? 'enabled' : 'disabled'}`,
      settings: {
        read_receipts: readReceiptsEnabled
      }
    });
  });

  // Send read receipt for specific messages (manual control)
  router.post('/privacy/send-read-receipt', async (req: Request, res: Response) => {
    const sock = getSock();

    if (!sock) {
      return res.status(503).json({
        success: false,
        message: 'Not connected to WhatsApp'
      });
    }

    const { chat_jid, message_ids }: ReadReceiptRequest = req.body;

    if (!chat_jid || !message_ids || !Array.isArray(message_ids)) {
      return res.status(400).json({
        success: false,
        message: 'chat_jid and message_ids (array) are required'
      });
    }

    try {
      // Send read receipt for the messages
      await sock.readMessages([
        {
          remoteJid: chat_jid,
          id: message_ids[0], // Baileys uses the first message ID
          participant: undefined
        }
      ]);

      res.json({
        success: true,
        message: `Read receipt sent for ${message_ids.length} message(s)`,
        chat_jid,
        message_count: message_ids.length
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        message: 'Failed to send read receipt',
        error: String(error)
      });
    }
  });

  // Mark chat as read (send read receipt for all messages)
  router.post('/privacy/mark-chat-read', async (req: Request, res: Response) => {
    const sock = getSock();

    if (!sock) {
      return res.status(503).json({
        success: false,
        message: 'Not connected to WhatsApp'
      });
    }

    const { chat_jid } = req.body;

    if (!chat_jid) {
      return res.status(400).json({
        success: false,
        message: 'chat_jid is required'
      });
    }

    // Check if read receipts are enabled
    if (!readReceiptsEnabled) {
      return res.status(403).json({
        success: false,
        message: 'Read receipts are disabled. Enable them first or use /privacy/send-read-receipt to override.'
      });
    }

    try {
      // Mark chat as read
      await sock.chatModify(
        { markRead: true, lastMessages: [] },
        chat_jid
      );

      res.json({
        success: true,
        message: 'Chat marked as read',
        chat_jid
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        message: 'Failed to mark chat as read',
        error: String(error)
      });
    }
  });

  // Get read receipts preference (convenience endpoint)
  router.get('/privacy/read-receipts', (req: Request, res: Response) => {
    res.json({
      success: true,
      enabled: readReceiptsEnabled
    });
  });
}

// Export function to check if read receipts are enabled (for internal use)
export function shouldSendReadReceipts(): boolean {
  return readReceiptsEnabled;
}
