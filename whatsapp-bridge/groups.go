package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/types"
)

// CreateGroupRequest represents the request body for creating a group
type CreateGroupRequest struct {
	Name         string   `json:"name"`
	Participants []string `json:"participants"` // Array of phone numbers or JIDs
}

// CreateGroupResponse represents the response for creating a group
type CreateGroupResponse struct {
	Success  bool   `json:"success"`
	Message  string `json:"message"`
	GroupJID string `json:"group_jid,omitempty"`
}

// UpdateMetadataRequest represents the request body for updating group metadata
type UpdateMetadataRequest struct {
	Name        string `json:"name,omitempty"`
	Description string `json:"description,omitempty"`
	Picture     string `json:"picture,omitempty"` // Base64 encoded image or file path
}

// UpdateMetadataResponse represents the response for updating group metadata
type UpdateMetadataResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message"`
}

// ParticipantsRequest represents the request body for adding/removing participants
type ParticipantsRequest struct {
	Participants []string `json:"participants"` // Array of phone numbers or JIDs
}

// ParticipantsResponse represents the response for participant operations
type ParticipantsResponse struct {
	Success      bool              `json:"success"`
	Message      string            `json:"message"`
	SuccessCount int               `json:"success_count,omitempty"`
	FailCount    int               `json:"fail_count,omitempty"`
	Results      map[string]string `json:"results,omitempty"` // JID -> status message
}

// GetParticipantsResponse represents the response for listing participants
type GetParticipantsResponse struct {
	Success      bool                 `json:"success"`
	Message      string               `json:"message,omitempty"`
	GroupJID     string               `json:"group_jid"`
	Participants []ParticipantInfo    `json:"participants"`
	Admins       []string             `json:"admins"` // JIDs of admin users
}

// ParticipantInfo represents information about a group participant
type ParticipantInfo struct {
	JID      string `json:"jid"`
	IsAdmin  bool   `json:"is_admin"`
	IsSuperAdmin bool `json:"is_super_admin"`
}

// InviteLinkResponse represents the response for getting an invite link
type InviteLinkResponse struct {
	Success    bool   `json:"success"`
	Message    string `json:"message,omitempty"`
	InviteLink string `json:"invite_link,omitempty"`
	InviteCode string `json:"invite_code,omitempty"`
}

// RegisterGroupRoutes sets up HTTP handlers for group endpoints
func RegisterGroupRoutes(mux *http.ServeMux, client *whatsmeow.Client) {
	// POST /api/groups/create
	mux.HandleFunc("/api/groups/create", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleCreateGroup(w, r, client)
	})

	// Handle all other group endpoints under /api/groups/:jid/
	mux.HandleFunc("/api/groups/", func(w http.ResponseWriter, r *http.Request) {
		// Extract JID from path: /api/groups/{jid}/...
		pathParts := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/groups/"), "/")
		if len(pathParts) < 1 || pathParts[0] == "" || pathParts[0] == "create" {
			http.Error(w, "Group JID required", http.StatusBadRequest)
			return
		}

		groupJID := pathParts[0]

		// Route based on the remaining path
		if len(pathParts) == 1 {
			// /api/groups/:jid
			http.Error(w, "Not found", http.StatusNotFound)
			return
		}

		action := pathParts[1]

		switch action {
		case "metadata":
			// PUT /api/groups/:jid/metadata
			if r.Method == http.MethodPut {
				handleUpdateMetadata(w, r, groupJID, client)
			} else {
				http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			}

		case "participants":
			if len(pathParts) < 3 {
				// GET /api/groups/:jid/participants
				if r.Method == http.MethodGet {
					handleGetParticipants(w, r, groupJID, client)
				} else {
					http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
				}
				return
			}

			subAction := pathParts[2]
			if r.Method != http.MethodPost {
				http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
				return
			}

			switch subAction {
			case "add":
				// POST /api/groups/:jid/participants/add
				handleAddParticipants(w, r, groupJID, client)
			case "remove":
				// POST /api/groups/:jid/participants/remove
				handleRemoveParticipants(w, r, groupJID, client)
			case "promote":
				// POST /api/groups/:jid/participants/promote
				handlePromoteParticipants(w, r, groupJID, client)
			case "demote":
				// POST /api/groups/:jid/participants/demote
				handleDemoteParticipants(w, r, groupJID, client)
			default:
				http.Error(w, "Not found", http.StatusNotFound)
			}

		case "invite":
			if len(pathParts) == 2 {
				// GET /api/groups/:jid/invite
				if r.Method == http.MethodGet {
					handleGetInviteLink(w, r, groupJID, client)
				} else {
					http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
				}
			} else if len(pathParts) == 3 && pathParts[2] == "revoke" {
				// POST /api/groups/:jid/invite/revoke
				if r.Method == http.MethodPost {
					handleRevokeInviteLink(w, r, groupJID, client)
				} else {
					http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
				}
			} else {
				http.Error(w, "Not found", http.StatusNotFound)
			}

		default:
			http.Error(w, "Not found", http.StatusNotFound)
		}
	})
}

