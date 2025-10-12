package services

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"time"

	_ "github.com/mattn/go-sqlite3"
	"go.mau.fi/whatsmeow"
)

// DatabaseConfig holds configuration for the database service
type DatabaseConfig struct {
	DataDir string // Directory for database file (default: data/)
	DBName  string // Database filename (default: messages.db)
}

// DatabaseService provides CRUD operations for WhatsApp message storage
type DatabaseService struct {
	db      *sql.DB
	dbPath  string
	dataDir string
}

// Chat represents a WhatsApp chat/conversation
type Chat struct {
	JID              string
	Name             string
	IsGroup          bool
	IsCommunity      bool
	IsBroadcast      bool
	IsNewsletter     bool
	ParentGroupJID   *string
	CreatedAt        time.Time
	UpdatedAt        time.Time
	AvatarURL        *string
	Description      *string
	ParticipantCount *int
	UnreadCount      int
}

// Message represents a WhatsApp message
type Message struct {
	ID               string
	ChatJID          string
	Timestamp        time.Time
	Sender           string
	FromMe           bool
	Content          *string
	MessageType      string
	PollData         *string
	MediaURL         *string
	Reactions        *string
	QuotedMessageID  *string
	SyncSource       string
	CreatedAt        time.Time
}

// SyncCheckpoint tracks history sync progress for a chat
type SyncCheckpoint struct {
	ChatJID         string
	LastMessageID   *string
	LastTimestamp   *time.Time
	MessagesSynced  int
	TotalEstimated  *int
	Status          string
	ErrorMessage    *string
	StartedAt       *time.Time
	UpdatedAt       time.Time
	CompletedAt     *time.Time
}

// NewDatabaseService creates and initializes a new database service
func NewDatabaseService(config DatabaseConfig) (*DatabaseService, error) {
	// Set defaults
	if config.DataDir == "" {
		config.DataDir = "data"
	}
	if config.DBName == "" {
		config.DBName = "messages.db"
	}

	// Create data directory with secure permissions (0700)
	if err := os.MkdirAll(config.DataDir, 0700); err != nil {
		return nil, fmt.Errorf("failed to create data directory: %w", err)
	}

	// Construct database path
	dbPath := fmt.Sprintf("file:%s/%s?_foreign_keys=on", config.DataDir, config.DBName)

	// Open database connection
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// Configure connection pool
	db.SetMaxOpenConns(25)
	db.SetMaxIdleConns(5)
	db.SetConnMaxLifetime(5 * time.Minute)

	// Test connection
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	service := &DatabaseService{
		db:      db,
		dbPath:  dbPath,
		dataDir: config.DataDir,
	}

	// Run migrations
	if err := RunMigrations(dbPath); err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to run migrations: %w", err)
	}

	return service, nil
}

// Close closes the database connection
func (ds *DatabaseService) Close() error {
	if ds.db != nil {
		return ds.db.Close()
	}
	return nil
}

// GetDB returns the underlying *sql.DB for advanced operations
func (ds *DatabaseService) GetDB() *sql.DB {
	return ds.db
}

// BeginTx starts a new transaction
func (ds *DatabaseService) BeginTx(ctx context.Context, opts *sql.TxOptions) (*sql.Tx, error) {
	return ds.db.BeginTx(ctx, opts)
}

// === Chat Operations ===

// StoreChat inserts or updates a chat in the database
func (ds *DatabaseService) StoreChat(chat *Chat) error {
	query := `
		INSERT INTO chats (jid, name, is_group, is_community, is_broadcast, is_newsletter,
			parent_group_jid, updated_at, avatar_url, description, participant_count, unread_count)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(jid) DO UPDATE SET
			name = excluded.name,
			is_group = excluded.is_group,
			is_community = excluded.is_community,
			is_broadcast = excluded.is_broadcast,
			is_newsletter = excluded.is_newsletter,
			parent_group_jid = excluded.parent_group_jid,
			updated_at = excluded.updated_at,
			avatar_url = excluded.avatar_url,
			description = excluded.description,
			participant_count = excluded.participant_count,
			unread_count = excluded.unread_count
	`

	_, err := ds.db.Exec(query,
		chat.JID, chat.Name, chat.IsGroup, chat.IsCommunity, chat.IsBroadcast, chat.IsNewsletter,
		chat.ParentGroupJID, time.Now().Unix(), chat.AvatarURL, chat.Description,
		chat.ParticipantCount, chat.UnreadCount,
	)

	return err
}

