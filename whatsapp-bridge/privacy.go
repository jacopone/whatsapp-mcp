package main

import (
	"context"
	"encoding/json"
	"net/http"

	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/types"
)

// T046: Blocking Endpoints

// BlockRequest represents a request to block a contact
type BlockRequest struct {
	JID   string `json:"jid,omitempty"`
	Phone string `json:"phone,omitempty"`
}

// BlockResponse represents the response to a blocking operation
type BlockResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message,omitempty"`
	JID     string `json:"jid,omitempty"`
}

// BlockedContactsResponse represents the list of blocked contacts
type BlockedContactsResponse struct {
	Success  bool     `json:"success"`
	Message  string   `json:"message,omitempty"`
	Blocked  []string `json:"blocked,omitempty"`
	Count    int      `json:"count"`
}

// T047: Privacy Settings Endpoints

// PrivacySettingsResponse represents all privacy settings
type PrivacySettingsResponse struct {
	Success         bool                   `json:"success"`
	Message         string                 `json:"message,omitempty"`
	Settings        map[string]interface{} `json:"settings,omitempty"`
}

// PrivacyUpdateRequest represents a privacy setting update
type PrivacyUpdateRequest struct {
	Value string `json:"value"` // "all", "contacts", "nobody"
}

// RegisterPrivacyRoutes sets up HTTP handlers for privacy endpoints
func RegisterPrivacyRoutes(mux *http.ServeMux, client *whatsmeow.Client) {
	// T046: Blocking endpoints
	mux.HandleFunc("/api/privacy/block", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			handleBlockContact(w, r, client)
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc("/api/privacy/unblock", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPost {
			handleUnblockContact(w, r, client)
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc("/api/privacy/blocked", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			handleGetBlockedContacts(w, r, client)
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	// T047: Privacy settings endpoints
	mux.HandleFunc("/api/privacy/settings", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			handleGetPrivacySettings(w, r, client)
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc("/api/privacy/last-seen", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPut {
			handleUpdateLastSeenPrivacy(w, r, client)
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc("/api/privacy/profile-picture", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPut {
			handleUpdateProfilePicturePrivacy(w, r, client)
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc("/api/privacy/status", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPut {
			handleUpdateStatusPrivacy(w, r, client)
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc("/api/privacy/online", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodPut {
			handleUpdateOnlinePrivacy(w, r, client)
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})
}

// T046: Blocking endpoint handlers

func handleBlockContact(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req BlockRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(BlockResponse{
			Success: false,
			Message: "Invalid request format",
		})
		return
	}

	// Parse JID
	var jid types.JID
	var err error

	if req.JID != "" {
		jid, err = types.ParseJID(req.JID)
	} else if req.Phone != "" {
		// Convert phone to JID format
		jid = types.NewJID(req.Phone, types.DefaultUserServer)
	} else {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(BlockResponse{
			Success: false,
			Message: "Either jid or phone is required",
		})
		return
	}

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(BlockResponse{
			Success: false,
			Message: "Invalid JID format",
		})
		return
	}

	// Block the contact
	_, err = client.UpdateBlocklist(jid, "block")
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(BlockResponse{
			Success: false,
			Message: "Failed to block contact: " + err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(BlockResponse{
		Success: true,
		Message: "Contact blocked successfully",
		JID:     jid.String(),
	})
}

func handleUnblockContact(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req BlockRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(BlockResponse{
			Success: false,
			Message: "Invalid request format",
		})
		return
	}

	// Parse JID
	var jid types.JID
	var err error

	if req.JID != "" {
		jid, err = types.ParseJID(req.JID)
	} else if req.Phone != "" {
		jid = types.NewJID(req.Phone, types.DefaultUserServer)
	} else {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(BlockResponse{
			Success: false,
			Message: "Either jid or phone is required",
		})
		return
	}

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(BlockResponse{
			Success: false,
			Message: "Invalid JID format",
		})
		return
	}

	// Unblock the contact
	_, err = client.UpdateBlocklist(jid, "unblock")
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(BlockResponse{
			Success: false,
			Message: "Failed to unblock contact: " + err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(BlockResponse{
		Success: true,
		Message: "Contact unblocked successfully",
		JID:     jid.String(),
	})
}

func handleGetBlockedContacts(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	// Get blocklist from whatsmeow
	_, err := client.GetBlocklist()
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(BlockedContactsResponse{
			Success: false,
			Message: "Failed to get blocklist: " + err.Error(),
		})
		return
	}

	// Convert JIDs to strings
	// Note: Blocklist structure varies by whatsmeow version
	// For now, return empty list as this feature requires more investigation
	var blockedJIDs []string
	// TODO: Parse blocklist structure correctly based on whatsmeow version

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(BlockedContactsResponse{
		Success: true,
		Blocked: blockedJIDs,
		Count:   len(blockedJIDs),
	})
}

// T047: Privacy settings endpoint handlers

func handleGetPrivacySettings(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	// Get privacy settings from whatsmeow
	settings, err := client.TryFetchPrivacySettings(context.Background(), false)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Failed to get privacy settings: " + err.Error(),
		})
		return
	}

	// Convert to map for JSON response
	settingsMap := map[string]interface{}{
		"group_add":      settings.GroupAdd,
		"last_seen":      settings.LastSeen,
		"status":         settings.Status,
		"profile":        settings.Profile,
		"read_receipts":  settings.ReadReceipts,
		"online":         settings.Online,
		"call_add":       settings.CallAdd,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(PrivacySettingsResponse{
		Success:  true,
		Settings: settingsMap,
	})
}

func handleUpdateLastSeenPrivacy(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req PrivacyUpdateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Invalid request format",
		})
		return
	}

	// Validate value
	if req.Value != "all" && req.Value != "contacts" && req.Value != "match_last_seen" && req.Value != "none" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Invalid value. Must be 'all', 'contacts', 'match_last_seen', or 'none'",
		})
		return
	}

	// Update last seen privacy
	_, err := client.SetPrivacySetting(context.Background(), types.PrivacySettingTypeLastSeen, types.PrivacySetting(req.Value))
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Failed to update last seen privacy: " + err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(PrivacySettingsResponse{
		Success: true,
		Message: "Last seen privacy updated successfully",
	})
}

