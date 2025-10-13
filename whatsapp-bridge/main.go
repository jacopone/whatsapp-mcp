package main

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math"
	"math/rand"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"reflect"
	"strconv"
	"strings"
	"syscall"
	"time"

	_ "github.com/mattn/go-sqlite3"
	"github.com/mdp/qrterminal"

	"go.mau.fi/whatsmeow"
	waProto "go.mau.fi/whatsmeow/binary/proto"
	"go.mau.fi/whatsmeow/store/sqlstore"
	"go.mau.fi/whatsmeow/types"
	"go.mau.fi/whatsmeow/types/events"
	waLog "go.mau.fi/whatsmeow/util/log"
	"google.golang.org/protobuf/proto"
)

// Message represents a chat message for our client
type Message struct {
	Time       time.Time
	Sender     string
	SenderName string
	Content    string
	IsFromMe   bool
	MediaType  string
	Filename   string
}

// Database handler for storing message history
type MessageStore struct {
	db *sql.DB
}

// Initialize message store
func NewMessageStore() (*MessageStore, error) {
	// Create directory for database if it doesn't exist
	if err := os.MkdirAll("store", 0755); err != nil {
		return nil, fmt.Errorf("failed to create store directory: %v", err)
	}

	// Open SQLite database for messages
	db, err := sql.Open("sqlite3", "file:store/messages.db?_foreign_keys=on")
	if err != nil {
		return nil, fmt.Errorf("failed to open message database: %v", err)
	}

	// Create tables if they don't exist
	_, err = db.Exec(`
		CREATE TABLE IF NOT EXISTS chats (
			jid TEXT PRIMARY KEY,
			name TEXT,
			last_message_time TIMESTAMP,
			parent_group_jid TEXT
		);

		CREATE TABLE IF NOT EXISTS contacts (
			jid TEXT PRIMARY KEY,
			name TEXT,
			phone_number TEXT
		);

		CREATE TABLE IF NOT EXISTS messages (
			id TEXT,
			chat_jid TEXT,
			sender TEXT,
			content TEXT,
			timestamp TIMESTAMP,
			is_from_me BOOLEAN,
			is_read BOOLEAN DEFAULT 0,
			read_timestamp TIMESTAMP,
			media_type TEXT,
			filename TEXT,
			url TEXT,
			media_key BLOB,
			file_sha256 BLOB,
			file_enc_sha256 BLOB,
			file_length INTEGER,
			PRIMARY KEY (id, chat_jid),
			FOREIGN KEY (chat_jid) REFERENCES chats(jid)
		);
	`)
	if err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to create tables: %v", err)
	}

	// Add is_read column to existing database (migration)
	_, _ = db.Exec(`ALTER TABLE messages ADD COLUMN is_read BOOLEAN DEFAULT 0`)
	_, _ = db.Exec(`ALTER TABLE messages ADD COLUMN read_timestamp TIMESTAMP`)

	// Update existing messages: mark outgoing as read, incoming as unread
	_, _ = db.Exec(`UPDATE messages SET is_read = CASE WHEN is_from_me = 1 THEN 1 ELSE 0 END WHERE is_read IS NULL`)

	// Create performance indexes
	_, err = db.Exec(`
		CREATE INDEX IF NOT EXISTS idx_messages_chat_timestamp
		ON messages(chat_jid, timestamp DESC);

		CREATE INDEX IF NOT EXISTS idx_messages_unread
		ON messages(chat_jid, is_read, timestamp DESC);
	`)
	if err != nil {
		db.Close()
		return nil, fmt.Errorf("failed to create index: %v", err)
	}

	return &MessageStore{db: db}, nil
}

// Close the database connection
func (store *MessageStore) Close() error {
	return store.db.Close()
}

// Store a chat in the database
func (store *MessageStore) StoreChat(jid, name string, lastMessageTime time.Time) error {
	_, err := store.db.Exec(
		"INSERT OR REPLACE INTO chats (jid, name, last_message_time) VALUES (?, ?, ?)",
		jid, name, lastMessageTime,
	)
	return err
}

// Store a chat with parent group JID in the database
func (store *MessageStore) StoreChatWithParent(jid, name string, lastMessageTime time.Time, parentGroupJID string) error {
	_, err := store.db.Exec(
		"INSERT OR REPLACE INTO chats (jid, name, last_message_time, parent_group_jid) VALUES (?, ?, ?, ?)",
		jid, name, lastMessageTime, parentGroupJID,
	)
	return err
}