// GetChat retrieves a chat by JID
func (ds *DatabaseService) GetChat(jid string) (*Chat, error) {
	query := `
		SELECT jid, name, is_group, is_community, is_broadcast, is_newsletter,
			parent_group_jid, created_at, updated_at, avatar_url, description,
			participant_count, unread_count
		FROM chats
		WHERE jid = ?
	`

	var chat Chat
	var createdAt, updatedAt int64

	err := ds.db.QueryRow(query, jid).Scan(
		&chat.JID, &chat.Name, &chat.IsGroup, &chat.IsCommunity, &chat.IsBroadcast,
		&chat.IsNewsletter, &chat.ParentGroupJID, &createdAt, &updatedAt,
		&chat.AvatarURL, &chat.Description, &chat.ParticipantCount, &chat.UnreadCount,
	)

	if err != nil {
		return nil, err
	}

	chat.CreatedAt = time.Unix(createdAt, 0)
	chat.UpdatedAt = time.Unix(updatedAt, 0)

	return &chat, nil
}

// ListChats retrieves all chats, ordered by most recent update
func (ds *DatabaseService) ListChats(limit int) ([]*Chat, error) {
	query := `
		SELECT jid, name, is_group, is_community, is_broadcast, is_newsletter,
			parent_group_jid, created_at, updated_at, avatar_url, description,
			participant_count, unread_count
		FROM chats
		ORDER BY updated_at DESC
		LIMIT ?
	`

	rows, err := ds.db.Query(query, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var chats []*Chat
	for rows.Next() {
		var chat Chat
		var createdAt, updatedAt int64

		err := rows.Scan(
			&chat.JID, &chat.Name, &chat.IsGroup, &chat.IsCommunity, &chat.IsBroadcast,
			&chat.IsNewsletter, &chat.ParentGroupJID, &createdAt, &updatedAt,
			&chat.AvatarURL, &chat.Description, &chat.ParticipantCount, &chat.UnreadCount,
		)
		if err != nil {
			return nil, err
		}

		chat.CreatedAt = time.Unix(createdAt, 0)
		chat.UpdatedAt = time.Unix(updatedAt, 0)

		chats = append(chats, &chat)
	}

	return chats, rows.Err()
}

// GetCommunityGroups retrieves all groups belonging to a community
func (ds *DatabaseService) GetCommunityGroups(communityJID string) ([]*Chat, error) {
	query := `
		SELECT jid, name, is_group, is_community, is_broadcast, is_newsletter,
			parent_group_jid, created_at, updated_at, avatar_url, description,
			participant_count, unread_count
		FROM chats
		WHERE parent_group_jid = ?
		ORDER BY name
	`

	rows, err := ds.db.Query(query, communityJID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var groups []*Chat
	for rows.Next() {
		var chat Chat
		var createdAt, updatedAt int64

		err := rows.Scan(
			&chat.JID, &chat.Name, &chat.IsGroup, &chat.IsCommunity, &chat.IsBroadcast,
			&chat.IsNewsletter, &chat.ParentGroupJID, &createdAt, &updatedAt,
			&chat.AvatarURL, &chat.Description, &chat.ParticipantCount, &chat.UnreadCount,
		)
		if err != nil {
			return nil, err
		}

		chat.CreatedAt = time.Unix(createdAt, 0)
		chat.UpdatedAt = time.Unix(updatedAt, 0)

		groups = append(groups, &chat)
	}

	return groups, rows.Err()
}

// === Message Operations ===

// StoreMessage inserts or updates a message in the database
func (ds *DatabaseService) StoreMessage(msg *Message) error {
	query := `
		INSERT INTO messages (id, chat_jid, timestamp, sender, from_me, content,
			message_type, poll_data, media_url, reactions, quoted_message_id,
			sync_source, created_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(chat_jid, timestamp, id) DO UPDATE SET
			sender = excluded.sender,
			from_me = excluded.from_me,
			content = excluded.content,
			message_type = excluded.message_type,
			poll_data = excluded.poll_data,
			media_url = excluded.media_url,
			reactions = excluded.reactions,
			quoted_message_id = excluded.quoted_message_id,
			sync_source = excluded.sync_source
	`

	_, err := ds.db.Exec(query,
		msg.ID, msg.ChatJID, msg.Timestamp.Unix(), msg.Sender, msg.FromMe,
		msg.Content, msg.MessageType, msg.PollData, msg.MediaURL, msg.Reactions,
		msg.QuotedMessageID, msg.SyncSource, time.Now().Unix(),
	)

	return err
}

// GetMessages retrieves messages for a chat, ordered by most recent first
func (ds *DatabaseService) GetMessages(chatJID string, limit int) ([]*Message, error) {
	query := `
		SELECT id, chat_jid, timestamp, sender, from_me, content, message_type,
			poll_data, media_url, reactions, quoted_message_id, sync_source, created_at
		FROM messages
		WHERE chat_jid = ?
		ORDER BY timestamp DESC
		LIMIT ?
	`

	rows, err := ds.db.Query(query, chatJID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []*Message
	for rows.Next() {
		var msg Message
		var timestamp, createdAt int64

		err := rows.Scan(
			&msg.ID, &msg.ChatJID, &timestamp, &msg.Sender, &msg.FromMe,
			&msg.Content, &msg.MessageType, &msg.PollData, &msg.MediaURL,
			&msg.Reactions, &msg.QuotedMessageID, &msg.SyncSource, &createdAt,
		)
		if err != nil {
			return nil, err
		}

		msg.Timestamp = time.Unix(timestamp, 0)
		msg.CreatedAt = time.Unix(createdAt, 0)

		messages = append(messages, &msg)
	}

	return messages, rows.Err()
}

// GetMessageByID retrieves a specific message by ID and chat JID
func (ds *DatabaseService) GetMessageByID(chatJID, messageID string) (*Message, error) {
	query := `
		SELECT id, chat_jid, timestamp, sender, from_me, content, message_type,
			poll_data, media_url, reactions, quoted_message_id, sync_source, created_at
		FROM messages
		WHERE chat_jid = ? AND id = ?
	`

	var msg Message
	var timestamp, createdAt int64

	err := ds.db.QueryRow(query, chatJID, messageID).Scan(
		&msg.ID, &msg.ChatJID, &timestamp, &msg.Sender, &msg.FromMe,
		&msg.Content, &msg.MessageType, &msg.PollData, &msg.MediaURL,
		&msg.Reactions, &msg.QuotedMessageID, &msg.SyncSource, &createdAt,
	)

	if err != nil {
		return nil, err
	}

	msg.Timestamp = time.Unix(timestamp, 0)
	msg.CreatedAt = time.Unix(createdAt, 0)

	return &msg, nil
}

// === Sync Checkpoint Operations ===

// GetCheckpoint retrieves the sync checkpoint for a chat
func (ds *DatabaseService) GetCheckpoint(chatJID string) (*SyncCheckpoint, error) {
	query := `
		SELECT chat_jid, last_message_id, last_timestamp, messages_synced,
			total_estimated, status, error_message, started_at, updated_at, completed_at
		FROM sync_checkpoints
		WHERE chat_jid = ?
	`

	var cp SyncCheckpoint
	var lastTimestamp, startedAt, updatedAt, completedAt *int64

	err := ds.db.QueryRow(query, chatJID).Scan(
		&cp.ChatJID, &cp.LastMessageID, &lastTimestamp, &cp.MessagesSynced,
		&cp.TotalEstimated, &cp.Status, &cp.ErrorMessage, &startedAt,
		&updatedAt, &completedAt,
	)

	if err != nil {
		return nil, err
	}

	// Convert Unix timestamps to time.Time
	if lastTimestamp != nil {
		t := time.Unix(*lastTimestamp, 0)
		cp.LastTimestamp = &t
	}
	if startedAt != nil {
		t := time.Unix(*startedAt, 0)
		cp.StartedAt = &t
	}
	if updatedAt != nil {
		cp.UpdatedAt = time.Unix(*updatedAt, 0)
	}
	if completedAt != nil {
		t := time.Unix(*completedAt, 0)
		cp.CompletedAt = &t
	}

	return &cp, nil
}

// UpdateCheckpoint inserts or updates a sync checkpoint
func (ds *DatabaseService) UpdateCheckpoint(cp *SyncCheckpoint) error {
	query := `
		INSERT INTO sync_checkpoints (chat_jid, last_message_id, last_timestamp,
			messages_synced, total_estimated, status, error_message, started_at,
			updated_at, completed_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(chat_jid) DO UPDATE SET
			last_message_id = excluded.last_message_id,
			last_timestamp = excluded.last_timestamp,
			messages_synced = excluded.messages_synced,
			total_estimated = excluded.total_estimated,
			status = excluded.status,
			error_message = excluded.error_message,
			started_at = excluded.started_at,
			updated_at = excluded.updated_at,
			completed_at = excluded.completed_at
	`

	var lastTimestamp, startedAt, completedAt *int64
	if cp.LastTimestamp != nil {
		ts := cp.LastTimestamp.Unix()
		lastTimestamp = &ts
	}
	if cp.StartedAt != nil {
		ts := cp.StartedAt.Unix()
		startedAt = &ts
	}
	if cp.CompletedAt != nil {
		ts := cp.CompletedAt.Unix()
		completedAt = &ts
	}

	updatedAt := time.Now().Unix()

	_, err := ds.db.Exec(query,
		cp.ChatJID, cp.LastMessageID, lastTimestamp, cp.MessagesSynced,
		cp.TotalEstimated, cp.Status, cp.ErrorMessage, startedAt,
		updatedAt, completedAt,
	)

	return err
}

// ListCheckpoints retrieves all sync checkpoints, optionally filtered by status
func (ds *DatabaseService) ListCheckpoints(status string) ([]*SyncCheckpoint, error) {
	var query string
	var args []interface{}

	if status != "" {
		query = `
			SELECT chat_jid, last_message_id, last_timestamp, messages_synced,
				total_estimated, status, error_message, started_at, updated_at, completed_at
			FROM sync_checkpoints
			WHERE status = ?
			ORDER BY updated_at DESC
		`
		args = append(args, status)
	} else {
		query = `
			SELECT chat_jid, last_message_id, last_timestamp, messages_synced,
				total_estimated, status, error_message, started_at, updated_at, completed_at
			FROM sync_checkpoints
			ORDER BY updated_at DESC
		`
	}

	rows, err := ds.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var checkpoints []*SyncCheckpoint
	for rows.Next() {
		var cp SyncCheckpoint
		var lastTimestamp, startedAt, updatedAt, completedAt *int64

		err := rows.Scan(
			&cp.ChatJID, &cp.LastMessageID, &lastTimestamp, &cp.MessagesSynced,
			&cp.TotalEstimated, &cp.Status, &cp.ErrorMessage, &startedAt,
			&updatedAt, &completedAt,
		)
		if err != nil {
			return nil, err
		}

		// Convert Unix timestamps
		if lastTimestamp != nil {
			t := time.Unix(*lastTimestamp, 0)
			cp.LastTimestamp = &t
		}
		if startedAt != nil {
			t := time.Unix(*startedAt, 0)
			cp.StartedAt = &t
		}
		if updatedAt != nil {
			cp.UpdatedAt = time.Unix(*updatedAt, 0)
		}
		if completedAt != nil {
			t := time.Unix(*completedAt, 0)
			cp.CompletedAt = &t
		}

		checkpoints = append(checkpoints, &cp)
	}

	return checkpoints, rows.Err()
}

// === Batch Operations ===

// StoreMessagesInBatch stores multiple messages in a single transaction
func (ds *DatabaseService) StoreMessagesInBatch(messages []*Message) error {
	tx, err := ds.db.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	stmt, err := tx.Prepare(`
		INSERT INTO messages (id, chat_jid, timestamp, sender, from_me, content,
			message_type, poll_data, media_url, reactions, quoted_message_id,
			sync_source, created_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(chat_jid, timestamp, id) DO UPDATE SET
			sender = excluded.sender,
			from_me = excluded.from_me,
			content = excluded.content,
			message_type = excluded.message_type,
			poll_data = excluded.poll_data,
			media_url = excluded.media_url,
			reactions = excluded.reactions,
			quoted_message_id = excluded.quoted_message_id,
			sync_source = excluded.sync_source
	`)
	if err != nil {
		return fmt.Errorf("failed to prepare statement: %w", err)
	}
	defer stmt.Close()

	for _, msg := range messages {
		_, err := stmt.Exec(
			msg.ID, msg.ChatJID, msg.Timestamp.Unix(), msg.Sender, msg.FromMe,
			msg.Content, msg.MessageType, msg.PollData, msg.MediaURL, msg.Reactions,
			msg.QuotedMessageID, msg.SyncSource, time.Now().Unix(),
		)
		if err != nil {
			return fmt.Errorf("failed to execute statement: %w", err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit transaction: %w", err)
	}

	return nil
}

// === Contact Population (for compatibility with existing code) ===

// PopulateContacts fetches all contacts from WhatsApp and stores them in the chats table
func (ds *DatabaseService) PopulateContacts(client *whatsmeow.Client) error {
	contacts, err := client.Store.Contacts.GetAllContacts(context.Background())
	if err != nil {
		return fmt.Errorf("failed to get contacts: %w", err)
	}

	tx, err := ds.db.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	stmt, err := tx.Prepare(`
		INSERT INTO chats (jid, name, is_group, updated_at)
		VALUES (?, ?, 0, ?)
		ON CONFLICT(jid) DO UPDATE SET
			name = excluded.name,
			updated_at = excluded.updated_at
	`)
	if err != nil {
		return fmt.Errorf("failed to prepare statement: %w", err)
	}
	defer stmt.Close()

	count := 0
	for jid, contact := range contacts {
		name := contact.FullName
		if name == "" {
			name = jid.User
		}

		_, err := stmt.Exec(jid.String(), name, time.Now().Unix())
		if err != nil {
			return fmt.Errorf("failed to store contact %s: %w", jid.String(), err)
		}
		count++
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit transaction: %w", err)
	}

	fmt.Printf("Populated %d contacts into the database\n", count)
	return nil
}
