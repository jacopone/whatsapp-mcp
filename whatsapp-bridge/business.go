package main

import (
	"encoding/json"
	"net/http"

	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/types"
)

// T051: Business Profile Endpoint

// BusinessProfileResponse represents a business account profile
type BusinessProfileResponse struct {
	Success     bool                   `json:"success"`
	Message     string                 `json:"message,omitempty"`
	Profile     *BusinessProfile       `json:"profile,omitempty"`
}

// BusinessProfile contains business account information
type BusinessProfile struct {
	JID         string  `json:"jid"`
	Description *string `json:"description,omitempty"`
	Category    *string `json:"category,omitempty"`
	Address     *string `json:"address,omitempty"`
	Website     *string `json:"website,omitempty"`
	Email       *string `json:"email,omitempty"`
	// Note: hours field would require parsing from whatsmeow business info structure
}

// RegisterBusinessRoutes sets up HTTP handlers for business endpoints
func RegisterBusinessRoutes(mux *http.ServeMux, client *whatsmeow.Client) {
	// T051: Business profile endpoint
	mux.HandleFunc("/api/business/", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodGet {
			// Parse JID from path: /api/business/:jid/profile
			// Expected format: /api/business/1234567890@s.whatsapp.net/profile
			path := r.URL.Path

			// Simple path parsing
			if len(path) < len("/api/business/") {
				http.Error(w, "Invalid path", http.StatusBadRequest)
				return
			}

			// Extract JID and action
			remainder := path[len("/api/business/"):]
			// Find last slash to separate JID from action
			lastSlash := -1
			for i := len(remainder) - 1; i >= 0; i-- {
				if remainder[i] == '/' {
					lastSlash = i
					break
				}
			}

			if lastSlash == -1 {
				http.Error(w, "Invalid path format", http.StatusBadRequest)
				return
			}

			jidStr := remainder[:lastSlash]
			action := remainder[lastSlash+1:]

			if action == "profile" {
				handleGetBusinessProfile(w, r, client, jidStr)
			} else {
				http.Error(w, "Unknown action", http.StatusNotFound)
			}
		} else {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})
}

func handleGetBusinessProfile(w http.ResponseWriter, r *http.Request, client *whatsmeow.Client, jidStr string) {
	// Parse JID
	jid, err := types.ParseJID(jidStr)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(BusinessProfileResponse{
			Success: false,
			Message: "Invalid JID format: " + err.Error(),
		})
		return
	}

	// Get business profile from whatsmeow
	businessInfo, err := client.GetBusinessProfile(jid)
	if err != nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(BusinessProfileResponse{
			Success: false,
			Message: "Failed to get business profile: " + err.Error(),
		})
		return
	}

	// Handle non-business accounts gracefully
	if businessInfo == nil {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(BusinessProfileResponse{
			Success: true,
			Message: "Contact is not a business account",
			Profile: nil,
		})
		return
	}

	// Convert to our response format
	// Note: BusinessProfile has Address, Email, Categories, ProfileOptions, BusinessHoursTimeZone, BusinessHours
	// We'll populate Category from the first category's Name field
	var description *string
	var category *string
	if len(businessInfo.Categories) > 0 {
		// Category struct has ID and Name fields
		cat := businessInfo.Categories[0].Name
		category = &cat
	}

	profile := &BusinessProfile{
		JID:         jid.String(),
		Description: description, // Not directly available in whatsmeow BusinessProfile
		Category:    category,
		Address:     &businessInfo.Address,
		Website:     nil, // Not available in whatsmeow BusinessProfile
		Email:       &businessInfo.Email,
	}

	// Handle optional fields
	if businessInfo.Address == "" {
		profile.Address = nil
	}
	if businessInfo.Email == "" {
		profile.Email = nil
	}

	// Return success response
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(BusinessProfileResponse{
		Success: true,
		Message: "Business profile retrieved successfully",
		Profile: profile,
	})
}
