package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/appstate"
	"go.mau.fi/whatsmeow/types"
)

// ChatListRequest represents query parameters for listing chats
type ChatListRequest struct {
	Limit    int
	Archived bool
}

// ChatMetadataResponse represents chat metadata
type ChatMetadataResponse struct {
	Success   bool      `json:"success"`
	JID       string    `json:"jid"`
	Name      string    `json:"name,omitempty"`
	IsGroup   bool      `json:"is_group"`
	IsPinned  bool      `json:"is_pinned"`
	IsArchived bool     `json:"is_archived"`
	IsMuted   bool      `json:"is_muted"`
	MutedUntil *int64   `json:"muted_until,omitempty"` // Unix timestamp
	LastMessageTime *time.Time `json:"last_message_time,omitempty"`
}

// ChatOperationResponse represents response for chat operations
type ChatOperationResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// RegisterChatRoutes sets up HTTP handlers for chat management endpoints
func RegisterChatRoutes(mux *http.ServeMux, client *whatsmeow.Client) {
	// GET /api/chats/list - List all chats with filters
	mux.HandleFunc("/api/chats/list", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleListChats(w, r, client)
	})

	// GET /api/chats/:jid - Get chat metadata
	mux.HandleFunc("/api/chats/metadata", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleGetChatMetadata(w, r, client)
	})

	// POST /api/chats/archive - Archive chat
	mux.HandleFunc("/api/chats/archive", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleArchiveChat(w, r, client)
	})

	// DELETE /api/chats/archive - Unarchive chat
	mux.HandleFunc("/api/chats/unarchive", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodDelete && r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleUnarchiveChat(w, r, client)
	})

	// POST /api/chats/pin - Pin chat
	mux.HandleFunc("/api/chats/pin", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handlePinChat(w, r, client)
	})

	// DELETE /api/chats/pin - Unpin chat
	mux.HandleFunc("/api/chats/unpin", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodDelete && r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleUnpinChat(w, r, client)
	})

	// POST /api/chats/mute - Mute notifications
	mux.HandleFunc("/api/chats/mute", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleMuteChat(w, r, client)
	})

	// DELETE /api/chats/mute - Unmute notifications
	mux.HandleFunc("/api/chats/unmute", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodDelete && r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleUnmuteChat(w, r, client)
	})
}

// handleListChats lists all chats with optional filters
func handleListChats(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	// Parse query parameters
	limitStr := r.URL.Query().Get("limit")
	archivedStr := r.URL.Query().Get("archived")

	limit := 50 // Default limit
	if limitStr != "" {
		if parsedLimit, err := strconv.Atoi(limitStr); err == nil {
			limit = parsedLimit
		}
	}

	archived := false
	if archivedStr == "true" {
		archived = true
	}

	// Note: whatsmeow doesn't have a direct "list all chats" API.
	// Chats are typically populated from message history or stored in the database.
	// For now, return a stub indicating database integration is needed.

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNotImplemented)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": false,
		"message": fmt.Sprintf("Chat listing requires MessageStore integration. Parameters: limit=%d, archived=%v", limit, archived),
		"note":    "Chats are stored in the messages database. Query the 'chats' table for this functionality.",
	})
}

// handleGetChatMetadata gets metadata for a specific chat
func handleGetChatMetadata(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	// Parse query parameter
	jidStr := r.URL.Query().Get("jid")

	if jidStr == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: "jid query parameter is required",
		})
		return
	}

	// Parse JID
	jid, err := types.ParseJID(jidStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid JID: %v", err),
		})
		return
	}

	// Get chat metadata
	isGroup := jid.Server == "g.us"
	name := jidStr

	// Try to get group metadata if it's a group
	if isGroup {
		groupInfo, err := client.GetGroupInfo(jid)
		if err == nil && groupInfo != nil {
			name = groupInfo.Name
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ChatMetadataResponse{
		Success:  true,
		JID:      jidStr,
		Name:     name,
		IsGroup:  isGroup,
		IsPinned: false, // Would need database lookup
		IsArchived: false, // Would need database lookup
		IsMuted:  false, // Would need database lookup
	})
}