// handleCreateGroup creates a new WhatsApp group
func handleCreateGroup(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req CreateGroupRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(CreateGroupResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Validate request
	if req.Name == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(CreateGroupResponse{
			Success: false,
			Message: "Group name is required",
		})
		return
	}

	if len(req.Participants) == 0 {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(CreateGroupResponse{
			Success: false,
			Message: "At least one participant is required",
		})
		return
	}

	// Parse participant JIDs
	participantJIDs := make([]types.JID, 0, len(req.Participants))
	for _, p := range req.Participants {
		jid, err := parseJIDOrPhone(p)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(CreateGroupResponse{
				Success: false,
				Message: fmt.Sprintf("Invalid participant %s: %v", p, err),
			})
			return
		}
		participantJIDs = append(participantJIDs, jid)
	}

	// Create group using whatsmeow
	createResp, err := client.CreateGroup(context.Background(), whatsmeow.ReqCreateGroup{
		Name:         req.Name,
		Participants: participantJIDs,
	})

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(CreateGroupResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to create group: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(CreateGroupResponse{
		Success:  true,
		Message:  "Group created successfully",
		GroupJID: createResp.JID.String(),
	})
}

// handleUpdateMetadata updates group name, description, or picture
func handleUpdateMetadata(w http.ResponseWriter, r *http.Request, groupJIDStr string, client *whatsmeow.Client) {
	var req UpdateMetadataRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(UpdateMetadataResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Parse group JID
	groupJID, err := types.ParseJID(groupJIDStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(UpdateMetadataResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid group JID: %v", err),
		})
		return
	}

	// Update name if provided
	if req.Name != "" {
		err = client.SetGroupName(groupJID, req.Name)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(UpdateMetadataResponse{
				Success: false,
				Message: fmt.Sprintf("Failed to update group name: %v", err),
			})
			return
		}
	}

	// Update description if provided
	if req.Description != "" {
		err = client.SetGroupTopic(groupJID, "", req.Description, "")
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusInternalServerError)
			json.NewEncoder(w).Encode(UpdateMetadataResponse{
				Success: false,
				Message: fmt.Sprintf("Failed to update group description: %v", err),
			})
			return
		}
	}

	// Update picture if provided
	if req.Picture != "" {
		// TODO: Implement picture update
		// This would require reading the image file and uploading it
		// For now, return not implemented
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotImplemented)
		json.NewEncoder(w).Encode(UpdateMetadataResponse{
			Success: false,
			Message: "Picture update not yet implemented",
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(UpdateMetadataResponse{
		Success: true,
		Message: "Group metadata updated successfully",
	})
}

// handleAddParticipants adds participants to a group
func handleAddParticipants(w http.ResponseWriter, r *http.Request, groupJIDStr string, client *whatsmeow.Client) {
	var req ParticipantsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Parse group JID
	groupJID, err := types.ParseJID(groupJIDStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid group JID: %v", err),
		})
		return
	}

	// Parse participant JIDs
	participantJIDs := make([]types.JID, 0, len(req.Participants))
	for _, p := range req.Participants {
		jid, err := parseJIDOrPhone(p)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(ParticipantsResponse{
				Success: false,
				Message: fmt.Sprintf("Invalid participant %s: %v", p, err),
			})
			return
		}
		participantJIDs = append(participantJIDs, jid)
	}

	// Add participants
	addResp, err := client.UpdateGroupParticipants(groupJID, participantJIDs, whatsmeow.ParticipantChangeAdd)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to add participants: %v", err),
		})
		return
	}

	// Process results
	results := make(map[string]string)
	successCount := 0
	failCount := 0

	for _, change := range addResp {
		jidStr := change.JID.String()
		if change.Error == 403 {
			results[jidStr] = "Forbidden (user privacy settings or not on WhatsApp)"
			failCount++
		} else if change.Error == 409 {
			results[jidStr] = "Already in group"
			failCount++
		} else if change.Error != 0 {
			results[jidStr] = fmt.Sprintf("Error code: %d", change.Error)
			failCount++
		} else {
			results[jidStr] = "Added successfully"
			successCount++
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ParticipantsResponse{
		Success:      successCount > 0,
		Message:      fmt.Sprintf("Added %d participants, %d failed", successCount, failCount),
		SuccessCount: successCount,
		FailCount:    failCount,
		Results:      results,
	})
}

