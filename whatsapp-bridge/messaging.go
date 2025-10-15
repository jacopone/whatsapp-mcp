package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"strings"
	"time"

	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/types"
	waProto "go.mau.fi/whatsmeow/binary/proto"
	"google.golang.org/protobuf/proto"
)

// SendTextRequest represents the request body for sending a text message
type SendTextRequest struct {
	Recipient string `json:"recipient"` // Phone number or JID
	Message   string `json:"message"`
}

// SendMediaRequest represents the request body for sending media
type SendMediaRequest struct {
	Recipient string `json:"recipient"` // Phone number or JID
	MediaPath string `json:"media_path"`
	MediaType string `json:"media_type"` // image, video, audio, document
	Caption   string `json:"caption,omitempty"`
	Filename  string `json:"filename,omitempty"` // For documents
}

// SendVoiceRequest represents the request body for sending a voice note
type SendVoiceRequest struct {
	Recipient string `json:"recipient"` // Phone number or JID
	AudioPath string `json:"audio_path"` // Path to audio file (will be converted to Opus OGG)
}

// SendStickerRequest represents the request body for sending a sticker
type SendStickerRequest struct {
	Recipient   string `json:"recipient"`    // Phone number or JID
	StickerPath string `json:"sticker_path"` // Path to sticker image (WebP)
}

// SendContactRequest represents the request body for sending a contact vCard
type SendContactRequest struct {
	Recipient string `json:"recipient"` // Phone number or JID
	VCard     string `json:"vcard"`     // vCard formatted contact
	Name      string `json:"name"`      // Display name for the contact
}

// SendLocationRequest represents the request body for sending a location
type SendLocationRequest struct {
	Recipient string  `json:"recipient"` // Phone number or JID
	Latitude  float64 `json:"latitude"`
	Longitude float64 `json:"longitude"`
	Name      string  `json:"name,omitempty"`    // Optional location name
	Address   string  `json:"address,omitempty"` // Optional address
}

// MessageResponse represents the response for message sending operations
type MessageResponse struct {
	Success   bool   `json:"success"`
	Message   string `json:"message"`
	MessageID string `json:"message_id,omitempty"`
	Timestamp int64  `json:"timestamp,omitempty"`
}

// RegisterMessagingRoutes sets up HTTP handlers for messaging endpoints
func RegisterMessagingRoutes(mux *http.ServeMux, client *whatsmeow.Client) {
	// POST /api/messages/send-text
	mux.HandleFunc("/api/messages/send-text", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleSendText(w, r, client)
	})

	// POST /api/messages/send-media
	mux.HandleFunc("/api/messages/send-media", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleSendMedia(w, r, client)
	})

	// POST /api/messages/send-voice
	mux.HandleFunc("/api/messages/send-voice", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleSendVoice(w, r, client)
	})

	// POST /api/messages/send-sticker
	mux.HandleFunc("/api/messages/send-sticker", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleSendSticker(w, r, client)
	})

	// POST /api/messages/send-contact
	mux.HandleFunc("/api/messages/send-contact", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleSendContact(w, r, client)
	})

	// POST /api/messages/send-location
	mux.HandleFunc("/api/messages/send-location", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleSendLocation(w, r, client)
	})

	// POST /api/messages/react - Add or update reaction
	// PUT /api/messages/react - Update existing reaction
	// DELETE /api/messages/react - Remove reaction
	mux.HandleFunc("/api/messages/react", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost && r.Method != http.MethodPut && r.Method != http.MethodDelete {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleReactToMessage(w, r, client)
	})

	// PUT /api/messages/edit - Edit message within 15min window
	mux.HandleFunc("/api/messages/edit", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPut {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleEditMessage(w, r, client)
	})

	// DELETE /api/messages/revoke - Delete message within 48hr window
	mux.HandleFunc("/api/messages/revoke", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodDelete {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleRevokeMessage(w, r, client)
	})

	// POST /api/messages/forward - Forward message to another chat
	mux.HandleFunc("/api/messages/forward", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleForwardMessage(w, r, client)
	})

	// GET /api/messages/media - Download media from a message
	mux.HandleFunc("/api/messages/media", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleDownloadMedia(w, r, client)
	})

	// POST /api/messages/batch - Batch insert messages (for Baileys sync)
	mux.HandleFunc("/api/messages/batch", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleBatchInsertMessages(w, r)
	})
}