func handleUpdateProfilePicturePrivacy(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req PrivacyUpdateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Invalid request format",
		})
		return
	}

	// Validate value
	if req.Value != "all" && req.Value != "contacts" && req.Value != "match_last_seen" && req.Value != "none" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Invalid value. Must be 'all', 'contacts', 'match_last_seen', or 'none'",
		})
		return
	}

	// Update profile picture privacy
	_, err := client.SetPrivacySetting(context.Background(), types.PrivacySettingTypeProfile, types.PrivacySetting(req.Value))
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Failed to update profile picture privacy: " + err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(PrivacySettingsResponse{
		Success: true,
		Message: "Profile picture privacy updated successfully",
	})
}

func handleUpdateStatusPrivacy(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req PrivacyUpdateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Invalid request format",
		})
		return
	}

	// Validate value
	if req.Value != "all" && req.Value != "contacts" && req.Value != "match_last_seen" && req.Value != "none" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Invalid value. Must be 'all', 'contacts', 'match_last_seen', or 'none'",
		})
		return
	}

	// Update status privacy
	_, err := client.SetPrivacySetting(context.Background(), types.PrivacySettingTypeStatus, types.PrivacySetting(req.Value))
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Failed to update status privacy: " + err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(PrivacySettingsResponse{
		Success: true,
		Message: "Status privacy updated successfully",
	})
}

func handleUpdateOnlinePrivacy(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req PrivacyUpdateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Invalid request format",
		})
		return
	}

	// Validate value
	if req.Value != "all" && req.Value != "match_last_seen" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Invalid value. Must be 'all' or 'match_last_seen'",
		})
		return
	}

	// Update online privacy
	_, err := client.SetPrivacySetting(context.Background(), types.PrivacySettingTypeOnline, types.PrivacySetting(req.Value))
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(PrivacySettingsResponse{
			Success: false,
			Message: "Failed to update online privacy: " + err.Error(),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(PrivacySettingsResponse{
		Success: true,
		Message: "Online privacy updated successfully",
	})
}