// handleRemoveParticipants removes participants from a group
func handleRemoveParticipants(w http.ResponseWriter, r *http.Request, groupJIDStr string, client *whatsmeow.Client) {
	var req ParticipantsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Parse group JID
	groupJID, err := types.ParseJID(groupJIDStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid group JID: %v", err),
		})
		return
	}

	// Parse participant JIDs
	participantJIDs := make([]types.JID, 0, len(req.Participants))
	for _, p := range req.Participants {
		jid, err := parseJIDOrPhone(p)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(ParticipantsResponse{
				Success: false,
				Message: fmt.Sprintf("Invalid participant %s: %v", p, err),
			})
			return
		}
		participantJIDs = append(participantJIDs, jid)
	}

	// Remove participants
	removeResp, err := client.UpdateGroupParticipants(groupJID, participantJIDs, whatsmeow.ParticipantChangeRemove)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to remove participants: %v", err),
		})
		return
	}

	// Process results
	results := make(map[string]string)
	successCount := 0
	failCount := 0

	for _, change := range removeResp {
		jidStr := change.JID.String()
		if change.Error == 404 {
			results[jidStr] = "Not in group"
			failCount++
		} else if change.Error != 0 {
			results[jidStr] = fmt.Sprintf("Error code: %d", change.Error)
			failCount++
		} else {
			results[jidStr] = "Removed successfully"
			successCount++
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ParticipantsResponse{
		Success:      successCount > 0,
		Message:      fmt.Sprintf("Removed %d participants, %d failed", successCount, failCount),
		SuccessCount: successCount,
		FailCount:    failCount,
		Results:      results,
	})
}

// handlePromoteParticipants promotes participants to admins
func handlePromoteParticipants(w http.ResponseWriter, r *http.Request, groupJIDStr string, client *whatsmeow.Client) {
	var req ParticipantsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Parse group JID
	groupJID, err := types.ParseJID(groupJIDStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid group JID: %v", err),
		})
		return
	}

	// Parse participant JIDs
	participantJIDs := make([]types.JID, 0, len(req.Participants))
	for _, p := range req.Participants {
		jid, err := parseJIDOrPhone(p)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(ParticipantsResponse{
				Success: false,
				Message: fmt.Sprintf("Invalid participant %s: %v", p, err),
			})
			return
		}
		participantJIDs = append(participantJIDs, jid)
	}

	// Promote participants
	promoteResp, err := client.UpdateGroupParticipants(groupJID, participantJIDs, whatsmeow.ParticipantChangePromote)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to promote participants: %v", err),
		})
		return
	}

	// Process results
	results := make(map[string]string)
	successCount := 0
	failCount := 0

	for _, change := range promoteResp {
		jidStr := change.JID.String()
		if change.Error != 0 {
			results[jidStr] = fmt.Sprintf("Error code: %d", change.Error)
			failCount++
		} else {
			results[jidStr] = "Promoted to admin successfully"
			successCount++
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ParticipantsResponse{
		Success:      successCount > 0,
		Message:      fmt.Sprintf("Promoted %d participants, %d failed", successCount, failCount),
		SuccessCount: successCount,
		FailCount:    failCount,
		Results:      results,
	})
}

