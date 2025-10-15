package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/types"
)

// CommunityInfo represents metadata about a community
type CommunityInfo struct {
	JID        string    `json:"jid"`
	Name       string    `json:"name"`
	GroupCount int       `json:"group_count"`
	LastUpdate time.Time `json:"last_update,omitempty"`
}

// CommunityListResponse represents the response for listing communities
type CommunityListResponse struct {
	Success     bool            `json:"success"`
	Message     string          `json:"message,omitempty"`
	Communities []CommunityInfo `json:"communities"`
	Total       int             `json:"total"`
}

// CommunityGroupsResponse represents the response for getting community groups
type CommunityGroupsResponse struct {
	Success      bool                     `json:"success"`
	Message      string                   `json:"message,omitempty"`
	CommunityJID string                   `json:"community_jid"`
	Groups       []map[string]interface{} `json:"groups"`
	Total        int                      `json:"total"`
}

// MarkCommunityReadResponse represents the response for marking a community as read
type MarkCommunityReadResponse struct {
	Success       bool                       `json:"success"`
	Message       string                     `json:"message"`
	SuccessCount  int                        `json:"success_count"`
	FailCount     int                        `json:"fail_count"`
	SkippedCount  int                        `json:"skipped_count"`
	GroupResults  map[string]GroupMarkResult `json:"group_results"`
}

// GroupMarkResult represents the result of marking a single group as read
type GroupMarkResult struct {
	Success      bool   `json:"success"`
	Message      string `json:"message"`
	MessageCount int    `json:"message_count"`
	Skipped      bool   `json:"skipped"`
}

// RegisterCommunityRoutes sets up HTTP handlers for community endpoints
func RegisterCommunityRoutes(mux *http.ServeMux, client *whatsmeow.Client, messageStore *MessageStore) {
	// GET /api/communities/list
	mux.HandleFunc("/api/communities/list", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		handleListCommunities(w, r, messageStore)
	})

	// GET /api/communities/{jid}
	mux.HandleFunc("/api/communities/", func(w http.ResponseWriter, r *http.Request) {
		// Extract JID from path
		jid := r.URL.Path[len("/api/communities/"):]

		if jid == "" || jid == "list" {
			// This is handled by the list endpoint
			return
		}

		if r.Method == http.MethodGet {
			// Check if this is asking for groups
			if len(r.URL.Path) > len("/api/communities/"+jid+"/groups") &&
				r.URL.Path[len("/api/communities/"+jid):len("/api/communities/"+jid+"/groups")] == "/groups" {
				handleGetCommunityGroups(w, r, jid, messageStore)
			} else {
				handleGetCommunityMetadata(w, r, jid, messageStore)
			}
		} else if r.Method == http.MethodPost {
			// Check if this is mark-read endpoint
			if len(r.URL.Path) > len("/api/communities/"+jid+"/mark-read") &&
				r.URL.Path[len("/api/communities/"+jid):] == "/mark-read" {
				handleMarkCommunityRead(w, r, jid, client, messageStore)
			} else {
				http.Error(w, "Not found", http.StatusNotFound)
			}
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})
}

