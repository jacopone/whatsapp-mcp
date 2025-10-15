import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
  Browsers,
  WASocket,
  ConnectionState
} from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import pino, { Logger } from 'pino';
import qrcode from 'qrcode-terminal';
import * as fs from 'fs';
import * as path from 'path';

export interface BaileysClientConfig {
  authDir?: string;          // Directory for authentication state (default: data/auth_baileys/)
  logLevel?: 'trace' | 'debug' | 'info' | 'warn' | 'error';  // Log level (default: info)
  syncFullHistory?: boolean; // Enable full history sync on connect (default: true)
}

export class BaileysClient {
  private sock: WASocket | null = null;
  private logger: Logger;
  private authDir: string;
  private syncFullHistory: boolean;
  private isConnected: boolean = false;
  private reconnectTimeout: NodeJS.Timeout | null = null;

  constructor(config: BaileysClientConfig = {}) {
    // Set defaults
    this.authDir = config.authDir || 'data/auth_baileys';
    this.syncFullHistory = config.syncFullHistory ?? true;

    // Create logger
    this.logger = pino({ level: config.logLevel || 'info' });

    // Create auth directory with secure permissions
    this.ensureAuthDirectory();
  }

  /**
   * Ensure auth directory exists with secure permissions (700)
   */
  private ensureAuthDirectory(): void {
    if (!fs.existsSync(this.authDir)) {
      fs.mkdirSync(this.authDir, { recursive: true, mode: 0o700 });
      this.logger.info(`Created auth directory: ${this.authDir}`);
    }

    // Set permissions to 700 (user rwx only)
    try {
      fs.chmodSync(this.authDir, 0o700);
    } catch (error) {
      this.logger.warn({ error }, 'Failed to set auth directory permissions');
    }
  }

  /**
   * Set file permissions to 600 (user rw only) for all files in auth directory
   */
  private setAuthFilePermissions(): void {
    try {
      if (!fs.existsSync(this.authDir)) return;

      const files = fs.readdirSync(this.authDir);
      for (const file of files) {
        const filePath = path.join(this.authDir, file);
        const stats = fs.statSync(filePath);

        if (stats.isFile()) {
          fs.chmodSync(filePath, 0o600);
        }
      }
      this.logger.debug('Set auth file permissions to 600');
    } catch (error) {
      this.logger.warn({ error }, 'Failed to set auth file permissions');
    }
  }

  /**
   * Connect to WhatsApp servers
   * Handles both QR code auth (new devices) and automatic reconnection (existing sessions)
   */
  async connect(): Promise<void> {
    try {
      // Load authentication state
      const { state, saveCreds } = await useMultiFileAuthState(this.authDir);

      // Set file permissions after auth state is loaded
      this.setAuthFilePermissions();

      // Fetch latest Baileys version
      const { version, isLatest } = await fetchLatestBaileysVersion();
      this.logger.info(`Using Baileys v${version.join('.')}, isLatest: ${isLatest}`);

      // Create WhatsApp socket
      this.sock = makeWASocket({
        version,
        logger: this.logger,
        printQRInTerminal: false, // We handle QR display
        auth: state,
        browser: Browsers.macOS('Desktop'),
        syncFullHistory: this.syncFullHistory,
        getMessage: async (key) => {
          // Required by Baileys for message handling
          return { conversation: '' };
        }
      });

      // Setup event handlers
      this.setupEventHandlers(saveCreds);

      this.logger.info('Baileys client initialized');
    } catch (error) {
      this.logger.error({ error }, 'Failed to connect to WhatsApp');
      throw error;
    }
  }

  /**
   * Setup event handlers for Baileys socket
   */
  private setupEventHandlers(saveCreds: () => Promise<void>): void {
    if (!this.sock) return;

    // Handle connection updates
    this.sock.ev.on('connection.update', async (update) => {
      const { connection, lastDisconnect, qr } = update;

      // Display QR code
      if (qr) {
        console.log('\n📱 Scan this QR code with WhatsApp:');
        qrcode.generate(qr, { small: true });
      }

      // Handle connection state changes
      if (connection === 'close') {
        this.isConnected = false;
        const shouldReconnect =
          (lastDisconnect?.error as Boom)?.output?.statusCode !== DisconnectReason.loggedOut;

        this.logger.info({ shouldReconnect }, 'Connection closed');

        if (shouldReconnect) {
          // Reconnect after 3 seconds
          this.scheduleReconnect();
        } else {
          this.logger.warn('Logged out from WhatsApp. Please scan QR code to reconnect.');
        }
      } else if (connection === 'open') {
        this.logger.info('✅ Connected to WhatsApp!');
        this.isConnected = true;

        // Clear any pending reconnect timeout
        if (this.reconnectTimeout) {
          clearTimeout(this.reconnectTimeout);
          this.reconnectTimeout = null;
        }

        // Set file permissions after successful connection
        this.setAuthFilePermissions();
      }
    });

    // Save credentials on update
    this.sock.ev.on('creds.update', async () => {
      await saveCreds();
      this.setAuthFilePermissions();
    });
  }

  /**
   * Schedule automatic reconnection after connection loss
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }

    this.reconnectTimeout = setTimeout(async () => {
      this.logger.info('Attempting to reconnect...');
      try {
        await this.connect();
      } catch (error) {
        this.logger.error({ error }, 'Reconnection failed');
        // Try again after delay
        this.scheduleReconnect();
      }
    }, 3000);
  }

  /**
   * Disconnect from WhatsApp
   */
  disconnect(): void {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.sock) {
      this.logger.info('Disconnecting from WhatsApp...');
      this.sock.end(undefined);
      this.sock = null;
    }

    this.isConnected = false;
  }

  /**
   * Check if connected to WhatsApp
   */
  getConnectionState(): boolean {
    return this.isConnected;
  }

  /**
   * Get the Baileys socket instance
   * Returns null if not connected
   */
  getSocket(): WASocket | null {
    return this.sock;
  }

  /**
   * Add event listener to Baileys socket
   */
  on(event: string, handler: (...args: any[]) => void): void {
    if (this.sock) {
      this.sock.ev.on(event as any, handler);
    } else {
      this.logger.warn(`Cannot add event handler for '${event}': Socket not initialized`);
    }
  }

  /**
   * Clean up resources
   */
  close(): void {
    this.disconnect();
  }
}
