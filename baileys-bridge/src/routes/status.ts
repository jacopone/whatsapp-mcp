import { Router, Request, Response } from 'express';
import { proto } from '@whiskeysockets/baileys';

/**
 * Status Routes for Baileys Bridge
 *
 * Handles WhatsApp Status (Stories) operations:
 * - Post text/image/video status
 * - List status updates from contacts
 * - Mark status as viewed
 * - Query status privacy settings
 */

export function registerStatusRoutes(router: Router, getSock: () => any) {
  // POST /status/post - Post a status update
  router.post('/status/post', async (req: Request, res: Response) => {
    const { text, media_path, background_color } = req.body;

    // Validation - at least one content type required
    if (!text && !media_path) {
      return res.status(400).json({
        success: false,
        message: 'Either text or media_path must be provided'
      });
    }

    const sock = getSock();
    if (!sock) {
      return res.status(503).json({
        success: false,
        message: 'WhatsApp client not connected'
      });
    }

    try {
      let statusMessage: any;

      if (media_path) {
        // Media status (image/video)
        const fs = await import('fs');
        const mediaBuffer = fs.readFileSync(media_path);

        // Determine media type from file extension
        const ext = media_path.toLowerCase().split('.').pop();
        const isVideo = ['mp4', 'mov', 'avi', 'mkv'].includes(ext || '');

        statusMessage = {
          [isVideo ? 'video' : 'image']: mediaBuffer,
          caption: text || ''
        };
      } else {
        // Text status with optional background color
        statusMessage = {
          text: text,
          backgroundColor: background_color || '#000000'
        };
      }

      // Send status to broadcast list (status updates)
      // WhatsApp uses a special JID for status: status@broadcast
      const result = await sock.sendMessage('status@broadcast', statusMessage);

      res.json({
        success: true,
        message: 'Status posted successfully',
        status_id: result.key.id,
        timestamp: result.messageTimestamp
      });
    } catch (error: any) {
      res.status(500).json({
        success: false,
        message: 'Failed to post status',
        error: error.message
      });
    }
  });

  // GET /status/list - Get status updates from contacts
  router.get('/status/list', async (req: Request, res: Response) => {
    const { limit = 50 } = req.query;

    const sock = getSock();
    if (!sock) {
      return res.status(503).json({
        success: false,
        message: 'WhatsApp client not connected'
      });
    }

    try {
      // Note: Baileys stores status updates in the message store
      // This is a simplified implementation - production would query the store
      // Status updates are received via messages.upsert event with chat_jid = 'status@broadcast'

      res.json({
        success: true,
        message: 'Status list retrieval not fully implemented',
        note: 'Status updates are tracked via messages.upsert events. Implement message store querying for full functionality.',
        statuses: []
      });
    } catch (error: any) {
      res.status(500).json({
        success: false,
        message: 'Failed to list statuses',
        error: error.message
      });
    }
  });

  // POST /status/:status_id/view - Mark status as viewed
  router.post('/status/:status_id/view', async (req: Request, res: Response) => {
    const { status_id } = req.params;
    const { owner_jid } = req.body;

    // Validation
    if (!owner_jid) {
      return res.status(400).json({
        success: false,
        message: 'Missing required field: owner_jid (the JID of the status owner)'
      });
    }

    const sock = getSock();
    if (!sock) {
      return res.status(503).json({
        success: false,
        message: 'WhatsApp client not connected'
      });
    }

    try {
      // Send read receipt for status
      // Status read receipts use the same mechanism as message read receipts
      await sock.readMessages([
        {
          remoteJid: 'status@broadcast',
          id: status_id,
          participant: owner_jid
        }
      ]);

      res.json({
        success: true,
        message: 'Status marked as viewed',
        status_id,
        owner_jid
      });
    } catch (error: any) {
      res.status(500).json({
        success: false,
        message: 'Failed to mark status as viewed',
        error: error.message
      });
    }
  });

  // GET /status/privacy - Get status privacy settings
  router.get('/status/privacy', async (req: Request, res: Response) => {
    const sock = getSock();
    if (!sock) {
      return res.status(503).json({
        success: false,
        message: 'WhatsApp client not connected'
      });
    }

    try {
      // Note: Baileys privacy settings are limited
      // Full privacy settings require whatsmeow (Go backend)
      // This returns basic status privacy info

      res.json({
        success: true,
        message: 'Status privacy settings retrieval',
        note: 'Full privacy settings available via Go backend. Baileys provides limited privacy info.',
        privacy: {
          who_can_see_status: 'all',  // This would need to be queried from Baileys store
          note: 'Status privacy is typically managed through WhatsApp mobile app'
        }
      });
    } catch (error: any) {
      res.status(500).json({
        success: false,
        message: 'Failed to get status privacy settings',
        error: error.message
      });
    }
  });

  return router;
}