// handleListCommunities returns all communities from the database
func handleListCommunities(w http.ResponseWriter, r *http.Request, messageStore *MessageStore) {
	query := r.URL.Query().Get("query")
	limitStr := r.URL.Query().Get("limit")

	limit := 20 // Default limit
	if limitStr != "" {
		if l, err := strconv.Atoi(limitStr); err == nil && l > 0 {
			limit = l
		}
	}

	// Query database for communities (parent groups)
	// Communities are identified by having other groups with parent_group_jid pointing to them
	sqlQuery := `
		SELECT
			c.jid,
			c.name,
			COUNT(DISTINCT g.jid) as group_count,
			MAX(c.last_message_time) as last_update
		FROM chats c
		LEFT JOIN chats g ON g.parent_group_jid = c.jid
		WHERE c.jid IN (SELECT DISTINCT parent_group_jid FROM chats WHERE parent_group_jid IS NOT NULL AND parent_group_jid != '')
	`

	args := []interface{}{}

	if query != "" {
		sqlQuery += " AND (LOWER(c.name) LIKE LOWER(?) OR c.jid LIKE ?)"
		searchPattern := "%" + query + "%"
		args = append(args, searchPattern, searchPattern)
	}

	sqlQuery += " GROUP BY c.jid, c.name ORDER BY c.name LIMIT ?"
	args = append(args, limit)

	rows, err := messageStore.db.Query(sqlQuery, args...)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(CommunityListResponse{
			Success: false,
			Message: fmt.Sprintf("Database error: %v", err),
		})
		return
	}
	defer rows.Close()

	communities := []CommunityInfo{}
	for rows.Next() {
		var comm CommunityInfo
		var lastUpdate sql.NullTime

		err := rows.Scan(&comm.JID, &comm.Name, &comm.GroupCount, &lastUpdate)
		if err != nil {
			continue
		}

		if lastUpdate.Valid {
			comm.LastUpdate = lastUpdate.Time
		}

		communities = append(communities, comm)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(CommunityListResponse{
		Success:     true,
		Communities: communities,
		Total:       len(communities),
	})
}

// handleGetCommunityMetadata returns metadata for a specific community
func handleGetCommunityMetadata(w http.ResponseWriter, r *http.Request, jid string, messageStore *MessageStore) {
	// Query database for community info
	var name string
	var lastMessageTime sql.NullTime

	err := messageStore.db.QueryRow(
		"SELECT name, last_message_time FROM chats WHERE jid = ?",
		jid,
	).Scan(&name, &lastMessageTime)

	if err == sql.ErrNoRows {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"message": "Community not found",
		})
		return
	}

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"message": fmt.Sprintf("Database error: %v", err),
		})
		return
	}

	// Get group count
	var groupCount int
	err = messageStore.db.QueryRow(
		"SELECT COUNT(*) FROM chats WHERE parent_group_jid = ?",
		jid,
	).Scan(&groupCount)

	if err != nil {
		groupCount = 0
	}

	comm := CommunityInfo{
		JID:        jid,
		Name:       name,
		GroupCount: groupCount,
	}

	if lastMessageTime.Valid {
		comm.LastUpdate = lastMessageTime.Time
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success":   true,
		"community": comm,
	})
}

// handleGetCommunityGroups returns all groups belonging to a community
func handleGetCommunityGroups(w http.ResponseWriter, r *http.Request, communityJID string, messageStore *MessageStore) {
	limitStr := r.URL.Query().Get("limit")

	limit := 100 // Default limit
	if limitStr != "" {
		if l, err := strconv.Atoi(limitStr); err == nil && l > 0 {
			limit = l
		}
	}

	// Query database for groups in this community
	rows, err := messageStore.db.Query(`
		SELECT jid, name, last_message_time, parent_group_jid
		FROM chats
		WHERE parent_group_jid = ?
		ORDER BY name
		LIMIT ?
	`, communityJID, limit)

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(CommunityGroupsResponse{
			Success: false,
			Message: fmt.Sprintf("Database error: %v", err),
		})
		return
	}
	defer rows.Close()

	groups := []map[string]interface{}{}
	for rows.Next() {
		var jid, name string
		var parentGroupJID sql.NullString
		var lastMessageTime sql.NullTime

		err := rows.Scan(&jid, &name, &lastMessageTime, &parentGroupJID)
		if err != nil {
			continue
		}

		group := map[string]interface{}{
			"jid":  jid,
			"name": name,
		}

		if lastMessageTime.Valid {
			group["last_message_time"] = lastMessageTime.Time
		}

		if parentGroupJID.Valid {
			group["parent_group_jid"] = parentGroupJID.String
		}

		groups = append(groups, group)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(CommunityGroupsResponse{
		Success:      true,
		CommunityJID: communityJID,
		Groups:       groups,
		Total:        len(groups),
	})
}