// handleSendText sends a text message
func handleSendText(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req SendTextRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Validate request
	if req.Recipient == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Recipient is required",
		})
		return
	}

	if req.Message == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Message text is required",
		})
		return
	}

	// Parse recipient JID
	recipientJID, err := parseJIDOrPhone(req.Recipient)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid recipient: %v", err),
		})
		return
	}

	// Send message
	sentMsg, err := client.SendMessage(context.Background(), recipientJID, &waProto.Message{
		Conversation: proto.String(req.Message),
	})

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to send message: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MessageResponse{
		Success:   true,
		Message:   "Message sent successfully",
		MessageID: sentMsg.ID,
		Timestamp: sentMsg.Timestamp.Unix(),
	})
}

// handleSendMedia sends a media message (image, video, audio, document)
func handleSendMedia(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req SendMediaRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Validate request
	if req.Recipient == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Recipient is required",
		})
		return
	}

	if req.MediaPath == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Media path is required",
		})
		return
	}

	if req.MediaType == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Media type is required (image, video, audio, document)",
		})
		return
	}

	// Parse recipient JID
	recipientJID, err := parseJIDOrPhone(req.Recipient)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid recipient: %v", err),
		})
		return
	}

	// Read media file
	mediaData, err := ioutil.ReadFile(req.MediaPath)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to read media file: %v", err),
		})
		return
	}

	// Upload media
	uploaded, err := client.Upload(context.Background(), mediaData, whatsmeow.MediaType(req.MediaType))
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to upload media: %v", err),
		})
		return
	}

	// Create media message based on type
	var msg *waProto.Message
	caption := proto.String(req.Caption)

	switch strings.ToLower(req.MediaType) {
	case "image":
		msg = &waProto.Message{
			ImageMessage: &waProto.ImageMessage{
				Caption:       caption,
				URL:           proto.String(uploaded.URL),
				DirectPath:    proto.String(uploaded.DirectPath),
				MediaKey:      uploaded.MediaKey,
				FileEncSHA256: uploaded.FileEncSHA256,
				FileSHA256:    uploaded.FileSHA256,
				FileLength:    proto.Uint64(uint64(len(mediaData))),
				Mimetype:      proto.String(http.DetectContentType(mediaData)),
			},
		}
	case "video":
		msg = &waProto.Message{
			VideoMessage: &waProto.VideoMessage{
				Caption:       caption,
				URL:           proto.String(uploaded.URL),
				DirectPath:    proto.String(uploaded.DirectPath),
				MediaKey:      uploaded.MediaKey,
				FileEncSHA256: uploaded.FileEncSHA256,
				FileSHA256:    uploaded.FileSHA256,
				FileLength:    proto.Uint64(uint64(len(mediaData))),
				Mimetype:      proto.String(http.DetectContentType(mediaData)),
			},
		}
	case "audio":
		msg = &waProto.Message{
			AudioMessage: &waProto.AudioMessage{
				URL:           proto.String(uploaded.URL),
				DirectPath:    proto.String(uploaded.DirectPath),
				MediaKey:      uploaded.MediaKey,
				FileEncSHA256: uploaded.FileEncSHA256,
				FileSHA256:    uploaded.FileSHA256,
				FileLength:    proto.Uint64(uint64(len(mediaData))),
				Mimetype:      proto.String(http.DetectContentType(mediaData)),
			},
		}
	case "document":
		filename := req.Filename
		if filename == "" {
			filename = "document"
		}
		msg = &waProto.Message{
			DocumentMessage: &waProto.DocumentMessage{
				Caption:       caption,
				URL:           proto.String(uploaded.URL),
				DirectPath:    proto.String(uploaded.DirectPath),
				MediaKey:      uploaded.MediaKey,
				FileEncSHA256: uploaded.FileEncSHA256,
				FileSHA256:    uploaded.FileSHA256,
				FileLength:    proto.Uint64(uint64(len(mediaData))),
				Mimetype:      proto.String(http.DetectContentType(mediaData)),
				FileName:      proto.String(filename),
			},
		}
	default:
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Unsupported media type: %s", req.MediaType),
		})
		return
	}

	// Send media message
	sentMsg, err := client.SendMessage(context.Background(), recipientJID, msg)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to send media message: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MessageResponse{
		Success:   true,
		Message:   "Media message sent successfully",
		MessageID: sentMsg.ID,
		Timestamp: sentMsg.Timestamp.Unix(),
	})
}

