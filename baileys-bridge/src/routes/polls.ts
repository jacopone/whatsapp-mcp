import { Router, Request, Response } from 'express';
import { proto } from '@whiskeysockets/baileys';

/**
 * Poll Routes for Baileys Bridge
 *
 * Handles poll creation, voting, and result retrieval
 * using the Baileys WhatsApp library
 */

export function registerPollRoutes(router: Router, getSock: () => any) {
  // POST /polls/create-v2 - Create single-choice poll
  router.post('/polls/create-v2', async (req: Request, res: Response) => {
    const { chat_jid, name, options } = req.body;

    // Validation
    if (!chat_jid || !name || !options) {
      return res.status(400).json({
        success: false,
        message: 'Missing required fields: chat_jid, name, options'
      });
    }

    if (!Array.isArray(options) || options.length < 2 || options.length > 12) {
      return res.status(400).json({
        success: false,
        message: 'Options must be an array with 2-12 items'
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
      // Create poll message (v2 format - single choice)
      const pollMessage = {
        poll: {
          name,
          values: options,
          selectableCount: 1 // Single choice
        }
      };

      const result = await sock.sendMessage(chat_jid, pollMessage);

      res.json({
        success: true,
        message: 'Poll created successfully',
        message_id: result.key.id,
        chat_jid: result.key.remoteJid,
        poll_type: 'v2',
        selectable_count: 1
      });
    } catch (error: any) {
      res.status(500).json({
        success: false,
        message: 'Failed to create poll',
        error: error.message
      });
    }
  });

  // POST /polls/create-v3 - Create multiple-choice poll
  router.post('/polls/create-v3', async (req: Request, res: Response) => {
    const { chat_jid, name, options, allow_multiple = true, max_selections } = req.body;

    // Validation
    if (!chat_jid || !name || !options) {
      return res.status(400).json({
        success: false,
        message: 'Missing required fields: chat_jid, name, options'
      });
    }

    if (!Array.isArray(options) || options.length < 2 || options.length > 12) {
      return res.status(400).json({
        success: false,
        message: 'Options must be an array with 2-12 items'
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
      // Calculate selectable count
      let selectableCount = 1;
      if (allow_multiple) {
        selectableCount = max_selections || options.length;
      }

      // Create poll message (v3 format - multiple choice)
      const pollMessage = {
        poll: {
          name,
          values: options,
          selectableCount
        }
      };

      const result = await sock.sendMessage(chat_jid, pollMessage);

      res.json({
        success: true,
        message: 'Poll created successfully',
        message_id: result.key.id,
        chat_jid: result.key.remoteJid,
        poll_type: 'v3',
        selectable_count: selectableCount,
        allow_multiple: selectableCount > 1
      });
    } catch (error: any) {
      res.status(500).json({
        success: false,
        message: 'Failed to create poll',
        error: error.message
      });
    }
  });

  // POST /polls/:message_id/vote - Vote on a poll
  router.post('/polls/:message_id/vote', async (req: Request, res: Response) => {
    const { message_id } = req.params;
    const { chat_jid, option_indices } = req.body;

    // Validation
    if (!chat_jid || !option_indices) {
      return res.status(400).json({
        success: false,
        message: 'Missing required fields: chat_jid, option_indices'
      });
    }

    if (!Array.isArray(option_indices) || option_indices.length === 0) {
      return res.status(400).json({
        success: false,
        message: 'option_indices must be a non-empty array of numbers'
      });
    }

    // NOTE: Baileys does not support programmatic poll voting
    // See: https://github.com/WhiskeySockets/Baileys/issues/548
    // Poll voting can only be done manually through WhatsApp clients
    res.status(501).json({
      success: false,
      message: 'Poll voting is not supported programmatically via Baileys',
      note: 'Voting can only be done manually through WhatsApp clients. This is a known Baileys limitation (Issue #548)',
      message_id,
      chat_jid,
      requested_options: option_indices
    });
  });

  // GET /polls/:message_id/results - Get poll results
  router.get('/polls/:message_id/results', async (req: Request, res: Response) => {
    const { message_id } = req.params;
    const { chat_jid } = req.query;

    // Validation
    if (!chat_jid) {
      return res.status(400).json({
        success: false,
        message: 'Missing required query parameter: chat_jid'
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
      // Note: Baileys stores poll results locally when they're received
      // This is a simplified implementation - in production you'd query
      // the message store for the poll message and its votes

      res.json({
        success: true,
        message: 'Poll results retrieval not fully implemented in this version',
        message_id,
        chat_jid,
        note: 'Poll results are tracked via message events. Implement message store querying for full functionality.'
      });
    } catch (error: any) {
      res.status(500).json({
        success: false,
        message: 'Failed to get poll results',
        error: error.message
      });
    }
  });

  return router;
}