// handleDemoteParticipants demotes participants from admins to regular members
func handleDemoteParticipants(w http.ResponseWriter, r *http.Request, groupJIDStr string, client *whatsmeow.Client) {
	var req ParticipantsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	// Parse group JID
	groupJID, err := types.ParseJID(groupJIDStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid group JID: %v", err),
		})
		return
	}

	// Parse participant JIDs
	participantJIDs := make([]types.JID, 0, len(req.Participants))
	for _, p := range req.Participants {
		jid, err := parseJIDOrPhone(p)
		if err != nil {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusBadRequest)
			json.NewEncoder(w).Encode(ParticipantsResponse{
				Success: false,
				Message: fmt.Sprintf("Invalid participant %s: %v", p, err),
			})
			return
		}
		participantJIDs = append(participantJIDs, jid)
	}

	// Demote participants
	demoteResp, err := client.UpdateGroupParticipants(groupJID, participantJIDs, whatsmeow.ParticipantChangeDemote)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to demote participants: %v", err),
		})
		return
	}

	// Process results
	results := make(map[string]string)
	successCount := 0
	failCount := 0

	for _, change := range demoteResp {
		jidStr := change.JID.String()
		if change.Error != 0 {
			results[jidStr] = fmt.Sprintf("Error code: %d", change.Error)
			failCount++
		} else {
			results[jidStr] = "Demoted to member successfully"
			successCount++
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ParticipantsResponse{
		Success:      successCount > 0,
		Message:      fmt.Sprintf("Demoted %d participants, %d failed", successCount, failCount),
		SuccessCount: successCount,
		FailCount:    failCount,
		Results:      results,
	})
}

// handleGetParticipants lists all participants in a group
func handleGetParticipants(w http.ResponseWriter, r *http.Request, groupJIDStr string, client *whatsmeow.Client) {
	// Parse group JID
	groupJID, err := types.ParseJID(groupJIDStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(GetParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid group JID: %v", err),
		})
		return
	}

	// Get group info to retrieve participants
	groupInfo, err := client.GetGroupInfo(groupJID)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(GetParticipantsResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to get group info: %v", err),
		})
		return
	}

	// Build participant list
	participants := make([]ParticipantInfo, 0, len(groupInfo.Participants))
	admins := make([]string, 0)

	for _, p := range groupInfo.Participants {
		info := ParticipantInfo{
			JID:          p.JID.String(),
			IsAdmin:      p.IsAdmin,
			IsSuperAdmin: p.IsSuperAdmin,
		}
		participants = append(participants, info)

		if p.IsAdmin || p.IsSuperAdmin {
			admins = append(admins, p.JID.String())
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(GetParticipantsResponse{
		Success:      true,
		GroupJID:     groupJIDStr,
		Participants: participants,
		Admins:       admins,
	})
}

// handleGetInviteLink gets the current invite link for a group
func handleGetInviteLink(w http.ResponseWriter, r *http.Request, groupJIDStr string, client *whatsmeow.Client) {
	// Parse group JID
	groupJID, err := types.ParseJID(groupJIDStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(InviteLinkResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid group JID: %v", err),
		})
		return
	}

	// Get invite link
	inviteCode, err := client.GetGroupInviteLink(groupJID, false)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(InviteLinkResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to get invite link: %v", err),
		})
		return
	}

	// Build full invite link
	inviteLink := fmt.Sprintf("https://chat.whatsapp.com/%s", inviteCode)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(InviteLinkResponse{
		Success:    true,
		InviteLink: inviteLink,
		InviteCode: inviteCode,
	})
}

// handleRevokeInviteLink revokes the current invite link and generates a new one
func handleRevokeInviteLink(w http.ResponseWriter, r *http.Request, groupJIDStr string, client *whatsmeow.Client) {
	// Parse group JID
	groupJID, err := types.ParseJID(groupJIDStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(InviteLinkResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid group JID: %v", err),
		})
		return
	}

	// Revoke and get new invite link
	newInviteCode, err := client.GetGroupInviteLink(groupJID, true)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(InviteLinkResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to revoke invite link: %v", err),
		})
		return
	}

	// Build full invite link
	newInviteLink := fmt.Sprintf("https://chat.whatsapp.com/%s", newInviteCode)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(InviteLinkResponse{
		Success:    true,
		Message:    "Invite link revoked and regenerated successfully",
		InviteLink: newInviteLink,
		InviteCode: newInviteCode,
	})
}

// parseJIDOrPhone parses a JID string or phone number and returns a JID
func parseJIDOrPhone(input string) (types.JID, error) {
	// Check if it's already a JID
	if strings.Contains(input, "@") {
		return types.ParseJID(input)
	}

	// Treat as phone number - remove any non-digit characters
	phone := strings.TrimSpace(input)
	phone = strings.ReplaceAll(phone, "+", "")
	phone = strings.ReplaceAll(phone, "-", "")
	phone = strings.ReplaceAll(phone, " ", "")

	// Create JID from phone number
	return types.JID{
		User:   phone,
		Server: "s.whatsapp.net",
	}, nil
}