// handleSendVoice sends a voice note
func handleSendVoice(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req SendVoiceRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Validate request
	if req.Recipient == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Recipient is required",
		})
		return
	}

	if req.AudioPath == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Audio path is required",
		})
		return
	}

	// Parse recipient JID
	recipientJID, err := parseJIDOrPhone(req.Recipient)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid recipient: %v", err),
		})
		return
	}

	// Read audio file
	audioData, err := ioutil.ReadFile(req.AudioPath)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to read audio file: %v", err),
		})
		return
	}

	// Upload audio
	uploaded, err := client.Upload(context.Background(), audioData, whatsmeow.MediaAudio)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to upload audio: %v", err),
		})
		return
	}

	// Create voice message
	msg := &waProto.Message{
		AudioMessage: &waProto.AudioMessage{
			URL:           proto.String(uploaded.URL),
			DirectPath:    proto.String(uploaded.DirectPath),
			MediaKey:      uploaded.MediaKey,
			FileEncSHA256: uploaded.FileEncSHA256,
			FileSHA256:    uploaded.FileSHA256,
			FileLength:    proto.Uint64(uint64(len(audioData))),
			Mimetype:      proto.String("audio/ogg; codecs=opus"),
			PTT:           proto.Bool(true), // Push-to-talk flag for voice notes
		},
	}

	// Send voice message
	sentMsg, err := client.SendMessage(context.Background(), recipientJID, msg)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to send voice message: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MessageResponse{
		Success:   true,
		Message:   "Voice message sent successfully",
		MessageID: sentMsg.ID,
		Timestamp: sentMsg.Timestamp.Unix(),
	})
}

// handleSendSticker sends a sticker
func handleSendSticker(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req SendStickerRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Validate request
	if req.Recipient == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Recipient is required",
		})
		return
	}

	if req.StickerPath == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Sticker path is required",
		})
		return
	}

	// Parse recipient JID
	recipientJID, err := parseJIDOrPhone(req.Recipient)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid recipient: %v", err),
		})
		return
	}

	// Read sticker file
	stickerData, err := ioutil.ReadFile(req.StickerPath)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to read sticker file: %v", err),
		})
		return
	}

	// Upload sticker
	uploaded, err := client.Upload(context.Background(), stickerData, whatsmeow.MediaImage)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to upload sticker: %v", err),
		})
		return
	}

	// Create sticker message
	msg := &waProto.Message{
		StickerMessage: &waProto.StickerMessage{
			URL:           proto.String(uploaded.URL),
			DirectPath:    proto.String(uploaded.DirectPath),
			MediaKey:      uploaded.MediaKey,
			FileEncSHA256: uploaded.FileEncSHA256,
			FileSHA256:    uploaded.FileSHA256,
			FileLength:    proto.Uint64(uint64(len(stickerData))),
			Mimetype:      proto.String("image/webp"),
		},
	}

	// Send sticker message
	sentMsg, err := client.SendMessage(context.Background(), recipientJID, msg)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to send sticker: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MessageResponse{
		Success:   true,
		Message:   "Sticker sent successfully",
		MessageID: sentMsg.ID,
		Timestamp: sentMsg.Timestamp.Unix(),
	})
}