// Store a message in the database
func (store *MessageStore) StoreMessage(id, chatJID, sender, content string, timestamp time.Time, isFromMe bool,
	mediaType, filename, url string, mediaKey, fileSHA256, fileEncSHA256 []byte, fileLength uint64) error {
	// Only store if there's actual content or media
	if content == "" && mediaType == "" {
		return nil
	}

	// Outgoing messages are automatically marked as read
	isRead := isFromMe

	_, err := store.db.Exec(
		`INSERT OR REPLACE INTO messages
		(id, chat_jid, sender, content, timestamp, is_from_me, is_read, media_type, filename, url, media_key, file_sha256, file_enc_sha256, file_length)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		id, chatJID, sender, content, timestamp, isFromMe, isRead, mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength,
	)
	return err
}

// PopulateContacts fetches all contacts from WhatsApp and stores them in the database
func (store *MessageStore) PopulateContacts(client *whatsmeow.Client) error {
	contacts, err := client.Store.Contacts.GetAllContacts(context.Background())
	if err != nil {
		return fmt.Errorf("failed to get contacts: %v", err)
	}

	for jid, contact := range contacts {
		phoneNumber := jid.User
		name := contact.FullName
		if name == "" {
			name = phoneNumber
		}

		_, err := store.db.Exec(
			"INSERT OR REPLACE INTO contacts (jid, name, phone_number) VALUES (?, ?, ?)",
			jid.String(), name, phoneNumber,
		)
		if err != nil {
			return fmt.Errorf("failed to store contact %s: %v", jid.String(), err)
		}
	}

	fmt.Printf("Populated %d contacts into the database\n", len(contacts))
	return nil
}

// Get messages from a chat
func (store *MessageStore) GetMessages(chatJID string, limit int) ([]Message, error) {
	rows, err := store.db.Query(
		`SELECT m.sender, COALESCE(c.name, m.sender) as sender_name, m.content, m.timestamp, m.is_from_me, m.media_type, m.filename
		FROM messages m
		LEFT JOIN contacts c ON (
			-- Handle different sender formats
			CASE
				-- If sender has @ symbol, extract the number part for comparison
				WHEN INSTR(m.sender, '@') > 0 THEN
					SUBSTR(m.sender, 1, INSTR(m.sender, '@') - 1) = SUBSTR(c.jid, 1, INSTR(c.jid, '@') - 1)
				-- If sender is plain number, match with the number part of contact JID
				ELSE
					m.sender = SUBSTR(c.jid, 1, INSTR(c.jid, '@') - 1)
			END
		)
		WHERE m.chat_jid = ?
		ORDER BY m.timestamp DESC
		LIMIT ?`,
		chatJID, limit,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []Message
	for rows.Next() {
		var msg Message
		var timestamp time.Time
		err := rows.Scan(&msg.Sender, &msg.SenderName, &msg.Content, &timestamp, &msg.IsFromMe, &msg.MediaType, &msg.Filename)
		if err != nil {
			return nil, err
		}
		msg.Time = timestamp
		messages = append(messages, msg)
	}

	return messages, nil
}

// Get all chats
func (store *MessageStore) GetChats() (map[string]time.Time, error) {
	rows, err := store.db.Query("SELECT jid, last_message_time FROM chats ORDER BY last_message_time DESC")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	chats := make(map[string]time.Time)
	for rows.Next() {
		var jid string
		var lastMessageTime time.Time
		err := rows.Scan(&jid, &lastMessageTime)
		if err != nil {
			return nil, err
		}
		chats[jid] = lastMessageTime
	}

	return chats, nil
}

// QueryMessages queries messages with various filters
func (store *MessageStore) QueryMessages(req QueryMessagesRequest) ([]MessageResult, int, error) {
	// Build dynamic query
	query := `
		SELECT m.id, m.chat_jid, COALESCE(ch.name, m.chat_jid) as chat_name,
		       m.sender,
		       COALESCE(
		           -- Try to get the name from any contact with matching number
		           (SELECT name FROM contacts c2
		            WHERE SUBSTR(m.sender, 1, INSTR(m.sender, '@') - 1) = SUBSTR(c2.jid, 1, INSTR(c2.jid, '@') - 1)
		              AND c2.name != c2.phone_number
		            LIMIT 1),
		           -- Otherwise use the direct match
		           c.name,
		           -- Fallback to sender
		           m.sender
		       ) as sender_name,
		       m.content, m.timestamp, m.is_from_me, m.media_type, m.filename
		FROM messages m
		LEFT JOIN chats ch ON m.chat_jid = ch.jid
		LEFT JOIN contacts c ON (
			-- Handle different sender formats
			CASE
				-- If sender has @ symbol, extract the number part for comparison
				WHEN INSTR(m.sender, '@') > 0 THEN
					SUBSTR(m.sender, 1, INSTR(m.sender, '@') - 1) = SUBSTR(c.jid, 1, INSTR(c.jid, '@') - 1)
				-- If sender is plain number, match with the number part of contact JID
				ELSE
					m.sender = SUBSTR(c.jid, 1, INSTR(c.jid, '@') - 1)
			END
		)
		WHERE 1=1
	`
	countQuery := "SELECT COUNT(*) FROM messages m WHERE 1=1"

	args := []interface{}{}
	countArgs := []interface{}{}

	// Add filters
	if req.ChatJID != "" {
		query += " AND m.chat_jid = ?"
		countQuery += " AND m.chat_jid = ?"
		args = append(args, req.ChatJID)
		countArgs = append(countArgs, req.ChatJID)
	}

	if req.Sender != "" {
		query += " AND m.sender LIKE ?"
		countQuery += " AND m.sender LIKE ?"
		senderPattern := "%" + req.Sender + "%"
		args = append(args, senderPattern)
		countArgs = append(countArgs, senderPattern)
	}

	if req.Content != "" {
		query += " AND m.content LIKE ?"
		countQuery += " AND m.content LIKE ?"
		contentPattern := "%" + req.Content + "%"
		args = append(args, contentPattern)
		countArgs = append(countArgs, contentPattern)
	}

	// Add default time filter for recent messages (last 7 days) if no time filters provided
	if req.AfterTime == "" && req.BeforeTime == "" {
		sevenDaysAgo := time.Now().AddDate(0, 0, -7)
		query += " AND m.timestamp > ?"
		countQuery += " AND m.timestamp > ?"
		args = append(args, sevenDaysAgo)
		countArgs = append(countArgs, sevenDaysAgo)
	}

	if req.AfterTime != "" {
		afterTime, err := time.Parse(time.RFC3339, req.AfterTime)
		if err == nil {
			query += " AND m.timestamp > ?"
			countQuery += " AND m.timestamp > ?"
			args = append(args, afterTime)
			countArgs = append(countArgs, afterTime)
		}
	}

	if req.BeforeTime != "" {
		beforeTime, err := time.Parse(time.RFC3339, req.BeforeTime)
		if err == nil {
			query += " AND m.timestamp < ?"
			countQuery += " AND m.timestamp < ?"
			args = append(args, beforeTime)
			countArgs = append(countArgs, beforeTime)
		}
	}

	if !req.IncludeMedia {
		query += " AND (m.media_type IS NULL OR m.media_type = '')"
		countQuery += " AND (m.media_type IS NULL OR m.media_type = '')"
	} else if req.MediaTypeFilter != "" {
		query += " AND m.media_type = ?"
		countQuery += " AND m.media_type = ?"
		args = append(args, req.MediaTypeFilter)
		countArgs = append(countArgs, req.MediaTypeFilter)
	}

	// Get total count (skip for first page to improve performance)
	var total int
	if req.Offset > 0 {
		// Only count when paginating beyond first page
		err := store.db.QueryRow(countQuery, countArgs...).Scan(&total)
		if err != nil {
			return nil, 0, err
		}
	} else {
		// Return -1 for first page (indicates count not computed)
		total = -1
	}

	// Add ordering and pagination
	query += " ORDER BY m.timestamp DESC"

	if req.Limit > 0 {
		query += " LIMIT ?"
		args = append(args, req.Limit)
	} else {
		query += " LIMIT 100" // Default limit
	}

	if req.Offset > 0 {
		query += " OFFSET ?"
		args = append(args, req.Offset)
	}

	// Execute query
	rows, err := store.db.Query(query, args...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var messages []MessageResult
	for rows.Next() {
		var msg MessageResult
		var mediaType, filename sql.NullString

		err := rows.Scan(
			&msg.ID, &msg.ChatJID, &msg.ChatName,
			&msg.Sender, &msg.SenderName,
			&msg.Content, &msg.Timestamp, &msg.IsFromMe,
			&mediaType, &filename,
		)
		if err != nil {
			return nil, 0, err
		}

		if mediaType.Valid {
			msg.MediaType = mediaType.String
		}
		if filename.Valid {
			msg.Filename = filename.String
		}

		messages = append(messages, msg)
	}

	return messages, total, nil
}

// GetMessageStats returns statistics about stored messages
func (store *MessageStore) GetMessageStats() (MessageStatsResponse, error) {
	stats := MessageStatsResponse{
		Success:        true,
		MessagesByType: make(map[string]int),
	}

	// Get total messages
	err := store.db.QueryRow("SELECT COUNT(*) FROM messages").Scan(&stats.TotalMessages)
	if err != nil {
		return stats, err
	}

	// Get total chats
	err = store.db.QueryRow("SELECT COUNT(*) FROM chats").Scan(&stats.TotalChats)
	if err != nil {
		return stats, err
	}

	// Get total contacts
	err = store.db.QueryRow("SELECT COUNT(*) FROM contacts").Scan(&stats.TotalContacts)
	if err != nil {
		return stats, err
	}

	// Get media vs text messages
	err = store.db.QueryRow("SELECT COUNT(*) FROM messages WHERE media_type IS NOT NULL AND media_type != ''").Scan(&stats.MediaMessages)
	if err != nil {
		return stats, err
	}
	stats.TextMessages = stats.TotalMessages - stats.MediaMessages

	// Get messages by type
	rows, err := store.db.Query("SELECT media_type, COUNT(*) FROM messages WHERE media_type IS NOT NULL AND media_type != '' GROUP BY media_type")
	if err != nil {
		return stats, err
	}
	defer rows.Close()

	for rows.Next() {
		var mediaType string
		var count int
		if err := rows.Scan(&mediaType, &count); err == nil {
			stats.MessagesByType[mediaType] = count
		}
	}

	// Get oldest and newest message timestamps
	var oldestTimeStr, newestTimeStr sql.NullString
	err = store.db.QueryRow("SELECT MIN(timestamp), MAX(timestamp) FROM messages").Scan(&oldestTimeStr, &newestTimeStr)
	if err != nil && err != sql.ErrNoRows {
		return stats, err
	}

	// Only set timestamps if they're valid (not NULL) and parse them
	// SQLite stores timestamps as "2006-01-02 15:04:05-07:00" format
	timestampFormat := "2006-01-02 15:04:05-07:00"
	if oldestTimeStr.Valid && oldestTimeStr.String != "" {
		if t, err := time.Parse(timestampFormat, oldestTimeStr.String); err == nil {
			stats.OldestMessage = t
		}
	}
	if newestTimeStr.Valid && newestTimeStr.String != "" {
		if t, err := time.Parse(timestampFormat, newestTimeStr.String); err == nil {
			stats.NewestMessage = t
		}
	}

	return stats, nil
}

// Extract text content from a message
func extractTextContent(msg *waProto.Message) string {
	if msg == nil {
		return ""
	}

	// Try to get text content
	if text := msg.GetConversation(); text != "" {
		return text
	} else if extendedText := msg.GetExtendedTextMessage(); extendedText != nil {
		return extendedText.GetText()
	}

	// For now, we're ignoring non-text messages
	return ""
}

// SendMessageResponse represents the response for the send message API
type SendMessageResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// SendMessageRequest represents the request body for the send message API
type SendMessageRequest struct {
	Recipient string `json:"recipient"`
	Message   string `json:"message"`
	MediaPath string `json:"media_path,omitempty"`
}

// Function to send a WhatsApp message
func sendWhatsAppMessage(client *whatsmeow.Client, recipient string, message string, mediaPath string) (bool, string) {
	if !client.IsConnected() {
		return false, "Not connected to WhatsApp"
	}

	// Create JID for recipient
	var recipientJID types.JID
	var err error

	// Check if recipient is a JID
	isJID := strings.Contains(recipient, "@")

	if isJID {
		// Parse the JID string
		recipientJID, err = types.ParseJID(recipient)
		if err != nil {
			return false, fmt.Sprintf("Error parsing JID: %v", err)
		}
	} else {
		// Create JID from phone number
		recipientJID = types.JID{
			User:   recipient,
			Server: "s.whatsapp.net", // For personal chats
		}
	}

	msg := &waProto.Message{}

	// Check if we have media to send
	if mediaPath != "" {
		// Read media file
		mediaData, err := os.ReadFile(mediaPath)
		if err != nil {
			return false, fmt.Sprintf("Error reading media file: %v", err)
		}

		// Determine media type and mime type based on file extension
		fileExt := strings.ToLower(mediaPath[strings.LastIndex(mediaPath, ".")+1:])
		var mediaType whatsmeow.MediaType
		var mimeType string

		// Handle different media types
		switch fileExt {
		// Image types
		case "jpg", "jpeg":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/jpeg"
		case "png":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/png"
		case "gif":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/gif"
		case "webp":
			mediaType = whatsmeow.MediaImage
			mimeType = "image/webp"

		// Audio types
		case "ogg":
			mediaType = whatsmeow.MediaAudio
			mimeType = "audio/ogg; codecs=opus"

		// Video types
		case "mp4":
			mediaType = whatsmeow.MediaVideo
			mimeType = "video/mp4"
		case "avi":
			mediaType = whatsmeow.MediaVideo
			mimeType = "video/avi"
		case "mov":
			mediaType = whatsmeow.MediaVideo
			mimeType = "video/quicktime"

		// Document types (for any other file type)
		default:
			mediaType = whatsmeow.MediaDocument
			mimeType = "application/octet-stream"
		}

		// Upload media to WhatsApp servers
		resp, err := client.Upload(context.Background(), mediaData, mediaType)
		if err != nil {
			return false, fmt.Sprintf("Error uploading media: %v", err)
		}

		fmt.Println("Media uploaded", resp)

		// Create the appropriate message type based on media type
		switch mediaType {
		case whatsmeow.MediaImage:
			msg.ImageMessage = &waProto.ImageMessage{
				Caption:       proto.String(message),
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
			}
		case whatsmeow.MediaAudio:
			// Handle ogg audio files
			var seconds uint32 = 30 // Default fallback
			var waveform []byte = nil

			// Try to analyze the ogg file
			if strings.Contains(mimeType, "ogg") {
				analyzedSeconds, analyzedWaveform, err := analyzeOggOpus(mediaData)
				if err == nil {
					seconds = analyzedSeconds
					waveform = analyzedWaveform
				} else {
					return false, fmt.Sprintf("Failed to analyze Ogg Opus file: %v", err)
				}
			} else {
				fmt.Printf("Not an Ogg Opus file: %s\n", mimeType)
			}

			msg.AudioMessage = &waProto.AudioMessage{
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
				Seconds:       proto.Uint32(seconds),
				PTT:           proto.Bool(true),
				Waveform:      waveform,
			}
		case whatsmeow.MediaVideo:
			msg.VideoMessage = &waProto.VideoMessage{
				Caption:       proto.String(message),
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
			}
		case whatsmeow.MediaDocument:
			msg.DocumentMessage = &waProto.DocumentMessage{
				Title:         proto.String(mediaPath[strings.LastIndex(mediaPath, "/")+1:]),
				Caption:       proto.String(message),
				Mimetype:      proto.String(mimeType),
				URL:           &resp.URL,
				DirectPath:    &resp.DirectPath,
				MediaKey:      resp.MediaKey,
				FileEncSHA256: resp.FileEncSHA256,
				FileSHA256:    resp.FileSHA256,
				FileLength:    &resp.FileLength,
			}
		}
	} else {
		msg.Conversation = proto.String(message)
	}

	// Send message
	_, err = client.SendMessage(context.Background(), recipientJID, msg)

	if err != nil {
		return false, fmt.Sprintf("Error sending message: %v", err)
	}

	return true, fmt.Sprintf("Message sent to %s", recipient)
}

// Extract media info from a message
func extractMediaInfo(msg *waProto.Message) (mediaType string, filename string, url string, mediaKey []byte, fileSHA256 []byte, fileEncSHA256 []byte, fileLength uint64) {
	if msg == nil {
		return "", "", "", nil, nil, nil, 0
	}

	// Check for image message
	if img := msg.GetImageMessage(); img != nil {
		return "image", "image_" + time.Now().Format("20060102_150405") + ".jpg",
			img.GetURL(), img.GetMediaKey(), img.GetFileSHA256(), img.GetFileEncSHA256(), img.GetFileLength()
	}

	// Check for video message
	if vid := msg.GetVideoMessage(); vid != nil {
		return "video", "video_" + time.Now().Format("20060102_150405") + ".mp4",
			vid.GetURL(), vid.GetMediaKey(), vid.GetFileSHA256(), vid.GetFileEncSHA256(), vid.GetFileLength()
	}

	// Check for audio message
	if aud := msg.GetAudioMessage(); aud != nil {
		return "audio", "audio_" + time.Now().Format("20060102_150405") + ".ogg",
			aud.GetURL(), aud.GetMediaKey(), aud.GetFileSHA256(), aud.GetFileEncSHA256(), aud.GetFileLength()
	}

	// Check for document message
	if doc := msg.GetDocumentMessage(); doc != nil {
		filename := doc.GetFileName()
		if filename == "" {
			filename = "document_" + time.Now().Format("20060102_150405")
		}
		return "document", filename,
			doc.GetURL(), doc.GetMediaKey(), doc.GetFileSHA256(), doc.GetFileEncSHA256(), doc.GetFileLength()
	}

	return "", "", "", nil, nil, nil, 0
}

// Handle regular incoming messages with media support
func handleMessage(client *whatsmeow.Client, messageStore *MessageStore, msg *events.Message, logger waLog.Logger) {
	// Save message to database
	chatJID := msg.Info.Chat.String()
	// CRITICAL FIX: Store full sender JID (with @lid or @s.whatsapp.net), not just User part
	// This ensures mark-as-read can properly parse the sender JID
	sender := msg.Info.Sender.String()

	// Get appropriate chat name (pass nil for conversation since we don't have one for regular messages)
	// Pass just User part for backwards compatibility with GetChatName
	name := GetChatName(client, messageStore, msg.Info.Chat, chatJID, nil, msg.Info.Sender.User, logger)

	// Update chat in database with the message timestamp (keeps last message time updated)
	err := messageStore.StoreChat(chatJID, name, msg.Info.Timestamp)
	if err != nil {
		logger.Warnf("Failed to store chat: %v", err)
	}

	// Extract text content
	content := extractTextContent(msg.Message)

	// Extract media info
	mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength := extractMediaInfo(msg.Message)

	// Skip if there's no content and no media
	if content == "" && mediaType == "" {
		return
	}

	// Store message in database
	err = messageStore.StoreMessage(
		msg.Info.ID,
		chatJID,
		sender,
		content,
		msg.Info.Timestamp,
		msg.Info.IsFromMe,
		mediaType,
		filename,
		url,
		mediaKey,
		fileSHA256,
		fileEncSHA256,
		fileLength,
	)

	if err != nil {
		logger.Warnf("Failed to store message: %v", err)
	} else {
		// Log message reception
		timestamp := msg.Info.Timestamp.Format("2006-01-02 15:04:05")
		direction := "←"
		if msg.Info.IsFromMe {
			direction = "→"
		}

		// Log based on message type
		if mediaType != "" {
			fmt.Printf("[%s] %s %s: [%s: %s] %s\n", timestamp, direction, sender, mediaType, filename, content)
		} else if content != "" {
			fmt.Printf("[%s] %s %s: %s\n", timestamp, direction, sender, content)
		}
	}
}

// DownloadMediaRequest represents the request body for the download media API
type DownloadMediaRequest struct {
	MessageID string `json:"message_id"`
	ChatJID   string `json:"chat_jid"`
}

// DownloadMediaResponse represents the response for the download media API
type DownloadMediaResponse struct {
	Success  bool   `json:"success"`
	Message  string `json:"message"`
	Filename string `json:"filename,omitempty"`
	Path     string `json:"path,omitempty"`
}

// MarkAsReadRequest represents the request body for marking messages as read
type MarkAsReadRequest struct {
	ChatJID    string   `json:"chat_jid"`
	MessageIDs []string `json:"message_ids"`
	Sender     string   `json:"sender"`
}

// MarkAsReadResponse represents the response for the mark as read API
type MarkAsReadResponse struct {
	Success   bool   `json:"success"`
	Message   string `json:"message"`
	Count     int    `json:"count"`               // Number of messages marked as read
	ErrorCode string `json:"error_code,omitempty"` // Machine-readable error code (Phase 2: T006)
}

// Store additional media info in the database
func (store *MessageStore) StoreMediaInfo(id, chatJID, url string, mediaKey, fileSHA256, fileEncSHA256 []byte, fileLength uint64) error {
	_, err := store.db.Exec(
		"UPDATE messages SET url = ?, media_key = ?, file_sha256 = ?, file_enc_sha256 = ?, file_length = ? WHERE id = ? AND chat_jid = ?",
		url, mediaKey, fileSHA256, fileEncSHA256, fileLength, id, chatJID,
	)
	return err
}

// Get media info from the database
func (store *MessageStore) GetMediaInfo(id, chatJID string) (string, string, string, []byte, []byte, []byte, uint64, error) {
	var mediaType, filename, url string
	var mediaKey, fileSHA256, fileEncSHA256 []byte
	var fileLength uint64

	err := store.db.QueryRow(
		"SELECT media_type, filename, url, media_key, file_sha256, file_enc_sha256, file_length FROM messages WHERE id = ? AND chat_jid = ?",
		id, chatJID,
	).Scan(&mediaType, &filename, &url, &mediaKey, &fileSHA256, &fileEncSHA256, &fileLength)

	return mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength, err
}

// MediaDownloader implements the whatsmeow.DownloadableMessage interface
type MediaDownloader struct {
	URL           string
	DirectPath    string
	MediaKey      []byte
	FileLength    uint64
	FileSHA256    []byte
	FileEncSHA256 []byte
	MediaType     whatsmeow.MediaType
}

// GetDirectPath implements the DownloadableMessage interface
func (d *MediaDownloader) GetDirectPath() string {
	return d.DirectPath
}

// GetURL implements the DownloadableMessage interface
func (d *MediaDownloader) GetURL() string {
	return d.URL
}

// GetMediaKey implements the DownloadableMessage interface
func (d *MediaDownloader) GetMediaKey() []byte {
	return d.MediaKey
}

// GetFileLength implements the DownloadableMessage interface
func (d *MediaDownloader) GetFileLength() uint64 {
	return d.FileLength
}

// GetFileSHA256 implements the DownloadableMessage interface
func (d *MediaDownloader) GetFileSHA256() []byte {
	return d.FileSHA256
}

// GetFileEncSHA256 implements the DownloadableMessage interface
func (d *MediaDownloader) GetFileEncSHA256() []byte {
	return d.FileEncSHA256
}

// GetMediaType implements the DownloadableMessage interface
func (d *MediaDownloader) GetMediaType() whatsmeow.MediaType {
	return d.MediaType
}

// Function to download media from a message
func downloadMedia(client *whatsmeow.Client, messageStore *MessageStore, messageID, chatJID string) (bool, string, string, string, error) {
	// Query the database for the message
	var mediaType, filename, url string
	var mediaKey, fileSHA256, fileEncSHA256 []byte
	var fileLength uint64
	var err error

	// First, check if we already have this file
	chatDir := fmt.Sprintf("store/%s", strings.ReplaceAll(chatJID, ":", "_"))
	localPath := ""

	// Get media info from the database
	mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength, err = messageStore.GetMediaInfo(messageID, chatJID)

	if err != nil {
		// Try to get basic info if extended info isn't available
		err = messageStore.db.QueryRow(
			"SELECT media_type, filename FROM messages WHERE id = ? AND chat_jid = ?",
			messageID, chatJID,
		).Scan(&mediaType, &filename)

		if err != nil {
			return false, "", "", "", fmt.Errorf("failed to find message: %v", err)
		}
	}

	// Check if this is a media message
	if mediaType == "" {
		return false, "", "", "", fmt.Errorf("not a media message")
	}

	// Create directory for the chat if it doesn't exist
	if err := os.MkdirAll(chatDir, 0755); err != nil {
		return false, "", "", "", fmt.Errorf("failed to create chat directory: %v", err)
	}

	// Generate a local path for the file
	localPath = fmt.Sprintf("%s/%s", chatDir, filename)

	// Get absolute path
	absPath, err := filepath.Abs(localPath)
	if err != nil {
		return false, "", "", "", fmt.Errorf("failed to get absolute path: %v", err)
	}

	// Check if file already exists
	if _, err := os.Stat(localPath); err == nil {
		// File exists, return it
		return true, mediaType, filename, absPath, nil
	}

	// If we don't have all the media info we need, we can't download
	if url == "" || len(mediaKey) == 0 || len(fileSHA256) == 0 || len(fileEncSHA256) == 0 || fileLength == 0 {
		return false, "", "", "", fmt.Errorf("incomplete media information for download")
	}

	fmt.Printf("Attempting to download media for message %s in chat %s...\n", messageID, chatJID)

	// Extract direct path from URL
	directPath := extractDirectPathFromURL(url)

	// Create a downloader that implements DownloadableMessage
	var waMediaType whatsmeow.MediaType
	switch mediaType {
	case "image":
		waMediaType = whatsmeow.MediaImage
	case "video":
		waMediaType = whatsmeow.MediaVideo
	case "audio":
		waMediaType = whatsmeow.MediaAudio
	case "document":
		waMediaType = whatsmeow.MediaDocument
	default:
		return false, "", "", "", fmt.Errorf("unsupported media type: %s", mediaType)
	}

	downloader := &MediaDownloader{
		URL:           url,
		DirectPath:    directPath,
		MediaKey:      mediaKey,
		FileLength:    fileLength,
		FileSHA256:    fileSHA256,
		FileEncSHA256: fileEncSHA256,
		MediaType:     waMediaType,
	}

	// Download the media using whatsmeow client
	mediaData, err := client.Download(context.Background(), downloader)
	if err != nil {
		return false, "", "", "", fmt.Errorf("failed to download media: %v", err)
	}

	// Save the downloaded media to file
	if err := os.WriteFile(localPath, mediaData, 0644); err != nil {
		return false, "", "", "", fmt.Errorf("failed to save media file: %v", err)
	}

	fmt.Printf("Successfully downloaded %s media to %s (%d bytes)\n", mediaType, absPath, len(mediaData))
	return true, mediaType, filename, absPath, nil
}

// MessageWithTimestamp represents a message ID with its timestamp
type MessageWithTimestamp struct {
	ID        string
	Timestamp time.Time
}

// Query all message IDs for a chat (Phase 3: T008)
// Returns message IDs with timestamps grouped by sender for batching
func (store *MessageStore) queryAllMessageIDs(chatJID string) (map[string][]MessageWithTimestamp, error) {
	// Use the performance index we created in Phase 2
	rows, err := store.db.Query(`
		SELECT id, sender, timestamp
		FROM messages
		WHERE chat_jid = ?
		ORDER BY timestamp DESC
	`, chatJID)
	if err != nil {
		return nil, fmt.Errorf("failed to query messages: %w", err)
	}
	defer rows.Close()

	// Group messages by sender (whatsmeow MarkRead requires same sender per call)
	messagesBySender := make(map[string][]MessageWithTimestamp)
	for rows.Next() {
		var id, sender string
		var timestamp time.Time
		if err := rows.Scan(&id, &sender, &timestamp); err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}
		messagesBySender[sender] = append(messagesBySender[sender], MessageWithTimestamp{
			ID:        id,
			Timestamp: timestamp,
		})
	}

	return messagesBySender, nil
}

// Query timestamps for specific message IDs (for explicit mark-as-read)
func (store *MessageStore) queryMessageTimestamps(chatJID string, messageIDs []string) (time.Time, error) {
	if len(messageIDs) == 0 {
		return time.Time{}, fmt.Errorf("no message IDs provided")
	}

	// Build placeholders for IN clause
	placeholders := make([]string, len(messageIDs))
	args := make([]interface{}, len(messageIDs)+1)
	args[0] = chatJID
	for i, id := range messageIDs {
		placeholders[i] = "?"
		args[i+1] = id
	}

	// Query for max timestamp
	query := fmt.Sprintf(`
		SELECT MAX(timestamp)
		FROM messages
		WHERE chat_jid = ? AND id IN (%s)
	`, strings.Join(placeholders, ","))

	var maxTimestamp time.Time
	err := store.db.QueryRow(query, args...).Scan(&maxTimestamp)
	if err != nil {
		return time.Time{}, fmt.Errorf("failed to query timestamps: %w", err)
	}

	return maxTimestamp, nil
}

// Extract direct path from a WhatsApp media URL
func extractDirectPathFromURL(url string) string {
	// The direct path is typically in the URL, we need to extract it
	// Example URL: https://mmg.whatsapp.net/v/t62.7118-24/13812002_698058036224062_3424455886509161511_n.enc?ccb=11-4&oh=...

	// Find the path part after the domain
	parts := strings.SplitN(url, ".net/", 2)
	if len(parts) < 2 {
		return url // Return original URL if parsing fails
	}

	pathPart := parts[1]

	// Remove query parameters
	pathPart = strings.SplitN(pathPart, "?", 2)[0]

	// Create proper direct path format
	return "/" + pathPart
}

// Start a REST API server to expose the WhatsApp client functionality
func startRESTServer(client *whatsmeow.Client, messageStore *MessageStore, port int) {
	// Handler for health check
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		// Get database path
		dbPath := "store/messages.db"

		// Calculate uptime (simple approximation - would need startTime global var for accuracy)
		uptime := 0 // Placeholder - would track actual uptime in production

		// Build response
		response := map[string]interface{}{
			"status":             "ok",
			"whatsapp_connected": client.IsConnected(),
			"database_path":      dbPath,
			"uptime_seconds":     uptime,
		}

		// Set status code based on connection
		statusCode := http.StatusOK
		if !client.IsConnected() {
			statusCode = http.StatusServiceUnavailable
			response["status"] = "degraded"
		}

		// Send response
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(statusCode)
		json.NewEncoder(w).Encode(response)
	})

	// Handler for sending messages
	http.HandleFunc("/api/send", func(w http.ResponseWriter, r *http.Request) {
		// Only allow POST requests
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Parse the request body
		var req SendMessageRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request format", http.StatusBadRequest)
			return
		}

		// Validate request
		if req.Recipient == "" {
			http.Error(w, "Recipient is required", http.StatusBadRequest)
			return
		}

		if req.Message == "" && req.MediaPath == "" {
			http.Error(w, "Message or media path is required", http.StatusBadRequest)
			return
		}

		fmt.Println("Received request to send message", req.Message, req.MediaPath)

		// Send the message
		success, message := sendWhatsAppMessage(client, req.Recipient, req.Message, req.MediaPath)
		fmt.Println("Message sent", success, message)
		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Set appropriate status code
		if !success {
			w.WriteHeader(http.StatusInternalServerError)
		}

		// Send response
		json.NewEncoder(w).Encode(SendMessageResponse{
			Success: success,
			Message: message,
		})
	})

	// Handler for downloading media
	http.HandleFunc("/api/download", func(w http.ResponseWriter, r *http.Request) {
		// Only allow POST requests
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Parse the request body
		var req DownloadMediaRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request format", http.StatusBadRequest)
			return
		}

		// Validate request
		if req.MessageID == "" || req.ChatJID == "" {
			http.Error(w, "Message ID and Chat JID are required", http.StatusBadRequest)
			return
		}

		// Download the media
		success, mediaType, filename, path, err := downloadMedia(client, messageStore, req.MessageID, req.ChatJID)

		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Handle download result
		if !success || err != nil {
			errMsg := "Unknown error"
			if err != nil {
				errMsg = err.Error()
			}

			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(DownloadMediaResponse{
				Success: false,
				Message: fmt.Sprintf("Failed to download media: %s", errMsg),
			})
			return
		}

		// Send successful response
		json.NewEncoder(w).Encode(DownloadMediaResponse{
			Success:  true,
			Message:  fmt.Sprintf("Successfully downloaded %s media", mediaType),
			Filename: filename,
			Path:     path,
		})
	})

	// Handler for marking messages as read
	http.HandleFunc("/api/mark_read", func(w http.ResponseWriter, r *http.Request) {
		// Only allow POST requests
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Parse the request body
		var req MarkAsReadRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request format", http.StatusBadRequest)
			return
		}

		// Validate request
		if req.ChatJID == "" {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(MarkAsReadResponse{
				Success:   false,
				Message:   "Chat JID is required",
				Count:     0,
				ErrorCode: "INVALID_JID",
			})
			return
		}

		// Parse chat JID
		chatJID, err := types.ParseJID(req.ChatJID)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(MarkAsReadResponse{
				Success:   false,
				Message:   fmt.Sprintf("Invalid chat JID format: %v", err),
				Count:     0,
				ErrorCode: "INVALID_JID",
			})
			return
		}

		// Phase 3: T007, T009, T010 - Handle empty message_ids (mark all messages)
		if len(req.MessageIDs) == 0 {
			// Phase 3: T014 - Enhanced logging for mark-all operations
			startTime := time.Now()
			fmt.Printf("[MarkAll] Starting mark-all operation for chat_jid=%s\n", req.ChatJID)

			// Query all message IDs from database (Phase 3: T009)
			messagesBySender, err := messageStore.queryAllMessageIDs(req.ChatJID)
			if err != nil {
				fmt.Printf("[MarkAll] ERROR: Database query failed for chat_jid=%s: %v\n", req.ChatJID, err)
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusInternalServerError)
				json.NewEncoder(w).Encode(MarkAsReadResponse{
					Success:   false,
					Message:   fmt.Sprintf("Failed to query messages: %v", err),
					Count:     0,
					ErrorCode: "DATABASE_ERROR",
				})
				return
			}

			// Check if chat has no messages
			totalMessages := 0
			for _, ids := range messagesBySender {
				totalMessages += len(ids)
			}
			if totalMessages == 0 {
				fmt.Printf("[MarkAll] Chat has no messages: chat_jid=%s, count=0\n", req.ChatJID)
				w.Header().Set("Content-Type", "application/json")
				json.NewEncoder(w).Encode(MarkAsReadResponse{
					Success:   true,
					Message:   "Chat has no messages to mark",
					Count:     0,
					ErrorCode: "EMPTY_CHAT",
				})
				return
			}

			// Phase 3: T010 - Batch messages by sender (1000 per batch)
			fmt.Printf("[MarkAll] Processing %d messages from %d senders for chat_jid=%s\n",
				totalMessages, len(messagesBySender), req.ChatJID)

			markedCount := 0
			failedCount := 0
			batchCount := 0

			for sender, ids := range messagesBySender {
				// CRITICAL FIX: Skip messages where sender == group JID (invalid history sync data)
				// These are messages where historySync didn't provide a Participant field
				if chatJID.Server == "g.us" && (sender == chatJID.User || sender == chatJID.String()) {
					fmt.Printf("[MarkAll] SKIP: Skipping %d messages with invalid sender=%s (group JID cannot be sender)\n",
						len(ids), sender)
					continue
				}

				// Parse sender JID - handle both old format (without @) and new format (with @)
				var senderJID types.JID
				if sender != "" {
					// CRITICAL FIX: Check if sender already has @ suffix (new format)
					if strings.Contains(sender, "@") {
						// New format - sender is already a full JID like "126134616338497@lid"
						senderJID, err = types.ParseJID(sender)
					} else {
						// Old format - sender is just the User part like "126134616338497"
						// Need to reconstruct the proper JID
						if chatJID.Server == "g.us" {
							// Group chat - individual participants use @lid format
							senderJID, err = types.ParseJID(sender + "@lid")
							if err != nil {
								// Fallback to @s.whatsapp.net if @lid doesn't work
								senderJID, err = types.ParseJID(sender + "@s.whatsapp.net")
							}
						} else {
							// Direct chat - use standard WhatsApp format
							senderJID, err = types.ParseJID(sender + "@s.whatsapp.net")
						}
					}

					if err != nil {
						failedCount += len(ids)
						fmt.Printf("[MarkAll] ERROR: Invalid sender JID sender=%s, skipping %d messages: %v\n",
							sender, len(ids), err)
						continue
					}
				}

				// Batch in groups of 1000 messages
				for i := 0; i < len(ids); i += 1000 {
					end := i + 1000
					if end > len(ids) {
						end = len(ids)
					}
					batch := ids[i:end]
					batchCount++

					// Convert to MessageID types and find max timestamp
					messageIDs := make([]types.MessageID, len(batch))
					var maxTimestamp time.Time
					for j, msgWithTS := range batch {
						messageIDs[j] = types.MessageID(msgWithTS.ID)
						// Keep track of the newest timestamp in this batch
						if msgWithTS.Timestamp.After(maxTimestamp) {
							maxTimestamp = msgWithTS.Timestamp
						}
					}

					// Mark this batch as read with the actual timestamp of the newest message
					err = client.MarkRead(messageIDs, maxTimestamp, chatJID, senderJID)
					if err != nil {
						failedCount += len(batch)
						fmt.Printf("[MarkAll] ERROR: Failed to mark batch batch_num=%d, batch_size=%d, sender=%s: %v\n",
							batchCount, len(batch), sender, err)
						continue
					}

					markedCount += len(batch)
					fmt.Printf("[MarkAll] Marked batch batch_num=%d, batch_size=%d, sender=%s, progress=%d/%d\n",
						batchCount, len(batch), sender, markedCount, totalMessages)
				}
			}

			// Phase 3: T014 - Final summary log
			duration := time.Since(startTime)
			fmt.Printf("[MarkAll] SUMMARY: chat_jid=%s, total_messages=%d, marked=%d, failed=%d, batches=%d, duration=%v\n",
				req.ChatJID, totalMessages, markedCount, failedCount, batchCount, duration)

			// Update database to mark all messages in chat as read
			_, err = messageStore.db.Exec(`
				UPDATE messages
				SET is_read = 1, read_timestamp = ?
				WHERE chat_jid = ? AND is_from_me = 0`,
				time.Now(), req.ChatJID)
			if err != nil {
				fmt.Printf("WARNING: Failed to update is_read in database for chat %s: %v\n", req.ChatJID, err)
			}

			// Return success with count
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(MarkAsReadResponse{
				Success: true,
				Message: fmt.Sprintf("Marked %d message(s) as read", markedCount),
				Count:   markedCount,
			})
			return
		}

		// Explicit message IDs provided (existing behavior)
		// Parse sender JID if provided
		var senderJID types.JID
		if req.Sender != "" {
			senderJID, err = types.ParseJID(req.Sender)
			if err != nil {
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusBadRequest)
				json.NewEncoder(w).Encode(MarkAsReadResponse{
					Success:   false,
					Message:   fmt.Sprintf("Invalid sender JID: %v", err),
					Count:     0,
					ErrorCode: "INVALID_JID",
				})
				return
			}
		}

		// Query the actual timestamps of the messages being marked
		maxTimestamp, err := messageStore.queryMessageTimestamps(req.ChatJID, req.MessageIDs)
		if err != nil {
			fmt.Printf("Failed to query message timestamps: %v\n", err)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(MarkAsReadResponse{
				Success:   false,
				Message:   fmt.Sprintf("Failed to query message timestamps: %v", err),
				Count:     0,
				ErrorCode: "DATABASE_ERROR",
			})
			return
		}

		// Convert string IDs to MessageID types
		messageIDs := make([]types.MessageID, len(req.MessageIDs))
		for i, id := range req.MessageIDs {
			messageIDs[i] = types.MessageID(id)
		}

		// Send read receipt for the messages with the actual timestamp of the newest message
		err = client.MarkRead(messageIDs, maxTimestamp, chatJID, senderJID)
		if err != nil {
			fmt.Printf("Failed to mark messages as read: %v\n", err)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(MarkAsReadResponse{
				Success:   false,
				Message:   fmt.Sprintf("Failed to mark messages as read: %v", err),
				Count:     0,
				ErrorCode: "WHATSAPP_API_ERROR",
			})
			return
		}

		fmt.Printf("Marked %d message(s) as read in chat %s\n", len(req.MessageIDs), req.ChatJID)

		// Update database to mark messages as read
		for _, msgID := range req.MessageIDs {
			_, err = messageStore.db.Exec(`
				UPDATE messages
				SET is_read = 1, read_timestamp = ?
				WHERE id = ? AND chat_jid = ?`,
				time.Now(), msgID, req.ChatJID)
			if err != nil {
				fmt.Printf("WARNING: Failed to update is_read in database for message %s: %v\n", msgID, err)
			}
		}

		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Send response
		json.NewEncoder(w).Encode(MarkAsReadResponse{
			Success: true,
			Message: fmt.Sprintf("Marked %d message(s) as read", len(req.MessageIDs)),
			Count:   len(req.MessageIDs),
		})
	})

	// Handler for triggering history sync
	http.HandleFunc("/api/sync_history", func(w http.ResponseWriter, r *http.Request) {
		// Only allow POST requests
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Trigger history sync
		requestHistorySync(client)

		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Send response
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "History sync requested. Check logs for sync progress.",
		})
	})

	// Handler for syncing all groups from WhatsApp
	http.HandleFunc("/api/sync_groups", func(w http.ResponseWriter, r *http.Request) {
		// Only allow POST requests
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Get all joined groups from WhatsApp
		groups, err := client.GetJoinedGroups(context.Background())
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": false,
				"message": fmt.Sprintf("Failed to get joined groups: %v", err),
			})
			return
		}

		fmt.Printf("Syncing %d groups from WhatsApp...\n", len(groups))

		// Store each group in the database
		syncedCount := 0
		for _, group := range groups {
			groupJID := group.JID.String()
			groupName := group.Name
			if groupName == "" {
				groupName = fmt.Sprintf("Group %s", group.JID.User)
			}

			// Check if group belongs to a community
			parentGroupJID := ""
			if group.GroupLinkedParent.LinkedParentJID.User != "" {
				parentGroupJID = group.GroupLinkedParent.LinkedParentJID.String()
			}

			// Store the group with current timestamp
			err := messageStore.StoreChatWithParent(groupJID, groupName, time.Now(), parentGroupJID)
			if err != nil {
				fmt.Printf("Failed to store group %s: %v\n", groupJID, err)
			} else {
				syncedCount++
				if parentGroupJID != "" {
					fmt.Printf("Stored group: %s (name: %s, community: %s)\n", groupJID, groupName, parentGroupJID)
				} else {
					fmt.Printf("Stored group: %s (name: %s)\n", groupJID, groupName)
				}
			}
		}

		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Send response
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": fmt.Sprintf("Successfully synced %d groups", syncedCount),
			"total":   len(groups),
			"synced":  syncedCount,
		})
	})

	// Handler for syncing history for a specific chat
	http.HandleFunc("/api/sync_chat_history", func(w http.ResponseWriter, r *http.Request) {
		// Only allow POST requests
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		fmt.Println("[DEBUG] /api/sync_chat_history endpoint called")

		// Parse the request body
		var req SyncChatHistoryRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request format", http.StatusBadRequest)
			return
		}

		// Validate request
		if req.ChatJID == "" {
			http.Error(w, "Chat JID is required", http.StatusBadRequest)
			return
		}

		// Default count to 50 if not specified
		count := req.Count
		if count == 0 {
			count = 50
		}

		fmt.Printf("[DEBUG] Requesting history sync for chat %s (count: %d)...\n", req.ChatJID, count)

		// Validate client state before attempting history sync
		fmt.Println("[DEBUG] Checking client.IsConnected()...")
		if !client.IsConnected() {
			fmt.Println("[DEBUG] Client is NOT connected")
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusServiceUnavailable)
			json.NewEncoder(w).Encode(SyncChatHistoryResponse{
				Success: false,
				Message: "Client is not connected to WhatsApp",
			})
			return
		}
		fmt.Println("[DEBUG] Client is connected")

		fmt.Println("[DEBUG] Checking client.Store.ID...")
		if client.Store.ID == nil {
			fmt.Println("[DEBUG] Client.Store.ID is NIL")
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			json.NewEncoder(w).Encode(SyncChatHistoryResponse{
				Success: false,
				Message: "Client is not logged in to WhatsApp",
			})
			return
		}
		fmt.Printf("[DEBUG] Client.Store.ID is valid: %v\n", client.Store.ID)

		// Parse chat JID
		fmt.Printf("[DEBUG] Parsing chat JID: %s\n", req.ChatJID)
		chatJID, err := types.ParseJID(req.ChatJID)
		if err != nil {
			fmt.Printf("[DEBUG] Failed to parse chat JID: %v\n", err)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(SyncChatHistoryResponse{
				Success: false,
				Message: fmt.Sprintf("Invalid chat JID: %v", err),
			})
			return
		}
		fmt.Printf("[DEBUG] Successfully parsed chat JID: %v\n", chatJID)

		// Build history sync request for this specific chat
		// Use nil as the MessageInfo parameter to request most recent messages
		fmt.Println("[DEBUG] About to call client.BuildHistorySyncRequest...")
		fmt.Printf("[DEBUG] Parameters: MessageInfo=nil, count=%d\n", count)
		fmt.Printf("[DEBUG] Client state: IsConnected=%v, Store.ID=%v\n", client.IsConnected(), client.Store.ID)

		historyMsg := client.BuildHistorySyncRequest(nil, count)

		fmt.Println("[DEBUG] Successfully called BuildHistorySyncRequest")
		if historyMsg == nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(SyncChatHistoryResponse{
				Success: false,
				Message: "Failed to build history sync request",
			})
			return
		}

		// Send the history sync request with Peer flag
		_, err = client.SendMessage(context.Background(), chatJID, historyMsg, whatsmeow.SendRequestExtra{Peer: true})
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(SyncChatHistoryResponse{
				Success: false,
				Message: fmt.Sprintf("Failed to send history sync request: %v", err),
			})
			return
		}

		fmt.Printf("History sync requested for chat %s\n", req.ChatJID)

		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Send response
		json.NewEncoder(w).Encode(SyncChatHistoryResponse{
			Success: true,
			Message: fmt.Sprintf("History sync requested for chat %s. Messages will be synced in the background.", req.ChatJID),
		})
	})

	// Handler for querying messages with filters
	http.HandleFunc("/api/messages", func(w http.ResponseWriter, r *http.Request) {
		// Only allow GET requests
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Parse query parameters
		query := r.URL.Query()
		req := QueryMessagesRequest{
			ChatJID:         query.Get("chat_jid"),
			Sender:          query.Get("sender"),
			Content:         query.Get("content"),
			AfterTime:       query.Get("after_time"),
			BeforeTime:      query.Get("before_time"),
			MediaTypeFilter: query.Get("media_type"),
		}

		// Parse limit and offset
		if limitStr := query.Get("limit"); limitStr != "" {
			if limit, err := strconv.Atoi(limitStr); err == nil {
				req.Limit = limit
			}
		}
		if offsetStr := query.Get("offset"); offsetStr != "" {
			if offset, err := strconv.Atoi(offsetStr); err == nil {
				req.Offset = offset
			}
		}

		// Parse include_media flag
		if includeMediaStr := query.Get("include_media"); includeMediaStr == "true" {
			req.IncludeMedia = true
		}

		// Query messages
		messages, total, err := messageStore.QueryMessages(req)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(QueryMessagesResponse{
				Success: false,
				Message: fmt.Sprintf("Failed to query messages: %v", err),
			})
			return
		}

		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Send response
		limit := req.Limit
		if limit == 0 {
			limit = 100 // Default limit
		}
		json.NewEncoder(w).Encode(QueryMessagesResponse{
			Success:  true,
			Messages: messages,
			Total:    total,
			Limit:    limit,
			Offset:   req.Offset,
		})
	})

	// Handler for batch inserting messages (from Baileys sync)
	http.HandleFunc("/api/messages/batch", func(w http.ResponseWriter, r *http.Request) {
		// Only allow POST requests
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Parse the request body
		var req BatchInsertRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(BatchInsertResponse{
				Success: false,
				Message: fmt.Sprintf("Invalid request format: %v", err),
			})
			return
		}

		// Validate request
		if len(req.Messages) == 0 {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(BatchInsertResponse{
				Success: false,
				Message: "No messages provided",
			})
			return
		}

		if len(req.Messages) > 1000 {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(BatchInsertResponse{
				Success: false,
				Message: fmt.Sprintf("Batch size too large: %d messages (max 1000)", len(req.Messages)),
			})
			return
		}

		// Insert messages using MessageStore
		insertedCount := 0
		duplicateCount := 0
		failedCount := 0

		for _, msg := range req.Messages {
			// Convert Unix timestamp to time.Time
			timestamp := time.Unix(msg.Timestamp, 0)

			// Handle optional Content field
			content := ""
			if msg.Content != nil {
				content = *msg.Content
			}

			// Store message using existing MessageStore method
			err := messageStore.StoreMessage(
				msg.ID,
				msg.ChatJID,
				msg.Sender,
				content,
				timestamp,
				msg.FromMe,
				"", // mediaType - not provided in Baileys sync
				"", // filename
				"", // url
				nil, // mediaKey
				nil, // fileSHA256
				nil, // fileEncSHA256
				0,   // fileLength
			)

			if err != nil {
				// SQLite returns "UNIQUE constraint failed" for duplicates
				// Since we use INSERT OR REPLACE, this counts as an update (duplicate)
				if strings.Contains(err.Error(), "UNIQUE") {
					duplicateCount++
				} else {
					failedCount++
					fmt.Printf("Failed to store message %s: %v\n", msg.ID, err)
				}
			} else {
				insertedCount++
			}
		}

		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Send response
		json.NewEncoder(w).Encode(BatchInsertResponse{
			Success:         failedCount == 0,
			Message:         fmt.Sprintf("Processed %d messages: %d inserted, %d duplicates, %d failed", len(req.Messages), insertedCount, duplicateCount, failedCount),
			InsertedCount:   insertedCount,
			DuplicateCount:  duplicateCount,
			FailedCount:     failedCount,
		})
	})

	// Handler for getting chats with unread messages
	http.HandleFunc("/api/chats/unread", func(w http.ResponseWriter, r *http.Request) {
		// Only allow GET requests
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Parse query parameters
		query := r.URL.Query()
		limitStr := query.Get("limit")
		limit := 20 // default limit
		if limitStr != "" {
			if parsed, err := strconv.Atoi(limitStr); err == nil && parsed > 0 {
				limit = parsed
			}
		}

		// Query chats with unread messages
		sqlQuery := `
			WITH unread_chats AS (
				SELECT DISTINCT
					m.chat_jid,
					COUNT(CASE WHEN m.is_read = 0 THEN 1 END) as unread_count,
					MAX(m.timestamp) as last_message_time,
					MAX(CASE WHEN m.is_read = 0 THEN m.timestamp END) as last_unread_time
				FROM messages m
				WHERE m.is_from_me = 0
				GROUP BY m.chat_jid
				HAVING unread_count > 0
			),
			latest_messages AS (
				SELECT
					uc.chat_jid,
					uc.unread_count,
					uc.last_message_time,
					uc.last_unread_time,
					m.content as last_message,
					m.sender as last_sender,
					COALESCE(
						ch.name,  -- First try to get name from chats table
						c.name,   -- Then try contacts table
						c.phone_number,
						uc.chat_jid  -- Finally fallback to JID
					) as chat_name,
					CASE
						WHEN uc.chat_jid LIKE '%g.us' THEN 'group'
						WHEN uc.chat_jid LIKE '%newsletter' THEN 'newsletter'
						ELSE 'individual'
					END as chat_type,
					-- Calculate priority score based on various factors
					(
						CASE
							-- Group chats get higher priority
							WHEN uc.chat_jid LIKE '%g.us' THEN 2.0
							-- Individual chats
							ELSE 1.0
						END
						-- More unread messages = higher priority (simple scaling)
						+ MIN(uc.unread_count * 0.1, 2.0)
						-- Recent messages get higher priority (decay over time)
						+ (1.0 / (1.0 + (julianday('now') - julianday(uc.last_unread_time)) * 0.1))
					) as priority_score
				FROM unread_chats uc
				JOIN messages m ON m.chat_jid = uc.chat_jid
					AND m.timestamp = uc.last_message_time
				LEFT JOIN chats ch ON ch.jid = uc.chat_jid  -- Join with chats table
				LEFT JOIN contacts c ON c.jid = uc.chat_jid
			)
			SELECT
				chat_jid,
				chat_name,
				chat_type,
				unread_count,
				last_message,
				last_sender,
				last_message_time,
				last_unread_time,
				priority_score
			FROM latest_messages
			ORDER BY priority_score DESC, last_unread_time DESC
			LIMIT ?`

		rows, err := messageStore.db.Query(sqlQuery, limit)
		if err != nil {
			fmt.Printf("ERROR in /api/chats/unread: %v\n", err)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": false,
				"error":   err.Error(),
			})
			return
		}
		defer rows.Close()

		type UnreadChat struct {
			ChatJID         string    `json:"chat_jid"`
			ChatName        string    `json:"chat_name"`
			ChatType        string    `json:"chat_type"`
			UnreadCount     int       `json:"unread_count"`
			LastMessage     *string   `json:"last_message"`
			LastSender      *string   `json:"last_sender"`
			LastMessageTime time.Time `json:"last_message_time"`
			LastUnreadTime  time.Time `json:"last_unread_time"`
			PriorityScore   float64   `json:"priority_score"`
		}

		var chats []UnreadChat
		for rows.Next() {
			var chat UnreadChat
			var lastMessage, lastSender sql.NullString
			var lastMessageTimeStr, lastUnreadTimeStr string

			if err := rows.Scan(
				&chat.ChatJID,
				&chat.ChatName,
				&chat.ChatType,
				&chat.UnreadCount,
				&lastMessage,
				&lastSender,
				&lastMessageTimeStr,
				&lastUnreadTimeStr,
				&chat.PriorityScore,
			); err != nil {
				fmt.Printf("ERROR scanning row in /api/chats/unread: %v\n", err)
				continue
			}

			// Parse timestamp strings
			chat.LastMessageTime, _ = time.Parse("2006-01-02 15:04:05", lastMessageTimeStr)
			chat.LastUnreadTime, _ = time.Parse("2006-01-02 15:04:05", lastUnreadTimeStr)

			if lastMessage.Valid {
				chat.LastMessage = &lastMessage.String
			}
			if lastSender.Valid {
				chat.LastSender = &lastSender.String
			}

			chats = append(chats, chat)
		}

		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Send response
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"chats":   chats,
			"count":   len(chats),
		})
	})

	// Handler for getting conversation view for a specific chat
	http.HandleFunc("/api/chats/conversation", func(w http.ResponseWriter, r *http.Request) {
		// Only allow GET requests
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Parse query parameters
		query := r.URL.Query()
		chatJID := query.Get("chat_jid")
		if chatJID == "" {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": false,
				"error":   "chat_jid parameter is required",
			})
			return
		}

		limitStr := query.Get("limit")
		limit := 50 // default limit for conversation view
		if limitStr != "" {
			if parsed, err := strconv.Atoi(limitStr); err == nil && parsed > 0 {
				limit = parsed
			}
		}

		onlyUnread := query.Get("only_unread") == "true"

		// Build SQL query
		sqlQuery := `
			SELECT
				m.id as message_id,
				m.chat_jid,
				m.sender as sender_jid,
				COALESCE(
					-- First try direct match for @lid IDs
					(SELECT name FROM contacts WHERE jid = m.sender AND name != phone_number),
					-- Try to get the name from any contact with matching number
					(SELECT name FROM contacts c2
					 WHERE SUBSTR(m.sender, 1, INSTR(m.sender, '@') - 1) = SUBSTR(c2.jid, 1, INSTR(c2.jid, '@') - 1)
					   AND c2.name != c2.phone_number
					 LIMIT 1),
					-- Otherwise use the direct match
					c.name,
					-- Fallback to sender
					m.sender
				) as sender_name,
				m.content as message_text,
				m.media_type,
				m.filename as media_path,
				m.timestamp,
				m.is_from_me,
				m.is_read,
				m.read_timestamp,
				COALESCE(
					chats.name,  -- First try to get name from chats table
					ch.name,     -- Then try contacts table
					ch.phone_number,
					m.chat_jid   -- Finally fallback to JID
				) as chat_name
			FROM messages m
			LEFT JOIN contacts c ON c.jid = m.sender
			LEFT JOIN contacts ch ON ch.jid = m.chat_jid
			LEFT JOIN chats ON chats.jid = m.chat_jid  -- Join with chats table
			WHERE m.chat_jid = ?`

		if onlyUnread {
			sqlQuery += " AND m.is_read = 0"
		}

		sqlQuery += `
			ORDER BY m.timestamp DESC
			LIMIT ?`

		rows, err := messageStore.db.Query(sqlQuery, chatJID, limit)
		if err != nil {
			fmt.Printf("ERROR in /api/chats/conversation: %v\n", err)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": false,
				"error":   err.Error(),
			})
			return
		}
		defer rows.Close()

		type ConversationMessage struct {
			MessageID     string     `json:"message_id"`
			ChatJID       string     `json:"chat_jid"`
			SenderJID     string     `json:"sender_jid"`
			SenderName    string     `json:"sender_name"`
			MessageText   *string    `json:"message_text"`
			MediaType     *string    `json:"media_type"`
			MediaPath     *string    `json:"media_path"`
			Timestamp     time.Time  `json:"timestamp"`
			IsFromMe      bool       `json:"is_from_me"`
			IsRead        bool       `json:"is_read"`
			ReadTimestamp *time.Time `json:"read_timestamp"`
			ChatName      string     `json:"chat_name"`
		}

		var messages []ConversationMessage
		for rows.Next() {
			var msg ConversationMessage
			var messageText, mediaType, mediaPath sql.NullString
			var timestampStr string
			var readTimestampStr sql.NullString

			if err := rows.Scan(
				&msg.MessageID,
				&msg.ChatJID,
				&msg.SenderJID,
				&msg.SenderName,
				&messageText,
				&mediaType,
				&mediaPath,
				&timestampStr,
				&msg.IsFromMe,
				&msg.IsRead,
				&readTimestampStr,
				&msg.ChatName,
			); err != nil {
				fmt.Printf("ERROR scanning row in /api/chats/conversation: %v\n", err)
				continue
			}

			// Parse timestamp strings
			msg.Timestamp, _ = time.Parse("2006-01-02 15:04:05", timestampStr)
			if readTimestampStr.Valid && readTimestampStr.String != "" {
				if readTime, err := time.Parse("2006-01-02 15:04:05", readTimestampStr.String); err == nil {
					msg.ReadTimestamp = &readTime
				}
			}

			if messageText.Valid {
				msg.MessageText = &messageText.String
			}
			if mediaType.Valid {
				msg.MediaType = &mediaType.String
			}
			if mediaPath.Valid {
				msg.MediaPath = &mediaPath.String
			}

			messages = append(messages, msg)
		}

		// Reverse the messages array to show oldest first (since we queried DESC)
		for i, j := 0, len(messages)-1; i < j; i, j = i+1, j-1 {
			messages[i], messages[j] = messages[j], messages[i]
		}

		// Get unread count for this chat
		var unreadCount int
		err = messageStore.db.QueryRow(`
			SELECT COUNT(*)
			FROM messages
			WHERE chat_jid = ? AND is_read = 0 AND is_from_me = 0`,
			chatJID).Scan(&unreadCount)
		if err != nil {
			unreadCount = 0
		}

		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Send response
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success":      true,
			"chat_jid":     chatJID,
			"messages":     messages,
			"count":        len(messages),
			"unread_count": unreadCount,
		})
	})

	// Handler for getting message statistics
	http.HandleFunc("/api/stats", func(w http.ResponseWriter, r *http.Request) {
		// Only allow GET requests
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		// Get stats
		stats, err := messageStore.GetMessageStats()
		if err != nil {
			fmt.Printf("ERROR in /api/stats: %v\n", err)
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(MessageStatsResponse{
				Success: false,
			})
			return
		}

		// Set response headers
		w.Header().Set("Content-Type", "application/json")

		// Send response
		json.NewEncoder(w).Encode(stats)
	})

	// Note: All routes are registered above in the http.HandleFunc calls
	// No need for separate route registration functions

	// Start the server
	serverAddr := fmt.Sprintf(":%d", port)
	fmt.Printf("Starting REST API server on %s...\n", serverAddr)

	// Run server in a goroutine so it doesn't block
	go func() {
		if err := http.ListenAndServe(serverAddr, nil); err != nil {
			fmt.Printf("REST API server error: %v\n", err)
		}
	}()
}


// SyncChatHistoryRequest represents the request body for syncing a chat's history
type SyncChatHistoryRequest struct {
	ChatJID string `json:"chat_jid"`
	Count   int    `json:"count,omitempty"`
}

// SyncChatHistoryResponse represents the response for the sync chat history API
type SyncChatHistoryResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// QueryMessagesRequest represents the request for querying messages with filters
type QueryMessagesRequest struct {
	ChatJID        string `json:"chat_jid,omitempty"`
	Sender         string `json:"sender,omitempty"`
	Content        string `json:"content,omitempty"`
	AfterTime      string `json:"after_time,omitempty"`
	BeforeTime     string `json:"before_time,omitempty"`
	Limit          int    `json:"limit,omitempty"`
	Offset         int    `json:"offset,omitempty"`
	IncludeMedia   bool   `json:"include_media,omitempty"`
	MediaTypeFilter string `json:"media_type,omitempty"`
}

// MessageResult represents a message in query results
type MessageResult struct {
	ID         string    `json:"id"`
	ChatJID    string    `json:"chat_jid"`
	ChatName   string    `json:"chat_name,omitempty"`
	Sender     string    `json:"sender"`
	SenderName string    `json:"sender_name,omitempty"`
	Content    string    `json:"content"`
	Timestamp  time.Time `json:"timestamp"`
	IsFromMe   bool      `json:"is_from_me"`
	MediaType  string    `json:"media_type,omitempty"`
	Filename   string    `json:"filename,omitempty"`
}

// QueryMessagesResponse represents the response for message queries
type QueryMessagesResponse struct {
	Success  bool            `json:"success"`
	Message  string          `json:"message,omitempty"`
	Messages []MessageResult `json:"messages"`
	Total    int             `json:"total"`
	Limit    int             `json:"limit"`
	Offset   int             `json:"offset"`
}

// MessageStatsResponse represents statistics about messages
type MessageStatsResponse struct {
	Success        bool              `json:"success"`
	TotalMessages  int               `json:"total_messages"`
	TotalChats     int               `json:"total_chats"`
	TotalContacts  int               `json:"total_contacts"`
	MediaMessages  int               `json:"media_messages"`
	TextMessages   int               `json:"text_messages"`
	MessagesByType map[string]int    `json:"messages_by_type"`
	OldestMessage  time.Time         `json:"oldest_message,omitempty"`
	NewestMessage  time.Time         `json:"newest_message,omitempty"`
}

func main() {
	// Set up logger
	logger := waLog.Stdout("Client", "INFO", true)
	logger.Infof("Starting WhatsApp client...")

	// Create database connection for storing session data
	dbLog := waLog.Stdout("Database", "INFO", true)

	// Create directory for database if it doesn't exist
	if err := os.MkdirAll("store", 0755); err != nil {
		logger.Errorf("Failed to create store directory: %v", err)
		return
	}

	container, err := sqlstore.New(context.Background(), "sqlite3", "file:store/whatsapp.db?_foreign_keys=on", dbLog)
	if err != nil {
		logger.Errorf("Failed to connect to database: %v", err)
		return
	}

	// Get device store - This contains session information
	deviceStore, err := container.GetFirstDevice(context.Background())
	if err != nil {
		if err == sql.ErrNoRows {
			// No device exists, create one
			deviceStore = container.NewDevice()
			logger.Infof("Created new device")
		} else {
			logger.Errorf("Failed to get device: %v", err)
			return
		}
	}

	// Create client instance
	client := whatsmeow.NewClient(deviceStore, logger)
	if client == nil {
		logger.Errorf("Failed to create WhatsApp client")
		return
	}

	// Initialize message store
	messageStore, err := NewMessageStore()
	if err != nil {
		logger.Errorf("Failed to initialize message store: %v", err)
		return
	}
	defer messageStore.Close()

	// Setup event handling for messages and history sync
	client.AddEventHandler(func(evt interface{}) {
		switch v := evt.(type) {
		case *events.Message:
			// Process regular messages
			handleMessage(client, messageStore, v, logger)

		case *events.Receipt:
			// Track read receipts from other clients
			if v.Type == types.ReceiptTypeRead || v.Type == types.ReceiptTypeReadSelf {
				// Update messages as read in database
				for _, msgID := range v.MessageIDs {
					_, err := messageStore.db.Exec(`
						UPDATE messages
						SET is_read = 1, read_timestamp = ?
						WHERE id = ? AND chat_jid = ?`,
						v.Timestamp, msgID, v.Chat.String())
					if err != nil {
						logger.Warnf("Failed to update read status for message %s: %v", msgID, err)
					}
				}
				logger.Infof("Marked %d messages as read in chat %s", len(v.MessageIDs), v.Chat.String())
			}

		case *events.HistorySync:
			// Process history sync events
			handleHistorySync(client, messageStore, v, logger)

		case *events.Connected:
			logger.Infof("Connected to WhatsApp")

		case *events.LoggedOut:
			logger.Warnf("Device logged out, please scan QR code to log in again")
		}
	})

	// Create channel to track connection success
	connected := make(chan bool, 1)

	// Connect to WhatsApp
	if client.Store.ID == nil {
		// No ID stored, this is a new client, need to pair with phone
		qrChan, _ := client.GetQRChannel(context.Background())
		err = client.Connect()
		if err != nil {
			logger.Errorf("Failed to connect: %v", err)
			return
		}

		// Print QR code for pairing with phone
		for evt := range qrChan {
			if evt.Event == "code" {
				fmt.Println("\nScan this QR code with your WhatsApp app:")
				qrterminal.GenerateHalfBlock(evt.Code, qrterminal.L, os.Stdout)
			} else if evt.Event == "success" {
				connected <- true
				break
			}
		}

		// Wait for connection
		select {
		case <-connected:
			fmt.Println("\nSuccessfully connected and authenticated!")
		case <-time.After(3 * time.Minute):
			logger.Errorf("Timeout waiting for QR code scan")
			return
		}
	} else {
		// Already logged in, just connect
		err = client.Connect()
		if err != nil {
			logger.Errorf("Failed to connect: %v", err)
			return
		}
		connected <- true
	}

	// Wait a moment for connection to stabilize
	time.Sleep(2 * time.Second)

	if !client.IsConnected() {
		logger.Errorf("Failed to establish stable connection")
		return
	}

	fmt.Println("\n✓ Connected to WhatsApp! Type 'help' for commands.")

	// Populate contacts from WhatsApp into the database
	logger.Infof("Populating contacts from WhatsApp...")
	err = messageStore.PopulateContacts(client)
	if err != nil {
		logger.Warnf("Failed to populate contacts: %v", err)
	}

	// Populate group participant information to resolve @lid IDs to real names
	logger.Infof("Syncing group participant names...")
	err = messageStore.PopulateGroupParticipants(client)
	if err != nil {
		logger.Warnf("Failed to populate group participants: %v", err)
	}

	// Resync @lid entries with existing contacts
	logger.Infof("Resyncing @lid entries with existing contacts...")
	err = messageStore.ResyncLIDsWithContacts()
	if err != nil {
		logger.Warnf("Failed to resync @lid contacts: %v", err)
	}

	// Fix @lid mappings with wrong phone numbers
	logger.Infof("Fixing @lid mappings with correct phone numbers...")
	err = messageStore.FixLIDMappings(client)
	if err != nil {
		logger.Warnf("Failed to fix @lid mappings: %v", err)
	}

	// Start REST API server
	startRESTServer(client, messageStore, 8080)

	// Create a channel to keep the main goroutine alive
	exitChan := make(chan os.Signal, 1)
	signal.Notify(exitChan, syscall.SIGINT, syscall.SIGTERM)

	fmt.Println("REST server is running. Press Ctrl+C to disconnect and exit.")

	// Wait for termination signal
	<-exitChan

	fmt.Println("Disconnecting...")
	// Disconnect client
	client.Disconnect()
}

// GetChatName determines the appropriate name for a chat based on JID and other info
func GetChatName(client *whatsmeow.Client, messageStore *MessageStore, jid types.JID, chatJID string, conversation interface{}, sender string, logger waLog.Logger) string {
	// First, check if chat already exists in database with a name
	var existingName string
	err := messageStore.db.QueryRow("SELECT name FROM chats WHERE jid = ?", chatJID).Scan(&existingName)
	if err == nil && existingName != "" {
		// Chat exists with a name, use that
		logger.Infof("Using existing chat name for %s: %s", chatJID, existingName)
		return existingName
	}

	// Need to determine chat name
	var name string

	if jid.Server == "g.us" {
		// This is a group chat
		logger.Infof("Getting name for group: %s", chatJID)

		// Use conversation data if provided (from history sync)
		if conversation != nil {
			// Extract name from conversation if available
			// This uses type assertions to handle different possible types
			var displayName, convName *string
			// Try to extract the fields we care about regardless of the exact type
			v := reflect.ValueOf(conversation)
			if v.Kind() == reflect.Ptr && !v.IsNil() {
				v = v.Elem()

				// Try to find DisplayName field
				if displayNameField := v.FieldByName("DisplayName"); displayNameField.IsValid() && displayNameField.Kind() == reflect.Ptr && !displayNameField.IsNil() {
					dn := displayNameField.Elem().String()
					displayName = &dn
				}

				// Try to find Name field
				if nameField := v.FieldByName("Name"); nameField.IsValid() && nameField.Kind() == reflect.Ptr && !nameField.IsNil() {
					n := nameField.Elem().String()
					convName = &n
				}
			}

			// Use the name we found
			if displayName != nil && *displayName != "" {
				name = *displayName
			} else if convName != nil && *convName != "" {
				name = *convName
			}
		}

		// If we didn't get a name, try group info
		if name == "" {
			groupInfo, err := client.GetGroupInfo(jid)
			if err == nil && groupInfo.Name != "" {
				name = groupInfo.Name
			} else {
				// Fallback name for groups
				name = fmt.Sprintf("Group %s", jid.User)
			}
		}

		logger.Infof("Using group name: %s", name)
	} else {
		// This is an individual contact
		logger.Infof("Getting name for contact: %s", chatJID)

		// Just use contact info (full name)
		contact, err := client.Store.Contacts.GetContact(context.Background(), jid)
		if err == nil && contact.FullName != "" {
			name = contact.FullName
		} else if sender != "" {
			// Fallback to sender
			name = sender
		} else {
			// Last fallback to JID
			name = jid.User
		}

		logger.Infof("Using contact name: %s", name)
	}

	return name
}

// Handle history sync events
func handleHistorySync(client *whatsmeow.Client, messageStore *MessageStore, historySync *events.HistorySync, logger waLog.Logger) {
	fmt.Printf("Received history sync event with %d conversations\n", len(historySync.Data.Conversations))

	syncedCount := 0
	for _, conversation := range historySync.Data.Conversations {
		// Parse JID from the conversation
		if conversation.ID == nil {
			continue
		}

		chatJID := *conversation.ID

		// Try to parse the JID
		jid, err := types.ParseJID(chatJID)
		if err != nil {
			logger.Warnf("Failed to parse JID %s: %v", chatJID, err)
			continue
		}

		// Get appropriate chat name by passing the history sync conversation directly
		name := GetChatName(client, messageStore, jid, chatJID, conversation, "", logger)

		// Process messages
		messages := conversation.Messages
		if len(messages) > 0 {
			// Update chat with latest message timestamp
			latestMsg := messages[0]
			if latestMsg == nil || latestMsg.Message == nil {
				continue
			}

			// Get timestamp from message info
			timestamp := time.Time{}
			if ts := latestMsg.Message.GetMessageTimestamp(); ts != 0 {
				timestamp = time.Unix(int64(ts), 0)
			} else {
				continue
			}

			messageStore.StoreChat(chatJID, name, timestamp)

			// Store messages
			for _, msg := range messages {
				if msg == nil || msg.Message == nil {
					continue
				}

				// Extract text content
				var content string
				if msg.Message.Message != nil {
					if conv := msg.Message.Message.GetConversation(); conv != "" {
						content = conv
					} else if ext := msg.Message.Message.GetExtendedTextMessage(); ext != nil {
						content = ext.GetText()
					}
				}

				// Extract media info
				var mediaType, filename, url string
				var mediaKey, fileSHA256, fileEncSHA256 []byte
				var fileLength uint64

				if msg.Message.Message != nil {
					mediaType, filename, url, mediaKey, fileSHA256, fileEncSHA256, fileLength = extractMediaInfo(msg.Message.Message)
				}

				// Log the message content for debugging
				logger.Infof("Message content: %v, Media Type: %v", content, mediaType)

				// Skip messages with no content and no media
				if content == "" && mediaType == "" {
					continue
				}

				// Determine sender
				var sender string
				isFromMe := false
				if msg.Message.Key != nil {
					if msg.Message.Key.FromMe != nil {
						isFromMe = *msg.Message.Key.FromMe
					}
					if !isFromMe && msg.Message.Key.Participant != nil && *msg.Message.Key.Participant != "" {
						sender = *msg.Message.Key.Participant
					} else if isFromMe {
						sender = client.Store.ID.User
					} else {
						sender = jid.User
					}
				} else {
					sender = jid.User
				}

				// Store message
				msgID := ""
				if msg.Message.Key != nil && msg.Message.Key.ID != nil {
					msgID = *msg.Message.Key.ID
				}

				// Get message timestamp
				timestamp := time.Time{}
				if ts := msg.Message.GetMessageTimestamp(); ts != 0 {
					timestamp = time.Unix(int64(ts), 0)
				} else {
					continue
				}

				err = messageStore.StoreMessage(
					msgID,
					chatJID,
					sender,
					content,
					timestamp,
					isFromMe,
					mediaType,
					filename,
					url,
					mediaKey,
					fileSHA256,
					fileEncSHA256,
					fileLength,
				)
				if err != nil {
					logger.Warnf("Failed to store history message: %v", err)
				} else {
					syncedCount++
					// Log successful message storage
					if mediaType != "" {
						logger.Infof("Stored message: [%s] %s -> %s: [%s: %s] %s",
							timestamp.Format("2006-01-02 15:04:05"), sender, chatJID, mediaType, filename, content)
					} else {
						logger.Infof("Stored message: [%s] %s -> %s: %s",
							timestamp.Format("2006-01-02 15:04:05"), sender, chatJID, content)
					}
				}
			}
		}
	}

	fmt.Printf("History sync complete. Stored %d messages.\n", syncedCount)
}

// Request history sync from the server
func requestHistorySync(client *whatsmeow.Client) {
	if client == nil {
		fmt.Println("Client is not initialized. Cannot request history sync.")
		return
	}

	if !client.IsConnected() {
		fmt.Println("Client is not connected. Please ensure you are connected to WhatsApp first.")
		return
	}

	if client.Store.ID == nil {
		fmt.Println("Client is not logged in. Please scan the QR code first.")
		return
	}

	// Build and send a history sync request
	historyMsg := client.BuildHistorySyncRequest(nil, 100)
	if historyMsg == nil {
		fmt.Println("Failed to build history sync request.")
		return
	}

	_, err := client.SendMessage(context.Background(), types.JID{
		Server: "s.whatsapp.net",
		User:   "status",
	}, historyMsg)

	if err != nil {
		fmt.Printf("Failed to request history sync: %v\n", err)
	} else {
		fmt.Println("History sync requested. Waiting for server response...")
	}
}

// analyzeOggOpus tries to extract duration and generate a simple waveform from an Ogg Opus file
func analyzeOggOpus(data []byte) (duration uint32, waveform []byte, err error) {
	// Try to detect if this is a valid Ogg file by checking for the "OggS" signature
	// at the beginning of the file
	if len(data) < 4 || string(data[0:4]) != "OggS" {
		return 0, nil, fmt.Errorf("not a valid Ogg file (missing OggS signature)")
	}

	// Parse Ogg pages to find the last page with a valid granule position
	var lastGranule uint64
	var sampleRate uint32 = 48000 // Default Opus sample rate
	var preSkip uint16 = 0
	var foundOpusHead bool

	// Scan through the file looking for Ogg pages
	for i := 0; i < len(data); {
		// Check if we have enough data to read Ogg page header
		if i+27 >= len(data) {
			break
		}

		// Verify Ogg page signature
		if string(data[i:i+4]) != "OggS" {
			// Skip until next potential page
			i++
			continue
		}

		// Extract header fields
		granulePos := binary.LittleEndian.Uint64(data[i+6 : i+14])
		pageSeqNum := binary.LittleEndian.Uint32(data[i+18 : i+22])
		numSegments := int(data[i+26])

		// Extract segment table
		if i+27+numSegments >= len(data) {
			break
		}
		segmentTable := data[i+27 : i+27+numSegments]

		// Calculate page size
		pageSize := 27 + numSegments
		for _, segLen := range segmentTable {
			pageSize += int(segLen)
		}

		// Check if we're looking at an OpusHead packet (should be in first few pages)
		if !foundOpusHead && pageSeqNum <= 1 {
			// Look for "OpusHead" marker in this page
			pageData := data[i : i+pageSize]
			headPos := bytes.Index(pageData, []byte("OpusHead"))
			if headPos >= 0 && headPos+12 < len(pageData) {
				// Found OpusHead, extract sample rate and pre-skip
				// OpusHead format: Magic(8) + Version(1) + Channels(1) + PreSkip(2) + SampleRate(4) + ...
				headPos += 8 // Skip "OpusHead" marker
				// PreSkip is 2 bytes at offset 10
				if headPos+12 <= len(pageData) {
					preSkip = binary.LittleEndian.Uint16(pageData[headPos+10 : headPos+12])
					sampleRate = binary.LittleEndian.Uint32(pageData[headPos+12 : headPos+16])
					foundOpusHead = true
					fmt.Printf("Found OpusHead: sampleRate=%d, preSkip=%d\n", sampleRate, preSkip)
				}
			}
		}

		// Keep track of last valid granule position
		if granulePos != 0 {
			lastGranule = granulePos
		}

		// Move to next page
		i += pageSize
	}

	if !foundOpusHead {
		fmt.Println("Warning: OpusHead not found, using default values")
	}

	// Calculate duration based on granule position
	if lastGranule > 0 {
		// Formula for duration: (lastGranule - preSkip) / sampleRate
		durationSeconds := float64(lastGranule-uint64(preSkip)) / float64(sampleRate)
		duration = uint32(math.Ceil(durationSeconds))
		fmt.Printf("Calculated Opus duration from granule: %f seconds (lastGranule=%d)\n",
			durationSeconds, lastGranule)
	} else {
		// Fallback to rough estimation if granule position not found
		fmt.Println("Warning: No valid granule position found, using estimation")
		durationEstimate := float64(len(data)) / 2000.0 // Very rough approximation
		duration = uint32(durationEstimate)
	}

	// Make sure we have a reasonable duration (at least 1 second, at most 300 seconds)
	if duration < 1 {
		duration = 1
	} else if duration > 300 {
		duration = 300
	}

	// Generate waveform
	waveform = placeholderWaveform(duration)

	fmt.Printf("Ogg Opus analysis: size=%d bytes, calculated duration=%d sec, waveform=%d bytes\n",
		len(data), duration, len(waveform))

	return duration, waveform, nil
}

// min returns the smaller of x or y
func min(x, y int) int {
	if x < y {
		return x
	}
	return y
}

// placeholderWaveform generates a synthetic waveform for WhatsApp voice messages
// that appears natural with some variability based on the duration
func placeholderWaveform(duration uint32) []byte {
	// WhatsApp expects a 64-byte waveform for voice messages
	const waveformLength = 64
	waveform := make([]byte, waveformLength)

	// Seed the random number generator for consistent results with the same duration
	rand.Seed(int64(duration))

	// Create a more natural looking waveform with some patterns and variability
	// rather than completely random values

	// Base amplitude and frequency - longer messages get faster frequency
	baseAmplitude := 35.0
	frequencyFactor := float64(min(int(duration), 120)) / 30.0

	for i := range waveform {
		// Position in the waveform (normalized 0-1)
		pos := float64(i) / float64(waveformLength)

		// Create a wave pattern with some randomness
		// Use multiple sine waves of different frequencies for more natural look
		val := baseAmplitude * math.Sin(pos*math.Pi*frequencyFactor*8)
		val += (baseAmplitude / 2) * math.Sin(pos*math.Pi*frequencyFactor*16)

		// Add some randomness to make it look more natural
		val += (rand.Float64() - 0.5) * 15

		// Add some fade-in and fade-out effects
		fadeInOut := math.Sin(pos * math.Pi)
		val = val * (0.7 + 0.3*fadeInOut)

		// Center around 50 (typical voice baseline)
		val = val + 50

		// Ensure values stay within WhatsApp's expected range (0-100)
		if val < 0 {
			val = 0
		} else if val > 100 {
			val = 100
		}

		waveform[i] = byte(val)
	}

	return waveform
}
