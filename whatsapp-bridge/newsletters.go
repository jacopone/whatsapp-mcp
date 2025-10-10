package main

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"

	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/types"
)

// T054: Newsletter REST Endpoints (Go bridge)

// NewsletterSubscribeRequest represents a subscription request
type NewsletterSubscribeRequest struct {
	JID string `json:"jid"`
}

// NewsletterSubscribeResponse represents subscription response
type NewsletterSubscribeResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
	JID     string `json:"jid,omitempty"`
}

// NewsletterCreateRequest represents a newsletter creation request
type NewsletterCreateRequest struct {
	Name        string `json:"name"`
	Description string `json:"description,omitempty"`
}

// NewsletterCreateResponse represents newsletter creation response
type NewsletterCreateResponse struct {
	Success   bool   `json:"success"`
	Message   string `json:"message"`
	JID       string `json:"jid,omitempty"`
	InviteURL string `json:"invite_url,omitempty"`
}

// NewsletterInfoResponse represents newsletter metadata response
type NewsletterInfoResponse struct {
	Success    bool              `json:"success"`
	Message    string            `json:"message,omitempty"`
	Newsletter *NewsletterInfo   `json:"newsletter,omitempty"`
}

// NewsletterInfo contains newsletter metadata
type NewsletterInfo struct {
	JID              string `json:"jid"`
	Name             string `json:"name"`
	Description      string `json:"description,omitempty"`
	SubscriberCount  int    `json:"subscriber_count,omitempty"`
	CreationTime     int64  `json:"creation_time,omitempty"`
	State            string `json:"state,omitempty"`
	OwnerJID         string `json:"owner_jid,omitempty"`
	Verification     string `json:"verification,omitempty"`
	ViewerMetadata   string `json:"viewer_metadata,omitempty"`
}

// NewsletterReactRequest represents a reaction to a newsletter message
type NewsletterReactRequest struct {
	Emoji string `json:"emoji"`
}

// NewsletterReactResponse represents reaction response
type NewsletterReactResponse struct {
	Success   bool   `json:"success"`
	Message   string `json:"message"`
	MessageID string `json:"message_id,omitempty"`
}

// RegisterNewsletterRoutes sets up HTTP handlers for newsletter endpoints
func RegisterNewsletterRoutes(mux *http.ServeMux, client *whatsmeow.Client) {
	// POST /newsletters/create - Create newsletter
	mux.HandleFunc("/api/newsletters/create", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleCreateNewsletter(w, r, client)
	})

	// Handle newsletter operations with JID path parameter
	mux.HandleFunc("/api/newsletters/", func(w http.ResponseWriter, r *http.Request) {
		path := r.URL.Path
		remainder := path[len("/api/newsletters/"):]

		// Parse path: /api/newsletters/:jid/subscribe OR /api/newsletters/:jid OR /api/newsletters/:jid/messages/:id/react
		parts := strings.Split(remainder, "/")
		if len(parts) == 0 || parts[0] == "" {
			http.Error(w, "Invalid path format", http.StatusBadRequest)
			return
		}

		jidStr := parts[0]

		if len(parts) == 1 {
			// GET /api/newsletters/:jid - Get newsletter metadata
			if r.Method == http.MethodGet {
				handleGetNewsletterInfo(w, r, client, jidStr)
			} else {
				http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			}
			return
		}

		if len(parts) == 2 && parts[1] == "subscribe" {
			// POST /api/newsletters/:jid/subscribe - Subscribe
			if r.Method == http.MethodPost {
				handleSubscribeNewsletter(w, r, client, jidStr)
			} else if r.Method == http.MethodDelete {
				// DELETE /api/newsletters/:jid/subscribe - Unsubscribe
				handleUnsubscribeNewsletter(w, r, client, jidStr)
			} else {
				http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			}
			return
		}

		if len(parts) == 4 && parts[1] == "messages" && parts[3] == "react" {
			// POST /api/newsletters/:jid/messages/:id/react
			if r.Method == http.MethodPost {
				messageID := parts[2]
				handleReactToNewsletterMessage(w, r, client, jidStr, messageID)
			} else {
				http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			}
			return
		}

		http.Error(w, "Invalid path format", http.StatusBadRequest)
	})
}

