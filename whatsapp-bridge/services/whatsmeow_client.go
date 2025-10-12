package services

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"time"

	"github.com/mdp/qrterminal"
	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
)

// WhatsmeowClient wraps the whatsmeow client with connection management
type WhatsmeowClient struct {
	Client      *whatsmeow.Client
	Store       *sqlstore.Container
	Logger      waLog.Logger
	authDir     string
	connected   bool
}

// WhatsmeowConfig holds configuration for the whatsmeow client
type WhatsmeowConfig struct {
	AuthDir   string // Directory for authentication state (default: data/auth_go/)
	LogLevel  string // Log level: DEBUG, INFO, WARN, ERROR (default: INFO)
}

// NewWhatsmeowClient creates and initializes a new whatsmeow client
func NewWhatsmeowClient(config WhatsmeowConfig) (*WhatsmeowClient, error) {
	// Set defaults
	if config.AuthDir == "" {
		config.AuthDir = "data/auth_go"
	}
	if config.LogLevel == "" {
		config.LogLevel = "INFO"
	}

	// Create auth directory if it doesn't exist
	if err := os.MkdirAll(config.AuthDir, 0700); err != nil {
		return nil, fmt.Errorf("failed to create auth directory: %v", err)
	}

	// Set file permissions on auth directory to 700 (user read/write/execute only)
	if err := os.Chmod(config.AuthDir, 0700); err != nil {
		return nil, fmt.Errorf("failed to set auth directory permissions: %v", err)
	}

	// Create logger
	logger := waLog.Stdout("WhatsApp", config.LogLevel, true)

	// Create database path for session storage
	dbPath := fmt.Sprintf("file:%s/session.db?_foreign_keys=on", config.AuthDir)
	logger.Infof("Using auth database: %s", dbPath)

	// Create SQLite store container
	container, err := sqlstore.New(context.Background(), "sqlite3", dbPath, waLog.Stdout("Database", config.LogLevel, true))
	if err != nil {
		return nil, fmt.Errorf("failed to connect to session database: %v", err)
	}

	// Set file permissions on session.db to 600 (user read/write only)
	sessionDBFile := fmt.Sprintf("%s/session.db", config.AuthDir)
	if _, err := os.Stat(sessionDBFile); err == nil {
		if err := os.Chmod(sessionDBFile, 0600); err != nil {
			logger.Warnf("Failed to set session db permissions: %v", err)
		}
	}

	// Get device store - contains session information
	deviceStore, err := container.GetFirstDevice(context.Background())
	if err != nil {
		if err == sql.ErrNoRows {
			// No device exists, create one
			deviceStore = container.NewDevice()
			logger.Infof("Created new device")
		} else {
			return nil, fmt.Errorf("failed to get device: %v", err)
		}
	}

	// Create whatsmeow client instance
	client := whatsmeow.NewClient(deviceStore, logger)
	if client == nil {
		return nil, fmt.Errorf("failed to create WhatsApp client")
	}

	return &WhatsmeowClient{
		Client:    client,
		Store:     container,
		Logger:    logger,
		authDir:   config.AuthDir,
		connected: false,
	}, nil
}

// Connect establishes connection to WhatsApp servers
// Handles both QR code auth (new devices) and automatic reconnection (existing sessions)
func (wc *WhatsmeowClient) Connect() error {
	if wc.Client.Store.ID == nil {
		// No ID stored, this is a new client, need to pair with phone
		return wc.connectWithQR()
	}

	// Already logged in, just connect
	wc.Logger.Infof("Reconnecting with existing session...")
	err := wc.Client.Connect()
	if err != nil {
		return fmt.Errorf("failed to connect: %v", err)
	}

	// Wait for connection to stabilize
	time.Sleep(2 * time.Second)

	if !wc.Client.IsConnected() {
		return fmt.Errorf("failed to establish stable connection")
	}

	wc.connected = true
	wc.Logger.Infof("Successfully reconnected to WhatsApp")
	return nil
}

// connectWithQR handles QR code authentication for new devices
func (wc *WhatsmeowClient) connectWithQR() error {
	wc.Logger.Infof("New device - QR code authentication required")

	qrChan, _ := wc.Client.GetQRChannel(context.Background())
	err := wc.Client.Connect()
	if err != nil {
		return fmt.Errorf("failed to connect: %v", err)
	}

	// Track connection success
	connected := make(chan bool, 1)

	// Display QR codes
	go func() {
		for evt := range qrChan {
			if evt.Event == "code" {
				fmt.Println("\nScan this QR code with your WhatsApp app:")
				qrterminal.GenerateHalfBlock(evt.Code, qrterminal.L, os.Stdout)
			} else if evt.Event == "success" {
				connected <- true
			}
		}
	}()

	// Wait for connection with timeout
	select {
	case <-connected:
		wc.Logger.Infof("Successfully connected and authenticated!")
		wc.connected = true
		return nil
	case <-time.After(3 * time.Minute):
		wc.Disconnect()
		return fmt.Errorf("timeout waiting for QR code scan (3 minutes)")
	}
}

// Disconnect gracefully disconnects from WhatsApp
func (wc *WhatsmeowClient) Disconnect() {
	if wc.Client != nil {
		wc.Logger.Infof("Disconnecting from WhatsApp...")
		wc.Client.Disconnect()
		wc.connected = false
	}
}

// IsConnected returns true if the client is connected to WhatsApp
func (wc *WhatsmeowClient) IsConnected() bool {
	if wc.Client == nil {
		return false
	}
	return wc.Client.IsConnected()
}

// AddEventHandler registers an event handler for WhatsApp events
func (wc *WhatsmeowClient) AddEventHandler(handler func(interface{})) {
	wc.Client.AddEventHandler(handler)
}

// SetupDefaultHandlers configures default event handlers for connection management
func (wc *WhatsmeowClient) SetupDefaultHandlers() {
	wc.Client.AddEventHandler(func(evt interface{}) {
		switch v := evt.(type) {
		case *events.Connected:
			wc.Logger.Infof("Connected to WhatsApp")
			wc.connected = true

		case *events.Disconnected:
			wc.Logger.Warnf("Disconnected from WhatsApp")
			wc.connected = false

		case *events.LoggedOut:
			wc.Logger.Warnf("Device logged out, please scan QR code to log in again")
			wc.connected = false

		case *events.StreamError:
			wc.Logger.Errorf("Stream error: %v", v)
			// Attempt reconnection on stream errors
			if !wc.IsConnected() {
				wc.Logger.Infof("Attempting to reconnect...")
				go func() {
					time.Sleep(5 * time.Second)
					if err := wc.Connect(); err != nil {
						wc.Logger.Errorf("Reconnection failed: %v", err)
					}
				}()
			}
		}
	})
}

// Reconnect attempts to reconnect to WhatsApp after connection loss
func (wc *WhatsmeowClient) Reconnect() error {
	wc.Logger.Infof("Attempting to reconnect...")

	if wc.connected {
		wc.Disconnect()
		time.Sleep(2 * time.Second)
	}

	return wc.Connect()
}

// Close cleans up resources
func (wc *WhatsmeowClient) Close() error {
	wc.Disconnect()
	// Note: sqlstore.Container doesn't have a Close method
	// The underlying database connection is managed internally
	return nil
}