// handleSendContact sends a contact vCard
func handleSendContact(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req SendContactRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Validate request
	if req.Recipient == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Recipient is required",
		})
		return
	}

	if req.VCard == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "VCard is required",
		})
		return
	}

	if req.Name == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Contact name is required",
		})
		return
	}

	// Parse recipient JID
	recipientJID, err := parseJIDOrPhone(req.Recipient)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid recipient: %v", err),
		})
		return
	}

	// Create contact message
	msg := &waProto.Message{
		ContactMessage: &waProto.ContactMessage{
			DisplayName: proto.String(req.Name),
			Vcard:       proto.String(req.VCard),
		},
	}

	// Send contact message
	sentMsg, err := client.SendMessage(context.Background(), recipientJID, msg)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to send contact: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MessageResponse{
		Success:   true,
		Message:   "Contact sent successfully",
		MessageID: sentMsg.ID,
		Timestamp: sentMsg.Timestamp.Unix(),
	})
}

// handleSendLocation sends a location message
func handleSendLocation(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req SendLocationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Validate request
	if req.Recipient == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "Recipient is required",
		})
		return
	}

	// Parse recipient JID
	recipientJID, err := parseJIDOrPhone(req.Recipient)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid recipient: %v", err),
		})
		return
	}

	// Create location message
	msg := &waProto.Message{
		LocationMessage: &waProto.LocationMessage{
			DegreesLatitude:  proto.Float64(req.Latitude),
			DegreesLongitude: proto.Float64(req.Longitude),
			Name:             proto.String(req.Name),
			Address:          proto.String(req.Address),
		},
	}

	// Send location message
	sentMsg, err := client.SendMessage(context.Background(), recipientJID, msg)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to send location: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MessageResponse{
		Success:   true,
		Message:   "Location sent successfully",
		MessageID: sentMsg.ID,
		Timestamp: sentMsg.Timestamp.Unix(),
	})
}

// ReactToMessageRequest represents the request body for reacting to a message
type ReactToMessageRequest struct {
	ChatJID   string `json:"chat_jid"`
	MessageID string `json:"message_id"`
	Emoji     string `json:"emoji"` // Empty string to remove reaction
}

// EditMessageRequest represents the request body for editing a message
type EditMessageRequest struct {
	ChatJID    string `json:"chat_jid"`
	MessageID  string `json:"message_id"`
	NewText    string `json:"new_text"`
	SentTime   int64  `json:"sent_time"` // Unix timestamp of original message
}

// RevokeMessageRequest represents the request body for deleting/revoking a message
type RevokeMessageRequest struct {
	ChatJID   string `json:"chat_jid"`
	MessageID string `json:"message_id"`
	SentTime  int64  `json:"sent_time"` // Unix timestamp of original message
}

// ForwardMessageRequest represents the request body for forwarding a message
type ForwardMessageRequest struct {
	FromChatJID string `json:"from_chat_jid"`
	MessageID   string `json:"message_id"`
	ToChatJID   string `json:"to_chat_jid"`
}

