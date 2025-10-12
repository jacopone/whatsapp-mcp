import pino from 'pino';
/**
 * HealthService provides health check functionality for Baileys bridge
 */
export class HealthService {
    startTime;
    logger;
    baileysClient;
    database;
    constructor(config = {}) {
        this.startTime = new Date();
        this.logger = pino({ level: config.logLevel || 'info' });
    }
    /**
     * Set the Baileys client (called after initialization)
     */
    setBaileysClient(client) {
        this.baileysClient = client;
    }
    /**
     * Set the database service (called after initialization)
     */
    setDatabase(database) {
        this.database = database;
    }
    /**
     * Get current health status
     */
    getHealthStatus() {
        const status = {
            status: 'ok',
            backend: 'baileys',
            whatsapp_connected: false,
            database_path: '',
            database_ok: false,
            uptime_seconds: this.getUptimeSeconds(),
            timestamp: new Date()
        };
        // Check WhatsApp connection
        if (this.baileysClient) {
            status.whatsapp_connected = this.baileysClient.getConnectionState();
        }
        // Check database
        if (this.database) {
            try {
                // Test database with a simple query
                const stats = this.database.getStats();
                status.database_path = this.database['dbPath']; // Access private field for health check
                status.database_ok = true;
                // Add database stats to details
                status.details = {
                    database_stats: {
                        messages: stats.messages,
                        chats: stats.chats,
                        database_size: stats.databaseSize
                    }
                };
            }
            catch (error) {
                status.database_ok = false;
                status.status = 'degraded';
                status.details = {
                    database_error: String(error)
                };
            }
        }
        else {
            status.status = 'degraded';
        }
        // Determine overall status
        if (!status.whatsapp_connected) {
            status.status = 'degraded';
        }
        if (!status.database_ok) {
            status.status = 'error';
        }
        return status;
    }
    /**
     * Get HTTP status code based on health
     */
    getStatusCode() {
        const health = this.getHealthStatus();
        switch (health.status) {
            case 'ok':
                return 200;
            case 'degraded':
                return 503;
            case 'error':
                return 503;
            default:
                return 500;
        }
    }
    /**
     * Check if service is healthy
     */
    isHealthy() {
        const health = this.getHealthStatus();
        return health.status === 'ok';
    }
    /**
     * Get readiness status (stricter than health - requires WhatsApp connection)
     */
    getReadinessStatus() {
        const status = this.getHealthStatus();
        // For readiness, we require WhatsApp connection
        if (!status.whatsapp_connected) {
            status.status = 'error';
            if (!status.details) {
                status.details = {};
            }
            status.details.readiness_check = 'WhatsApp connection required';
        }
        return status;
    }
    /**
     * Get liveness status (simple check - is service running?)
     */
    getLivenessStatus() {
        return {
            status: 'ok',
            backend: 'baileys',
            whatsapp_connected: false,
            database_path: '',
            database_ok: false,
            uptime_seconds: this.getUptimeSeconds(),
            timestamp: new Date()
        };
    }
    /**
     * Get detailed diagnostic information
     */
    getDetailedStatus() {
        const details = {};
        // Basic health
        details.health = this.getHealthStatus();
        // WhatsApp details
        if (this.baileysClient) {
            details.whatsapp = {
                connected: this.baileysClient.getConnectionState(),
                auth_dir: 'data/auth_baileys' // Hardcoded for now
            };
        }
        // Database details
        if (this.database) {
            try {
                const stats = this.database.getStats();
                details.database = {
                    path: this.database['dbPath'],
                    stats: {
                        chats: stats.chats,
                        messages: stats.messages,
                        database_size: stats.databaseSize
                    },
                    sync_status: stats.syncStatus
                };
            }
            catch (error) {
                details.database = {
                    error: String(error)
                };
            }
        }
        // Service info
        details.uptime_seconds = this.getUptimeSeconds();
        details.uptime_formatted = this.formatUptime(this.getUptimeSeconds());
        details.start_time = this.startTime;
        details.current_time = new Date();
        return details;
    }
    /**
     * Get uptime in seconds
     */
    getUptimeSeconds() {
        return Math.floor((new Date().getTime() - this.startTime.getTime()) / 1000);
    }
    /**
     * Format uptime as human-readable string
     */
    formatUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m ${secs}s`;
        }
        else if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        }
        else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        }
        return `${secs}s`;
    }
}
//# sourceMappingURL=health.js.map