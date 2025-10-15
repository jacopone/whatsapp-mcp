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

// ContactSearchResponse represents search results
type ContactSearchResponse struct {
	Success  bool      `json:"success"`
	Message  string    `json:"message,omitempty"`
	Contacts []Contact `json:"contacts,omitempty"`
	Count    int       `json:"count"`
}

// Contact represents a WhatsApp contact
type Contact struct {
	JID          string `json:"jid"`
	Name         string `json:"name,omitempty"`
	PhoneNumber  string `json:"phone_number,omitempty"`
	PushName     string `json:"push_name,omitempty"`
	BusinessName string `json:"business_name,omitempty"`
}

// ContactDetailsResponse represents contact details
type ContactDetailsResponse struct {
	Success      bool   `json:"success"`
	Message      string `json:"message,omitempty"`
	JID          string `json:"jid"`
	Name         string `json:"name,omitempty"`
	PhoneNumber  string `json:"phone_number,omitempty"`
	PushName     string `json:"push_name,omitempty"`
	BusinessName string `json:"business_name,omitempty"`
	IsOnWhatsApp bool   `json:"is_on_whatsapp"`
}

// IsOnWhatsAppResponse represents WhatsApp check result
type IsOnWhatsAppResponse struct {
	Success      bool   `json:"success"`
	Message      string `json:"message,omitempty"`
	PhoneNumber  string `json:"phone_number"`
	IsOnWhatsApp bool   `json:"is_on_whatsapp"`
	JID          string `json:"jid,omitempty"`
}

// ProfilePictureResponse represents profile picture URL
type ProfilePictureResponse struct {
	Success bool   `json:"success"`
	Message string `json:"message,omitempty"`
	JID     string `json:"jid"`
	URL     string `json:"url,omitempty"`
}

// StatusResponse represents status message
type StatusResponse struct {
	Success    bool   `json:"success"`
	Message    string `json:"message,omitempty"`
	JID        string `json:"jid"`
	StatusText string `json:"status_text,omitempty"`
}

// LinkedDevicesResponse represents linked devices
type LinkedDevicesResponse struct {
	Success bool           `json:"success"`
	Message string         `json:"message,omitempty"`
	Devices []LinkedDevice `json:"devices,omitempty"`
}

// LinkedDevice represents a linked WhatsApp device
type LinkedDevice struct {
	JID       string `json:"jid"`
	Platform  string `json:"platform"`
	Name      string `json:"name,omitempty"`
	Connected bool   `json:"connected"`
}

// RegisterContactRoutes sets up HTTP handlers for contact endpoints
func RegisterContactRoutes(mux *http.ServeMux, client *whatsmeow.Client) {
	// GET /contacts/search - Search contacts by name/phone
	mux.HandleFunc("/api/contacts/search", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleSearchContacts(w, r, client)
	})

	// GET /contacts/:jid - Get contact details
	mux.HandleFunc("/api/contacts/details", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleGetContactDetails(w, r, client)
	})

	// GET /contacts/:jid/is-on-whatsapp - Check if on WhatsApp
	mux.HandleFunc("/api/contacts/is-on-whatsapp", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleIsOnWhatsApp(w, r, client)
	})

	// GET /contacts/:jid/profile-picture - Get profile picture URL
	mux.HandleFunc("/api/contacts/profile-picture", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleGetProfilePicture(w, r, client)
	})

	// PUT /profile/picture - Update own profile picture
	mux.HandleFunc("/api/profile/picture", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPut && r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleUpdateProfilePicture(w, r, client)
	})

	// GET /contacts/:jid/status - Get status message
	mux.HandleFunc("/api/contacts/status", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleGetStatus(w, r, client)
	})

	// PUT /profile/status - Update own status message
	mux.HandleFunc("/api/profile/status", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPut && r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleUpdateStatus(w, r, client)
	})

	// GET /contacts/linked-devices - Get linked devices
	mux.HandleFunc("/api/contacts/linked-devices", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		handleGetLinkedDevices(w, r, client)
	})
}

// handleSearchContacts searches contacts by name or phone number
func handleSearchContacts(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	query := r.URL.Query().Get("query")

	if query == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ContactSearchResponse{
			Success: false,
			Message: "query parameter is required",
		})
		return
	}

	// Get all contacts from store
	allContacts, err := client.Store.Contacts.GetAllContacts(context.Background())
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ContactSearchResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to get contacts: %v", err),
		})
		return
	}

	// Filter contacts by query (case-insensitive search in name and phone)
	var matchingContacts []Contact
	queryLower := strings.ToLower(query)

	for jid, contact := range allContacts {
		fullName := contact.FullName
		businessName := contact.BusinessName
		phoneNumber := jid.User

		nameMatch := strings.Contains(strings.ToLower(fullName), queryLower)
		businessMatch := strings.Contains(strings.ToLower(businessName), queryLower)
		phoneMatch := strings.Contains(phoneNumber, query)

		if nameMatch || businessMatch || phoneMatch {
			matchingContacts = append(matchingContacts, Contact{
				JID:          jid.String(),
				Name:         fullName,
				PhoneNumber:  phoneNumber,
				PushName:     contact.PushName,
				BusinessName: businessName,
			})
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ContactSearchResponse{
		Success:  true,
		Contacts: matchingContacts,
		Count:    len(matchingContacts),
	})
}

