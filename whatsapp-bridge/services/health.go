package services

import (
	"fmt"
	"time"
)

// HealthStatus represents the health status of the WhatsApp bridge
type HealthStatus struct {
	Status           string                 `json:"status"`             // "ok", "degraded", or "error"
	Backend          string                 `json:"backend"`            // "go"
	WhatsAppConnected bool                   `json:"whatsapp_connected"` // WhatsApp connection status
	DatabasePath     string                 `json:"database_path"`      // Path to messages database
	DatabaseOK       bool                   `json:"database_ok"`        // Database connectivity
	UptimeSeconds    int64                  `json:"uptime_seconds"`     // Service uptime
	Timestamp        time.Time              `json:"timestamp"`          // Current timestamp
	Details          map[string]interface{} `json:"details,omitempty"`  // Additional details
}

// HealthService provides health check functionality
type HealthService struct {
	startTime      time.Time
	whatsmeowClient *WhatsmeowClient
	database       *DatabaseService
}

// NewHealthService creates a new health service
func NewHealthService(whatsmeowClient *WhatsmeowClient, database *DatabaseService) *HealthService {
	return &HealthService{
		startTime:      time.Now(),
		whatsmeowClient: whatsmeowClient,
		database:       database,
	}
}

// GetHealthStatus returns the current health status
func (hs *HealthService) GetHealthStatus() HealthStatus {
	status := HealthStatus{
		Status:    "ok",
		Backend:   "go",
		Timestamp: time.Now(),
	}

	// Calculate uptime
	status.UptimeSeconds = int64(time.Since(hs.startTime).Seconds())

	// Check WhatsApp connection
	if hs.whatsmeowClient != nil {
		status.WhatsAppConnected = hs.whatsmeowClient.IsConnected()
	} else {
		status.WhatsAppConnected = false
	}

	// Check database
	if hs.database != nil {
		status.DatabasePath = hs.database.dbPath
		// Test database connectivity with a simple query
		err := hs.database.db.Ping()
		status.DatabaseOK = err == nil

		if err != nil {
			status.Status = "degraded"
			if status.Details == nil {
				status.Details = make(map[string]interface{})
			}
			status.Details["database_error"] = err.Error()
		}
	} else {
		status.DatabaseOK = false
		status.Status = "degraded"
	}

	// Determine overall status
	if !status.WhatsAppConnected {
		status.Status = "degraded"
	}

	if !status.DatabaseOK {
		status.Status = "error"
	}

	return status
}

// GetStatusCode returns the appropriate HTTP status code for the current health
func (hs *HealthService) GetStatusCode() int {
	health := hs.GetHealthStatus()

	switch health.Status {
	case "ok":
		return 200
	case "degraded":
		return 503
	case "error":
		return 503
	default:
		return 500
	}
}

// IsHealthy returns true if the service is healthy
func (hs *HealthService) IsHealthy() bool {
	health := hs.GetHealthStatus()
	return health.Status == "ok"
}

// GetReadinessStatus returns readiness status (similar to health, but more strict)
// A service is ready if it can handle requests
func (hs *HealthService) GetReadinessStatus() HealthStatus {
	status := hs.GetHealthStatus()

	// For readiness, we require WhatsApp connection
	if !status.WhatsAppConnected {
		status.Status = "error"
		if status.Details == nil {
			status.Details = make(map[string]interface{})
		}
		status.Details["readiness_check"] = "WhatsApp connection required"
	}

	return status
}

// GetLivenessStatus returns liveness status (is the service running?)
// This is a simpler check - just verify the service is responsive
func (hs *HealthService) GetLivenessStatus() HealthStatus {
	return HealthStatus{
		Status:        "ok",
		Backend:       "go",
		UptimeSeconds: int64(time.Since(hs.startTime).Seconds()),
		Timestamp:     time.Now(),
	}
}

// GetDetailedStatus returns detailed diagnostic information
func (hs *HealthService) GetDetailedStatus() map[string]interface{} {
	details := make(map[string]interface{})

	// Basic health
	health := hs.GetHealthStatus()
	details["health"] = health

	// WhatsApp details
	if hs.whatsmeowClient != nil {
		whatsappDetails := make(map[string]interface{})
		whatsappDetails["connected"] = hs.whatsmeowClient.IsConnected()
		whatsappDetails["auth_dir"] = hs.whatsmeowClient.authDir
		details["whatsapp"] = whatsappDetails
	}

	// Database details
	if hs.database != nil {
		dbDetails := make(map[string]interface{})
		dbDetails["path"] = hs.database.dbPath
		dbDetails["data_dir"] = hs.database.dataDir

		// Get counts
		chatCount, _ := hs.database.GetChatCount()
		messageCount, _ := hs.database.GetMessageCount()

		dbDetails["chats"] = chatCount
		dbDetails["messages"] = messageCount
		details["database"] = dbDetails
	}

	// Service info
	details["uptime_seconds"] = int64(time.Since(hs.startTime).Seconds())
	details["start_time"] = hs.startTime
	details["current_time"] = time.Now()

	return details
}

// Helper method to get counts from database
func (ds *DatabaseService) GetChatCount() (int, error) {
	var count int
	err := ds.db.QueryRow("SELECT COUNT(*) FROM chats").Scan(&count)
	return count, err
}

// Helper method to get message count from database
func (ds *DatabaseService) GetMessageCount() (int, error) {
	var count int
	err := ds.db.QueryRow("SELECT COUNT(*) FROM messages").Scan(&count)
	return count, err
}

// FormatUptime formats uptime as a human-readable string
func FormatUptime(seconds int64) string {
	duration := time.Duration(seconds) * time.Second

	days := int(duration.Hours() / 24)
	hours := int(duration.Hours()) % 24
	minutes := int(duration.Minutes()) % 60
	secs := int(duration.Seconds()) % 60

	if days > 0 {
		return fmt.Sprintf("%dd %dh %dm %ds", days, hours, minutes, secs)
	} else if hours > 0 {
		return fmt.Sprintf("%dh %dm %ds", hours, minutes, secs)
	} else if minutes > 0 {
		return fmt.Sprintf("%dm %ds", minutes, secs)
	}
	return fmt.Sprintf("%ds", secs)
}