func handleSubscribeNewsletter(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client, jidStr string) {
	jid, err := types.ParseJID(jidStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(NewsletterSubscribeResponse{
			Success: false,
			Message: "Invalid JID format: " + err.Error(),
		})
		return
	}

	// Subscribe to newsletter using whatsmeow
	err = client.SubscribeNewsletter(jid)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(NewsletterSubscribeResponse{
			Success: false,
			Message: "Failed to subscribe to newsletter: " + err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(NewsletterSubscribeResponse{
		Success: true,
		Message: "Successfully subscribed to newsletter",
		JID:     jid.String(),
	})
}

func handleUnsubscribeNewsletter(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client, jidStr string) {
	jid, err := types.ParseJID(jidStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(NewsletterSubscribeResponse{
			Success: false,
			Message: "Invalid JID format: " + err.Error(),
		})
		return
	}

	// Unsubscribe from newsletter using whatsmeow
	err = client.UnsubscribeNewsletter(jid)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(NewsletterSubscribeResponse{
			Success: false,
			Message: "Failed to unsubscribe from newsletter: " + err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(NewsletterSubscribeResponse{
		Success: true,
		Message: "Successfully unsubscribed from newsletter",
		JID:     jid.String(),
	})
}

func handleCreateNewsletter(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req NewsletterCreateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(NewsletterCreateResponse{
			Success: false,
			Message: "Invalid request body: " + err.Error(),
		})
		return
	}

	if req.Name == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(NewsletterCreateResponse{
			Success: false,
			Message: "Newsletter name is required",
		})
		return
	}

	// Create newsletter using whatsmeow
	newsletterInfo, err := client.CreateNewsletter(types.CreateNewsletterParams{
		Name:        req.Name,
		Description: req.Description,
	})
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(NewsletterCreateResponse{
			Success: false,
			Message: "Failed to create newsletter: " + err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(NewsletterCreateResponse{
		Success:   true,
		Message:   "Newsletter created successfully",
		JID:       newsletterInfo.ID.String(),
		InviteURL: newsletterInfo.InviteCode,
	})
}

func handleGetNewsletterInfo(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client, jidStr string) {
	jid, err := types.ParseJID(jidStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(NewsletterInfoResponse{
			Success: false,
			Message: "Invalid JID format: " + err.Error(),
		})
		return
	}

	// Get newsletter metadata using whatsmeow
	newsletterMeta, err := client.GetNewsletterInfo(jid)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(NewsletterInfoResponse{
			Success: false,
			Message: "Failed to get newsletter info: " + err.Error(),
		})
		return
	}

	if newsletterMeta == nil {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(NewsletterInfoResponse{
			Success:    true,
			Message:    "Newsletter not found",
			Newsletter: nil,
		})
		return
	}

	info := &NewsletterInfo{
		JID:             newsletterMeta.ID.String(),
		Name:            newsletterMeta.ThreadMeta.Name.Text,
		Description:     newsletterMeta.ThreadMeta.Description.Text,
		SubscriberCount: int(newsletterMeta.ThreadMeta.SubscriberCount),
		CreationTime:    newsletterMeta.ThreadMeta.CreationTime,
		State:           string(newsletterMeta.ThreadMeta.Settings.ReactionCodes),
		OwnerJID:        newsletterMeta.ThreadMeta.Owner.String(),
		Verification:    string(newsletterMeta.ViewerMeta.Role),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(NewsletterInfoResponse{
		Success:    true,
		Message:    "Newsletter info retrieved successfully",
		Newsletter: info,
	})
}

func handleReactToNewsletterMessage(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client, jidStr string, messageID string) {
	jid, err := types.ParseJID(jidStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(NewsletterReactResponse{
			Success: false,
			Message: "Invalid JID format: " + err.Error(),
		})
		return
	}

	var req NewsletterReactRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(NewsletterReactResponse{
			Success: false,
			Message: "Invalid request body: " + err.Error(),
		})
		return
	}

	if req.Emoji == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(NewsletterReactResponse{
			Success: false,
			Message: "Emoji is required",
		})
		return
	}

	// React to newsletter message using whatsmeow
	messageKey := types.MessageKey{
		RemoteJID: jid,
		ID:        messageID,
	}

	_, err = client.SendMessage(context.Background(), jid, &types.ReactionMessage{
		Key: messageKey,
		Text: req.Emoji,
	})
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(NewsletterReactResponse{
			Success: false,
			Message: "Failed to react to newsletter message: " + err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(NewsletterReactResponse{
		Success:   true,
		Message:   "Successfully reacted to newsletter message",
		MessageID: messageID,
	})
}