// handleGetContactDetails gets contact details by JID
func handleGetContactDetails(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	jidStr := r.URL.Query().Get("jid")

	if jidStr == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ContactDetailsResponse{
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
		json.NewEncoder(w).Encode(ContactDetailsResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid JID: %v", err),
		})
		return
	}

	// Get contact from store
	contact, err := client.Store.Contacts.GetContact(context.Background(), jid)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ContactDetailsResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to get contact: %v", err),
		})
		return
	}

	// Check if contact is on WhatsApp (optional, may require additional API call)
	isOnWhatsApp := true // Assume true if we have contact info

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ContactDetailsResponse{
		Success:      true,
		JID:          jidStr,
		Name:         contact.FullName,
		PhoneNumber:  jid.User,
		PushName:     contact.PushName,
		BusinessName: contact.BusinessName,
		IsOnWhatsApp: isOnWhatsApp,
	})
}

// handleIsOnWhatsApp checks if a phone number is on WhatsApp
func handleIsOnWhatsApp(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	phone := r.URL.Query().Get("phone")

	if phone == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(IsOnWhatsAppResponse{
			Success: false,
			Message: "phone query parameter is required",
		})
		return
	}

	// Clean phone number (remove non-digits)
	cleanPhone := strings.Map(func(r rune) rune {
		if r >= '0' && r <= '9' {
			return r
		}
		return -1
	}, phone)

	// Use whatsmeow IsOnWhatsApp API
	result, err := client.IsOnWhatsApp([]string{cleanPhone})
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(IsOnWhatsAppResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to check WhatsApp status: %v", err),
		})
		return
	}

	// Check result
	isOnWA := false
	jidStr := ""
	if len(result) > 0 && result[0].IsIn {
		isOnWA = true
		jidStr = result[0].JID.String()
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(IsOnWhatsAppResponse{
		Success:      true,
		PhoneNumber:  phone,
		IsOnWhatsApp: isOnWA,
		JID:          jidStr,
	})
}

// handleGetProfilePicture gets profile picture URL for a contact
func handleGetProfilePicture(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	jidStr := r.URL.Query().Get("jid")

	if jidStr == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ProfilePictureResponse{
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
		json.NewEncoder(w).Encode(ProfilePictureResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid JID: %v", err),
		})
		return
	}

	// Get profile picture URL
	picInfo, err := client.GetProfilePictureInfo(jid, nil)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ProfilePictureResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to get profile picture: %v", err),
		})
		return
	}

	picURL := ""
	if picInfo != nil {
		picURL = picInfo.URL
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ProfilePictureResponse{
		Success: true,
		JID:     jidStr,
		URL:     picURL,
	})
}

// handleUpdateProfilePicture updates own profile picture
func handleUpdateProfilePicture(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req struct {
		ImagePath string `json:"image_path"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"message": fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	if req.ImagePath == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"message": "image_path is required",
		})
		return
	}

	// Note: whatsmeow doesn't have a SetProfilePicture API for user accounts
	// Only SetGroupPhoto exists for groups
	// This endpoint would require implementation via direct WhatsApp protocol
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNotImplemented)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": false,
		"message": "Setting user profile picture not directly supported by whatsmeow. Only group photos can be set via SetGroupPhoto.",
	})
}

// handleGetStatus gets status message for a contact
func handleGetStatus(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	jidStr := r.URL.Query().Get("jid")

	if jidStr == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(StatusResponse{
			Success: false,
			Message: "jid query parameter is required",
		})
		return
	}

	// Parse JID to validate format
	_, err := types.ParseJID(jidStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(StatusResponse{
			Success: false,
			Message: fmt.Sprintf("Invalid JID: %v", err),
		})
		return
	}

	// Note: whatsmeow doesn't have a direct GetStatus API
	// Status messages are typically received via presence updates
	// For now, return a stub indicating this limitation
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusNotImplemented)
	json.NewEncoder(w).Encode(StatusResponse{
		Success: false,
		Message: "Getting contact status not directly supported by whatsmeow. Status messages are received via presence updates.",
		JID:     jidStr,
	})
}

// handleUpdateStatus updates own status message
func handleUpdateStatus(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	var req struct {
		StatusText string `json:"status_text"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"message": fmt.Sprintf("Invalid request format: %v", err),
		})
		return
	}

	if req.StatusText == "" {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"message": "status_text is required",
		})
		return
	}

	// Set status/about text
	err := client.SetStatusMessage(req.StatusText)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"message": fmt.Sprintf("Failed to set status message: %v", err),
		})
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "Status message updated successfully",
		"status_text": req.StatusText,
	})
}

// handleGetLinkedDevices gets list of linked WhatsApp devices
func handleGetLinkedDevices(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client) {
	// Get linked devices (using GetUserDevicesContext with correct signature)
	devices, err := client.GetUserDevicesContext(context.Background(), []types.JID{*client.Store.ID}, false)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(LinkedDevicesResponse{
			Success: false,
			Message: fmt.Sprintf("Failed to get linked devices: %v", err),
		})
		return
	}

	// Convert to response format
	var linkedDevices []LinkedDevice
	for _, device := range devices {
		platform := "Unknown"
		// Determine platform from device ID
		if device.Device == 0 {
			platform = "Mobile"
		} else {
			platform = fmt.Sprintf("Companion-%d", device.Device)
		}

		linkedDevices = append(linkedDevices, LinkedDevice{
			JID:       device.String(),
			Platform:  platform,
			Connected: true, // Assume connected if listed
		})
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(LinkedDevicesResponse{
		Success: true,
		Devices: linkedDevices,
	})
}