// handleReactToMessage adds or updates an emoji reaction to a message
func handleReactToMessage(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req ReactToMessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Validate request
	if req.ChatJID == "" || req.MessageID == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "chat_jid and message_id are required",
		})
		return
	}

	// Parse chat JID
	chatJID, err := types.ParseJID(req.ChatJID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid chat JID: %v", err),
		})
		return
	}

	// Create reaction message
	reaction := &waProto.ReactionMessage{
		Key: &waProto.MessageKey{
			RemoteJID: proto.String(req.ChatJID),
			ID:        proto.String(req.MessageID),
			FromMe:    proto.Bool(false), // Reacting to someone else's message
		},
		Text:              proto.String(req.Emoji),
		SenderTimestampMS: proto.Int64(time.Now().UnixMilli()),
	}

	msg := &waProto.Message{
		ReactionMessage: reaction,
	}

	// Send reaction
	sentMsg, err := client.SendMessage(context.Background(), chatJID, msg)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to send reaction: %v", err),
		})
		return
	}

	action := "added"
	if req.Emoji == "" {
		action = "removed"
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MessageResponse{
		Success:   true,
		Message:   fmt.Sprintf("Reaction %s successfully", action),
		MessageID: sentMsg.ID,
		Timestamp: sentMsg.Timestamp.Unix(),
	})
}

// handleEditMessage edits a message within the 15-minute window
func handleEditMessage(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req EditMessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Validate request
	if req.ChatJID == "" || req.MessageID == "" || req.NewText == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "chat_jid, message_id, and new_text are required",
		})
		return
	}

	// Check 15-minute window
	if req.SentTime > 0 {
		sentTime := time.Unix(req.SentTime, 0)
		timeSince := time.Since(sentTime)
		if timeSince > 15*time.Minute {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(MessageResponse{
				Success: false,
				Message: fmt.Sprintf("Message edit window expired (15 minutes). Message was sent %v ago", timeSince.Round(time.Second)),
			})
			return
		}
	}

	// Parse chat JID
	chatJID, err := types.ParseJID(req.ChatJID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid chat JID: %v", err),
		})
		return
	}

	// Create edit message
	editMsg := &waProto.Message{
		EditedMessage: &waProto.FutureProofMessage{
			Message: &waProto.Message{
				Conversation: proto.String(req.NewText),
			},
		},
		ProtocolMessage: &waProto.ProtocolMessage{
			Type: waProto.ProtocolMessage_MESSAGE_EDIT.Enum(),
			Key: &waProto.MessageKey{
				RemoteJID: proto.String(req.ChatJID),
				ID:        proto.String(req.MessageID),
				FromMe:    proto.Bool(true),
			},
		},
	}

	// Send edit
	sentMsg, err := client.SendMessage(context.Background(), chatJID, editMsg)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to edit message: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MessageResponse{
		Success:   true,
		Message:   "Message edited successfully",
		MessageID: sentMsg.ID,
		Timestamp: sentMsg.Timestamp.Unix(),
	})
}

// handleRevokeMessage deletes/revokes a message within the 48-hour window
func handleRevokeMessage(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req RevokeMessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Validate request
	if req.ChatJID == "" || req.MessageID == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "chat_jid and message_id are required",
		})
		return
	}

	// Check 48-hour window
	if req.SentTime > 0 {
		sentTime := time.Unix(req.SentTime, 0)
		timeSince := time.Since(sentTime)
		if timeSince > 48*time.Hour {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(MessageResponse{
				Success: false,
				Message: fmt.Sprintf("Message revoke window expired (48 hours). Message was sent %v ago", timeSince.Round(time.Hour)),
			})
			return
		}
	}

	// Parse chat JID
	chatJID, err := types.ParseJID(req.ChatJID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid chat JID: %v", err),
		})
		return
	}

	// Create revoke message
	revokeMsg := &waProto.Message{
		ProtocolMessage: &waProto.ProtocolMessage{
			Type: waProto.ProtocolMessage_REVOKE.Enum(),
			Key: &waProto.MessageKey{
				RemoteJID: proto.String(req.ChatJID),
				ID:        proto.String(req.MessageID),
				FromMe:    proto.Bool(true),
			},
		},
	}

	// Send revoke
	sentMsg, err := client.SendMessage(context.Background(), chatJID, revokeMsg)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to revoke message: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MessageResponse{
		Success:   true,
		Message:   "Message revoked successfully",
		MessageID: sentMsg.ID,
		Timestamp: sentMsg.Timestamp.Unix(),
	})
}

