/**
 * Sync Checkpoint Model
 *
 * Tracks the state of history synchronization for a chat.
 * Used to enable resumable sync operations with progress tracking.
 */

/**
 * Sync status states representing the checkpoint lifecycle
 */
export enum SyncStatus {
  NOT_STARTED = 'not_started',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  INTERRUPTED = 'interrupted',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

/**
 * Checkpoint data structure for history sync
 */
export interface SyncCheckpointData {
  chat_jid: string;
  last_message_id: string | null;
  last_timestamp: number | null;  // Unix timestamp in milliseconds
  messages_synced: number;
  status: SyncStatus;
  created_at: Date;
  updated_at: Date;
  error_message?: string;
}

/**
 * SyncCheckpoint class for managing history sync state
 */
export class SyncCheckpoint {
  public chat_jid: string;
  public last_message_id: string | null;
  public last_timestamp: number | null;
  public messages_synced: number;
  public status: SyncStatus;
  public created_at: Date;
  public updated_at: Date;
  public error_message?: string;

  constructor(data: Partial<SyncCheckpointData> & { chat_jid: string }) {
    this.chat_jid = data.chat_jid;
    this.last_message_id = data.last_message_id || null;
    this.last_timestamp = data.last_timestamp || null;
    this.messages_synced = data.messages_synced || 0;
    this.status = data.status || SyncStatus.NOT_STARTED;
    this.created_at = data.created_at || new Date();
    this.updated_at = data.updated_at || new Date();
    this.error_message = data.error_message;

    this.validate();
  }

  /**
   * Validate checkpoint data
   *
   * @throws Error if validation fails
   */
  validate(): void {
    if (!this.chat_jid || this.chat_jid.trim().length === 0) {
      throw new Error('chat_jid is required and cannot be empty');
    }

    if (!this.chat_jid.includes('@')) {
      throw new Error('chat_jid must be a valid WhatsApp JID (must contain @)');
    }

    if (this.messages_synced < 0) {
      throw new Error('messages_synced cannot be negative');
    }

    if (this.last_timestamp !== null && this.last_timestamp < 0) {
      throw new Error('last_timestamp cannot be negative');
    }

    // Validate status transitions
    this.validateStatusTransition();
  }

  /**
   * Validate that status transitions follow allowed state machine
   */
  private validateStatusTransition(): void {
    const validTransitions: Record<SyncStatus, SyncStatus[]> = {
      [SyncStatus.NOT_STARTED]: [SyncStatus.IN_PROGRESS],
      [SyncStatus.IN_PROGRESS]: [
        SyncStatus.COMPLETED,
        SyncStatus.INTERRUPTED,
        SyncStatus.FAILED,
        SyncStatus.CANCELLED
      ],
      [SyncStatus.INTERRUPTED]: [SyncStatus.IN_PROGRESS, SyncStatus.CANCELLED],
      [SyncStatus.FAILED]: [SyncStatus.IN_PROGRESS],
      [SyncStatus.CANCELLED]: [],  // Terminal state
      [SyncStatus.COMPLETED]: []   // Terminal state
    };

    // This validation is for current status only
    // Transition validation happens in updateStatus()
  }

  /**
   * Update checkpoint status with validation
   *
   * @param newStatus - New status to transition to
   * @param errorMessage - Optional error message for failed/interrupted status
   * @throws Error if transition is invalid
   */
  updateStatus(newStatus: SyncStatus, errorMessage?: string): void {
    const validTransitions: Record<SyncStatus, SyncStatus[]> = {
      [SyncStatus.NOT_STARTED]: [SyncStatus.IN_PROGRESS],
      [SyncStatus.IN_PROGRESS]: [
        SyncStatus.COMPLETED,
        SyncStatus.INTERRUPTED,
        SyncStatus.FAILED,
        SyncStatus.CANCELLED
      ],
      [SyncStatus.INTERRUPTED]: [SyncStatus.IN_PROGRESS, SyncStatus.CANCELLED],
      [SyncStatus.FAILED]: [SyncStatus.IN_PROGRESS],
      [SyncStatus.CANCELLED]: [],
      [SyncStatus.COMPLETED]: []
    };

    const allowed = validTransitions[this.status];
    if (!allowed.includes(newStatus)) {
      throw new Error(
        `Invalid status transition: ${this.status} → ${newStatus}. ` +
        `Allowed transitions: ${allowed.join(', ')}`
      );
    }

    this.status = newStatus;
    this.updated_at = new Date();

    if (errorMessage) {
      this.error_message = errorMessage;
    }
  }

  /**
   * Update checkpoint progress (called during sync)
   *
   * @param lastMessageId - ID of last synced message
   * @param lastTimestamp - Timestamp of last synced message
   * @param messageCount - Number of messages synced in this batch
   */
  updateProgress(
    lastMessageId: string,
    lastTimestamp: number,
    messageCount: number
  ): void {
    if (this.status !== SyncStatus.IN_PROGRESS) {
      throw new Error(
        `Cannot update progress when status is ${this.status}. ` +
        'Progress updates only allowed during IN_PROGRESS status.'
      );
    }

    this.last_message_id = lastMessageId;
    this.last_timestamp = lastTimestamp;
    this.messages_synced += messageCount;
    this.updated_at = new Date();
  }

