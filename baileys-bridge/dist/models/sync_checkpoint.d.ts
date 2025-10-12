/**
 * Sync Checkpoint Model
 *
 * Tracks the state of history synchronization for a chat.
 * Used to enable resumable sync operations with progress tracking.
 */
/**
 * Sync status states representing the checkpoint lifecycle
 */
export declare enum SyncStatus {
    NOT_STARTED = "not_started",
    IN_PROGRESS = "in_progress",
    COMPLETED = "completed",
    INTERRUPTED = "interrupted",
    FAILED = "failed",
    CANCELLED = "cancelled"
}
/**
 * Checkpoint data structure for history sync
 */
export interface SyncCheckpointData {
    chat_jid: string;
    last_message_id: string | null;
    last_timestamp: number | null;
    messages_synced: number;
    status: SyncStatus;
    created_at: Date;
    updated_at: Date;
    error_message?: string;
}
/**
 * SyncCheckpoint class for managing history sync state
 */
export declare class SyncCheckpoint {
    chat_jid: string;
    last_message_id: string | null;
    last_timestamp: number | null;
    messages_synced: number;
    status: SyncStatus;
    created_at: Date;
    updated_at: Date;
    error_message?: string;
    constructor(data: Partial<SyncCheckpointData> & {
        chat_jid: string;
    });
    /**
     * Validate checkpoint data
     *
     * @throws Error if validation fails
     */
    validate(): void;
    /**
     * Validate that status transitions follow allowed state machine
     */
    private validateStatusTransition;
    /**
     * Update checkpoint status with validation
     *
     * @param newStatus - New status to transition to
     * @param errorMessage - Optional error message for failed/interrupted status
     * @throws Error if transition is invalid
     */
    updateStatus(newStatus: SyncStatus, errorMessage?: string): void;
    /**
     * Update checkpoint progress (called during sync)
     *
     * @param lastMessageId - ID of last synced message
     * @param lastTimestamp - Timestamp of last synced message
     * @param messageCount - Number of messages synced in this batch
     */
    updateProgress(lastMessageId: string, lastTimestamp: number, messageCount: number): void;
    /**
     * Mark checkpoint as started (transition to IN_PROGRESS)
     */
    start(): void;
    /**
     * Mark checkpoint as completed
     */
    complete(): void;
    /**
     * Mark checkpoint as interrupted (network error, etc.)
     *
     * @param errorMessage - Reason for interruption
     */
    interrupt(errorMessage: string): void;
    /**
     * Mark checkpoint as failed
     *
     * @param errorMessage - Reason for failure
     */
    fail(errorMessage: string): void;
    /**
     * Mark checkpoint as cancelled
     */
    cancel(): void;
    /**
     * Resume checkpoint from interrupted/failed state
     */
    resume(): void;
    /**
     * Check if checkpoint is in a terminal state
     *
     * @returns true if checkpoint is completed or cancelled
     */
    isTerminal(): boolean;
    /**
     * Check if checkpoint can be resumed
     *
     * @returns true if checkpoint is interrupted or failed
     */
    canResume(): boolean;
    /**
     * Check if checkpoint is active (in progress)
     *
     * @returns true if checkpoint is in progress
     */
    isActive(): boolean;
    /**
     * Serialize checkpoint to JSON
     *
     * @returns JSON-serializable object
     */
    toJSON(): Record<string, any>;
    /**
     * Deserialize checkpoint from JSON
     *
     * @param json - JSON object to deserialize
     * @returns SyncCheckpoint instance
     */
    static fromJSON(json: Record<string, any>): SyncCheckpoint;
    /**
     * Create a new checkpoint for a chat (initial state)
     *
     * @param chatJid - WhatsApp JID of the chat
     * @returns New SyncCheckpoint instance
     */
    static create(chatJid: string): SyncCheckpoint;
    /**
     * Get human-readable status description
     *
     * @returns Status description
     */
    getStatusDescription(): string;
    /**
     * Get checkpoint summary for logging
     *
     * @returns Summary string
     */
    toString(): string;
}
//# sourceMappingURL=sync_checkpoint.d.ts.map