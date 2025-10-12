import { DatabaseService } from './database.js';
import { BaileysClient } from './baileys_client.js';
export interface HealthStatus {
    status: 'ok' | 'degraded' | 'error';
    backend: string;
    whatsapp_connected: boolean;
    database_path: string;
    database_ok: boolean;
    uptime_seconds: number;
    timestamp: Date;
    details?: Record<string, any>;
}
export interface HealthServiceConfig {
    logLevel?: string;
}
/**
 * HealthService provides health check functionality for Baileys bridge
 */
export declare class HealthService {
    private startTime;
    private logger;
    private baileysClient?;
    private database?;
    constructor(config?: HealthServiceConfig);
    /**
     * Set the Baileys client (called after initialization)
     */
    setBaileysClient(client: BaileysClient): void;
    /**
     * Set the database service (called after initialization)
     */
    setDatabase(database: DatabaseService): void;
    /**
     * Get current health status
     */
    getHealthStatus(): HealthStatus;
    /**
     * Get HTTP status code based on health
     */
    getStatusCode(): number;
    /**
     * Check if service is healthy
     */
    isHealthy(): boolean;
    /**
     * Get readiness status (stricter than health - requires WhatsApp connection)
     */
    getReadinessStatus(): HealthStatus;
    /**
     * Get liveness status (simple check - is service running?)
     */
    getLivenessStatus(): HealthStatus;
    /**
     * Get detailed diagnostic information
     */
    getDetailedStatus(): Record<string, any>;
    /**
     * Get uptime in seconds
     */
    private getUptimeSeconds;
    /**
     * Format uptime as human-readable string
     */
    private formatUptime;
}
//# sourceMappingURL=health.d.ts.map