  /**
   * Mark checkpoint as started (transition to IN_PROGRESS)
   */
  start(): void {
    this.updateStatus(SyncStatus.IN_PROGRESS);
  }

  /**
   * Mark checkpoint as completed
   */
  complete(): void {
    this.updateStatus(SyncStatus.COMPLETED);
  }

  /**
   * Mark checkpoint as interrupted (network error, etc.)
   *
   * @param errorMessage - Reason for interruption
   */
  interrupt(errorMessage: string): void {
    this.updateStatus(SyncStatus.INTERRUPTED, errorMessage);
  }

  /**
   * Mark checkpoint as failed
   *
   * @param errorMessage - Reason for failure
   */
  fail(errorMessage: string): void {
    this.updateStatus(SyncStatus.FAILED, errorMessage);
  }

  /**
   * Mark checkpoint as cancelled
   */
  cancel(): void {
    this.updateStatus(SyncStatus.CANCELLED);
  }

  /**
   * Resume checkpoint from interrupted/failed state
   */
  resume(): void {
    if (this.status === SyncStatus.INTERRUPTED || this.status === SyncStatus.FAILED) {
      this.updateStatus(SyncStatus.IN_PROGRESS);
      this.error_message = undefined;
    } else {
      throw new Error(
        `Cannot resume checkpoint with status ${this.status}. ` +
        'Only INTERRUPTED or FAILED checkpoints can be resumed.'
      );
    }
  }

  /**
   * Check if checkpoint is in a terminal state
   *
   * @returns true if checkpoint is completed or cancelled
   */
  isTerminal(): boolean {
    return this.status === SyncStatus.COMPLETED || this.status === SyncStatus.CANCELLED;
  }

  /**
   * Check if checkpoint can be resumed
   *
   * @returns true if checkpoint is interrupted or failed
   */
  canResume(): boolean {
    return this.status === SyncStatus.INTERRUPTED || this.status === SyncStatus.FAILED;
  }

  /**
   * Check if checkpoint is active (in progress)
   *
   * @returns true if checkpoint is in progress
   */
  isActive(): boolean {
    return this.status === SyncStatus.IN_PROGRESS;
  }

  /**
   * Serialize checkpoint to JSON
   *
   * @returns JSON-serializable object
   */
  toJSON(): Record<string, any> {
    return {
      chat_jid: this.chat_jid,
      last_message_id: this.last_message_id,
      last_timestamp: this.last_timestamp,
      messages_synced: this.messages_synced,
      status: this.status,
      created_at: this.created_at.toISOString(),
      updated_at: this.updated_at.toISOString(),
      error_message: this.error_message
    };
  }

  /**
   * Deserialize checkpoint from JSON
   *
   * @param json - JSON object to deserialize
   * @returns SyncCheckpoint instance
   */
  static fromJSON(json: Record<string, any>): SyncCheckpoint {
    return new SyncCheckpoint({
      chat_jid: json.chat_jid,
      last_message_id: json.last_message_id,
      last_timestamp: json.last_timestamp,
      messages_synced: json.messages_synced,
      status: json.status as SyncStatus,
      created_at: new Date(json.created_at),
      updated_at: new Date(json.updated_at),
      error_message: json.error_message
    });
  }

  /**
   * Create a new checkpoint for a chat (initial state)
   *
   * @param chatJid - WhatsApp JID of the chat
   * @returns New SyncCheckpoint instance
   */
  static create(chatJid: string): SyncCheckpoint {
    return new SyncCheckpoint({
      chat_jid: chatJid,
      status: SyncStatus.NOT_STARTED
    });
  }

  /**
   * Get human-readable status description
   *
   * @returns Status description
   */
  getStatusDescription(): string {
    const descriptions: Record<SyncStatus, string> = {
      [SyncStatus.NOT_STARTED]: 'Sync has not started yet',
      [SyncStatus.IN_PROGRESS]: `Syncing messages (${this.messages_synced} synced)`,
      [SyncStatus.COMPLETED]: `Sync completed (${this.messages_synced} messages)`,
      [SyncStatus.INTERRUPTED]: `Sync interrupted: ${this.error_message || 'Unknown reason'}`,
      [SyncStatus.FAILED]: `Sync failed: ${this.error_message || 'Unknown error'}`,
      [SyncStatus.CANCELLED]: 'Sync was cancelled by user'
    };

    return descriptions[this.status];
  }

  /**
   * Get checkpoint summary for logging
   *
   * @returns Summary string
   */
  toString(): string {
    return `SyncCheckpoint[${this.chat_jid}]: ` +
      `status=${this.status}, ` +
      `messages=${this.messages_synced}, ` +
      `last_ts=${this.last_timestamp}`;
  }
}