// handleMarkCommunityRead marks all messages in all groups of a community as read
func handleMarkCommunityRead(w http.ResponseWriter, r *http.Request, communityJID string, client *whatsmeow.Client, messageStore *MessageStore) {
	// Get all groups in the community
	rows, err := messageStore.db.Query(`
		SELECT jid, name
		FROM chats
		WHERE parent_group_jid = ?
		ORDER BY name
	`, communityJID)

	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(MarkCommunityReadResponse{
			Success: false,
			Message: fmt.Sprintf("Database error: %v", err),
		})
		return
	}
	defer rows.Close()

	// Collect all groups
	type groupInfo struct {
		JID  string
		Name string
	}

	groups := []groupInfo{}
	for rows.Next() {
		var g groupInfo
		if err := rows.Scan(&g.JID, &g.Name); err == nil {
			groups = append(groups, g)
		}
	}

	if len(groups) == 0 {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(MarkCommunityReadResponse{
			Success: false,
			Message: "No groups found in community",
		})
		return
	}

	// Process each group with continue-on-error pattern
	results := make(map[string]GroupMarkResult)
	successCount := 0
	failCount := 0
	skippedCount := 0

	for _, group := range groups {
		// Get messages for this group
		msgRows, err := messageStore.db.Query(`
			SELECT id, sender
			FROM messages
			WHERE chat_jid = ? AND is_from_me = 0
			ORDER BY timestamp DESC
			LIMIT 1000
		`, group.JID)

		if err != nil {
			results[group.Name] = GroupMarkResult{
				Success: false,
				Message: fmt.Sprintf("Database error: %v", err),
				Skipped: false,
			}
			failCount++
			continue
		}

		messageIDs := []types.MessageID{}
		var senderJID types.JID
		hasMessages := false

		for msgRows.Next() {
			var msgID, sender string
			if err := msgRows.Scan(&msgID, &sender); err == nil {
				messageIDs = append(messageIDs, types.MessageID(msgID))
				if !hasMessages {
					// Parse sender for the first message (needed for group chats)
					if parsed, err := types.ParseJID(sender); err == nil {
						senderJID = parsed
					}
					hasMessages = true
				}
			}
		}
		msgRows.Close()

		if !hasMessages {
			results[group.Name] = GroupMarkResult{
				Success: true,
				Message: "No messages to mark",
				Skipped: true,
			}
			skippedCount++
			continue
		}

		// Parse group JID
		groupJID, err := types.ParseJID(group.JID)
		if err != nil {
			results[group.Name] = GroupMarkResult{
				Success: false,
				Message: fmt.Sprintf("Invalid group JID: %v", err),
				Skipped: false,
			}
			failCount++
			continue
		}

		// Mark messages as read
		err = client.MarkRead(messageIDs, time.Now(), groupJID, senderJID)
		if err != nil {
			results[group.Name] = GroupMarkResult{
				Success:      false,
				Message:      fmt.Sprintf("Failed to mark as read: %v", err),
				MessageCount: len(messageIDs),
				Skipped:      false,
			}
			failCount++
		} else {
			results[group.Name] = GroupMarkResult{
				Success:      true,
				Message:      "Marked as read",
				MessageCount: len(messageIDs),
				Skipped:      false,
			}
			successCount++
		}
	}

	// Build overall message
	overallMessage := fmt.Sprintf("Marked %d groups as read", successCount)
	if failCount > 0 {
		overallMessage += fmt.Sprintf(", %d groups failed", failCount)
	}
	if skippedCount > 0 {
		overallMessage += fmt.Sprintf(", %d groups skipped (no messages)", skippedCount)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MarkCommunityReadResponse{
		Success:      successCount > 0,
		Message:      overallMessage,
		SuccessCount: successCount,
		FailCount:    failCount,
		SkippedCount: skippedCount,
		GroupResults: results,
	})
}
