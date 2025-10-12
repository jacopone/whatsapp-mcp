import { WASocket } from '@whiskeysockets/baileys';
export interface BaileysClientConfig {
    authDir?: string;
    logLevel?: 'trace' | 'debug' | 'info' | 'warn' | 'error';
    syncFullHistory?: boolean;
}
export declare class BaileysClient {
    private sock;
    private logger;
    private authDir;
    private syncFullHistory;
    private isConnected;
    private reconnectTimeout;
    constructor(config?: BaileysClientConfig);
    /**
     * Ensure auth directory exists with secure permissions (700)
     */
    private ensureAuthDirectory;
    /**
     * Set file permissions to 600 (user rw only) for all files in auth directory
     */
    private setAuthFilePermissions;
    /**
     * Connect to WhatsApp servers
     * Handles both QR code auth (new devices) and automatic reconnection (existing sessions)
     */
    connect(): Promise<void>;
    /**
     * Setup event handlers for Baileys socket
     */
    private setupEventHandlers;
    /**
     * Schedule automatic reconnection after connection loss
     */
    private scheduleReconnect;
    /**
     * Disconnect from WhatsApp
     */
    disconnect(): void;
    /**
     * Check if connected to WhatsApp
     */
    getConnectionState(): boolean;
    /**
     * Get the Baileys socket instance
     * Returns null if not connected
     */
    getSocket(): WASocket | null;
    /**
     * Add event listener to Baileys socket
     */
    on(event: string, handler: (...args: any[]) => void): void;
    /**
     * Clean up resources
     */
    close(): void;
}
//# sourceMappingURL=baileys_client.d.ts.map