// handleForwardMessage forwards a message to another chat
func handleForwardMessage(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req ForwardMessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Validate request
	if req.FromChatJID == "" || req.MessageID == "" || req.ToChatJID == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "from_chat_jid, message_id, and to_chat_jid are required",
		})
		return
	}

	// Note: Forwarding requires fetching the original message first.
	// For simplicity, we'll create a forward stub that requires the caller
	// to provide the message content separately, or we could fetch it from the database.
	// For now, return a basic implementation that shows the structure.
	// Validation of to_chat_jid would be done here once forwarding is fully implemented.

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNotImplemented)
	json.NewEncoder(w).Encode(MessageResponse{
		Success: false,
		Message: "Message forwarding requires fetching the original message content. Please implement database lookup or pass message content in request.",
	})
}

// handleDownloadMedia downloads and streams media from a message
// Note: DownloadMediaRequest is defined in main.go
func handleDownloadMedia(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	// Parse query parameters
	messageID := r.URL.Query().Get("message_id")
	chatJID := r.URL.Query().Get("chat_jid")

	// Validate parameters
	if messageID == "" || chatJID == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(MessageResponse{
			Success: false,
			Message: "message_id and chat_jid query parameters are required",
		})
		return
	}

	// Note: Full implementation requires database integration to fetch media metadata
	// (URL, MediaKey, FileLength, FileSHA256, FileEncSHA256, etc.) from the messages table.
	//
	// The download flow would be:
	// 1. Query database for media info by message_id and chat_jid
	// 2. Create MediaDownloader with the metadata
	// 3. Call client.Download() with the downloader
	// 4. Stream the media data to the response with correct MIME type
	//
	// For reference, see the downloadMedia function in main.go which implements
	// the full flow with MessageStore integration.

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNotImplemented)
	json.NewEncoder(w).Encode(MessageResponse{
		Success: false,
		Message: "Media download endpoint requires MessageStore integration. Please use the /api/download endpoint from main.go which has full implementation with database support.",
	})
}

// BatchInsertRequest represents the request body for batch inserting messages
type BatchInsertRequest struct {
	Messages []BatchMessage `json:"messages"`
}

// BatchMessage represents a single message in a batch insert
type BatchMessage struct {
	ID              string  `json:"id"`
	ChatJID         string  `json:"chat_jid"`
	Timestamp       int64   `json:"timestamp"`      // Unix timestamp
	Sender          string  `json:"sender"`
	FromMe          bool    `json:"from_me"`
	Content         *string `json:"content,omitempty"`
	MessageType     string  `json:"message_type"`
	PollData        *string `json:"poll_data,omitempty"`
	MediaURL        *string `json:"media_url,omitempty"`
	Reactions       *string `json:"reactions,omitempty"`
	QuotedMessageID *string `json:"quoted_message_id,omitempty"`
	SyncSource      string  `json:"sync_source"`
}

// BatchInsertResponse represents the response for batch insert operations
type BatchInsertResponse struct {
	Success         bool   `json:"success"`
	Message         string `json:"message"`
	InsertedCount   int    `json:"inserted_count"`
	DuplicateCount  int    `json:"duplicate_count"`
	FailedCount     int    `json:"failed_count"`
}

// handleBatchInsertMessages handles batch insertion of messages from Baileys sync
func handleBatchInsertMessages(w http.ResponseWriter, r *http.Request) {
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

	// Get database service from global context
	// Note: This requires the database service to be accessible
	// For now, we'll return not implemented until main.go integration is complete
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNotImplemented)
	json.NewEncoder(w).Encode(BatchInsertResponse{
		Success: false,
		Message: "Batch insert endpoint requires database service integration. Please see main.go for full implementation.",
		InsertedCount: 0,
		DuplicateCount: 0,
		FailedCount: len(req.Messages),
	})
}