// handleArchiveChat archives a chat
func handleArchiveChat(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req struct {
		JID string `json:"jid"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	if req.JID == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: "jid is required",
		})
		return
	}

	// Parse JID
	jid, err := types.ParseJID(req.JID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid JID: %v", err),
		})
		return
	}

	// Archive the chat using appstate builder
	// Pass current time and nil for message key since we don't have a specific message reference
	err = client.SendAppState(context.Background(), appstate.BuildArchive(jid, true, time.Now(), nil))

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to archive chat: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ChatOperationResponse{
		Success: true,
		Message: fmt.Sprintf("Chat %s archived successfully", req.JID),
	})
}

// handleUnarchiveChat unarchives a chat
func handleUnarchiveChat(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req struct {
		JID string `json:"jid"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	if req.JID == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: "jid is required",
		})
		return
	}

	// Parse JID
	jid, err := types.ParseJID(req.JID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid JID: %v", err),
		})
		return
	}

	// Unarchive the chat using appstate builder
	// Pass current time and nil for message key since we don't have a specific message reference
	err = client.SendAppState(context.Background(), appstate.BuildArchive(jid, false, time.Now(), nil))

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to unarchive chat: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ChatOperationResponse{
		Success: true,
		Message: fmt.Sprintf("Chat %s unarchived successfully", req.JID),
	})
}

// handlePinChat pins a chat
func handlePinChat(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req struct {
		JID string `json:"jid"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	if req.JID == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: "jid is required",
		})
		return
	}

	// Parse JID
	jid, err := types.ParseJID(req.JID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid JID: %v", err),
		})
		return
	}

	// Pin the chat using appstate builder
	err = client.SendAppState(context.Background(), appstate.BuildPin(jid, true))

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to pin chat: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ChatOperationResponse{
		Success: true,
		Message: fmt.Sprintf("Chat %s pinned successfully", req.JID),
	})
}

// handleUnpinChat unpins a chat
func handleUnpinChat(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req struct {
		JID string `json:"jid"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	if req.JID == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: "jid is required",
		})
		return
	}

	// Parse JID
	jid, err := types.ParseJID(req.JID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid JID: %v", err),
		})
		return
	}

	// Unpin the chat using appstate builder
	err = client.SendAppState(context.Background(), appstate.BuildPin(jid, false))

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to unpin chat: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ChatOperationResponse{
		Success: true,
		Message: fmt.Sprintf("Chat %s unpinned successfully", req.JID),
	})
}

// handleMuteChat mutes a chat for a specified duration
func handleMuteChat(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req struct {
		JID             string `json:"jid"`
		DurationSeconds int64  `json:"duration_seconds"` // 0 = mute forever
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	if req.JID == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: "jid is required",
		})
		return
	}

	// Parse JID
	jid, err := types.ParseJID(req.JID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid JID: %v", err),
		})
		return
	}

	// Calculate mute duration
	var duration time.Duration
	if req.DurationSeconds == 0 {
		// Mute forever (use 0 duration as per whatsmeow docs)
		duration = 0
	} else {
		duration = time.Duration(req.DurationSeconds) * time.Second
	}

	// Mute the chat using appstate builder
	err = client.SendAppState(context.Background(), appstate.BuildMute(jid, true, duration))

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to mute chat: %v", err),
		})
		return
	}

	message := fmt.Sprintf("Chat %s muted successfully", req.JID)
	if req.DurationSeconds > 0 {
		message += fmt.Sprintf(" for %d seconds", req.DurationSeconds)
	} else {
		message += " forever"
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ChatOperationResponse{
		Success: true,
		Message: message,
	})
}

// handleUnmuteChat unmutes a chat
func handleUnmuteChat(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req struct {
		JID string `json:"jid"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	if req.JID == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: "jid is required",
		})
		return
	}

	// Parse JID
	jid, err := types.ParseJID(req.JID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid JID: %v", err),
		})
		return
	}

	// Unmute the chat using appstate builder (false = unmute, 0 duration)
	err = client.SendAppState(context.Background(), appstate.BuildMute(jid, false, 0))

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ChatOperationResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to unmute chat: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ChatOperationResponse{
		Success: true,
		Message: fmt.Sprintf("Chat %s unmuted successfully", req.JID),
	})
}
