package main

import (
	"context"
	"fmt"
	"strings"

	"go.mau.fi/whatsmeow"
	"go.mau.fi/whatsmeow/types"
)

// PopulateGroupParticipants syncs group participant information to resolve @lid IDs to real names
func (store *MessageStore) PopulateGroupParticipants(client *whatsmeow.Client) error {
	// First, get all groups from the database
	rows, err := store.db.Query(`
		SELECT DISTINCT jid, name
		FROM chats
		WHERE jid LIKE '%@g.us'
		ORDER BY jid
	`)
	if err != nil {
		return fmt.Errorf("failed to get groups: %v", err)
	}
	defer rows.Close()

	type Group struct {
		JID  string
		Name string
	}

	var groups []Group
	for rows.Next() {
		var g Group
		if err := rows.Scan(&g.JID, &g.Name); err != nil {
			continue
		}
		groups = append(groups, g)
	}

	fmt.Printf("Found %d groups to sync participants for\n", len(groups))
	totalParticipants := 0

	// For each group, get participant information
	// For each group, get participant information
	for _, group := range groups {
		// Parse the group JID
		groupJID, err := types.ParseJID(group.JID)
		if err != nil {
			fmt.Printf("Failed to parse group JID %s: %v\n", group.JID, err)
			continue
		}

		// Get group info including participants
		groupInfo, err := client.GetGroupInfo(groupJID)
		if err != nil {
			fmt.Printf("Failed to get info for group %s: %v\n", group.Name, err)
			continue
		}

		// Process each participant
		for _, participant := range groupInfo.Participants {
			// Use the PhoneNumber field which contains the REAL phone JID!
			phoneJID := participant.PhoneNumber.String()
			phoneNumber := participant.PhoneNumber.User  // Real phone number (e.g., 393485722640)

			// Get the participant's @lid ID for this group
			lidID := participant.LID.String()

			// Skip if no valid phone number
			if phoneJID == "" || phoneNumber == "" {
				fmt.Printf("Skipping participant with no phone number in group %s (LID: %s)\n",
					group.Name, lidID)
				continue
			}

			fmt.Printf("DEBUG Group %s - Phone: %s, LID: %s\n",
				group.Name, phoneNumber, lidID)

			// If we don't have a LID, try to construct it from existing patterns
			if lidID == "" || lidID == "0@lid" {
				// Check if we have messages from this user with @lid format
				var existingLID string
				err := store.db.QueryRow(`
					SELECT DISTINCT sender
					FROM messages
					WHERE chat_jid = ?
					AND sender LIKE '%@lid'
					AND sender LIKE ?
					LIMIT 1
				`, group.JID, "%"+phoneNumber[:6]+"%").Scan(&existingLID)

				if err == nil && existingLID != "" {
					lidID = existingLID
				}
			}

			// First check if we already have this contact from one-on-one chats
			var existingName string
			var hasExistingContact bool

			// Look for existing contact with this phone number (from one-on-one chats)
			err = store.db.QueryRow(`
				SELECT name FROM contacts
				WHERE (jid = ? OR phone_number = ?)
				AND name != ?
				AND name IS NOT NULL
				AND jid LIKE '%@s.whatsapp.net'
				ORDER BY
					CASE WHEN name = phone_number THEN 1 ELSE 0 END,
					length(name) DESC
				LIMIT 1
			`, phoneJID, phoneNumber, phoneNumber).Scan(&existingName)

			if err == nil && existingName != "" && existingName != phoneNumber {
				hasExistingContact = true
			}

			var displayName string

			// ALWAYS try to get the full name from WhatsApp contacts first (from address book)
			// Use PhoneNumber JID to query the contact store
			contact, err := client.Store.Contacts.GetContact(context.Background(), participant.PhoneNumber)
			if err == nil && contact.FullName != "" {
				displayName = contact.FullName
				fmt.Printf("Using WhatsApp address book name: %s for participant\n", displayName)
			} else if hasExistingContact {
				// Fall back to existing contact from one-on-one chats
				displayName = existingName
				fmt.Printf("Using existing contact name: %s for %s\n", displayName, phoneNumber)
			} else if contact.PushName != "" {
				// Use push name (WhatsApp display name) as last resort
				displayName = contact.PushName
			} else if contact.BusinessName != "" {
				displayName = contact.BusinessName
			} else if participant.DisplayName != "" {
				displayName = participant.DisplayName
			} else {
				displayName = phoneNumber // Fallback to phone number
			}

			// Store/update the contact with proper name
			_, err = store.db.Exec(`
				INSERT OR REPLACE INTO contacts (jid, name, phone_number)
				VALUES (?, ?, ?)
			`, phoneJID, displayName, phoneNumber)

			if err == nil {
				totalParticipants++
			}

			// If we have a LID, also store that mapping
			// IMPORTANT: Store the actual phone number, not the LID number
			if lidID != "" && lidID != "0@lid" {
				_, err = store.db.Exec(`
					INSERT OR REPLACE INTO contacts (jid, name, phone_number)
					VALUES (?, ?, ?)
				`, lidID, displayName, phoneNumber)  // phoneNumber is the real phone like 393485722640

				if err == nil {
					fmt.Printf("Mapped %s -> %s (phone: %s) in group %s\n", lidID, displayName, phoneNumber, group.Name)
				}
			}
		}
	}

	fmt.Printf("Synced %d group participant names\n", totalParticipants)
	return nil
}

// FixLIDMappings corrects @lid entries that have the wrong phone number
func (store *MessageStore) FixLIDMappings(client *whatsmeow.Client) error {
	// Get all groups to check their participants
	rows, err := store.db.Query(`
		SELECT DISTINCT jid FROM chats WHERE jid LIKE '%@g.us'
	`)
	if err != nil {
		return fmt.Errorf("failed to get groups: %v", err)
	}
	defer rows.Close()

	fixedCount := 0
	for rows.Next() {
		var groupJID string
		if err := rows.Scan(&groupJID); err != nil {
			continue
		}

		// Get group info
		gJID, err := types.ParseJID(groupJID)
		if err != nil {
			continue
		}

		groupInfo, err := client.GetGroupInfo(gJID)
		if err != nil {
			continue
		}

		// Process participants to fix mappings
		for _, participant := range groupInfo.Participants {
			lidID := participant.LID.String()
			actualPhoneNumber := participant.PhoneNumber.User
			phoneJID := participant.PhoneNumber.String()

			// Skip if no phone number available
			if phoneJID == "" || actualPhoneNumber == "" {
				continue
			}

			if lidID != "" && lidID != "0@lid" {
				// Get the full name from WhatsApp address book using the REAL phone JID
				contact, err := client.Store.Contacts.GetContact(context.Background(), participant.PhoneNumber)
				var fullName string

				if err == nil && contact.FullName != "" {
					fullName = contact.FullName
				} else {
					// Try to get from existing contacts with this phone number
					err := store.db.QueryRow(`
						SELECT name FROM contacts
						WHERE phone_number = ?
						AND jid LIKE '%@s.whatsapp.net'
						AND name != ?
						ORDER BY length(name) DESC
						LIMIT 1
					`, actualPhoneNumber, actualPhoneNumber).Scan(&fullName)

					if err != nil {
						continue // Skip if no name found
					}
				}

				if fullName != "" {
					// Update the @lid entry with correct name and phone
					_, err = store.db.Exec(`
						UPDATE contacts
						SET name = ?, phone_number = ?
						WHERE jid = ?
					`, fullName, actualPhoneNumber, lidID)

					if err == nil {
						fixedCount++
						fmt.Printf("Fixed %s -> %s (phone: %s)\n", lidID, fullName, actualPhoneNumber)
					}
				}
			}
		}
	}

	fmt.Printf("Fixed %d @lid mappings\n", fixedCount)
	return nil
}

// ResyncLIDsWithContacts matches existing @lid entries with known contacts by phone number
func (store *MessageStore) ResyncLIDsWithContacts() error {
	// First, find all @lid entries that don't have proper names
	rows, err := store.db.Query(`
		SELECT DISTINCT jid, phone_number
		FROM contacts
		WHERE jid LIKE '%@lid'
		AND (name = phone_number OR name = jid OR name LIKE '%@lid')
		AND phone_number IS NOT NULL
	`)
	if err != nil {
		return fmt.Errorf("failed to query @lid contacts: %v", err)
	}
	defer rows.Close()

	updateCount := 0
	for rows.Next() {
		var lidJID, phoneNumber string
		if err := rows.Scan(&lidJID, &phoneNumber); err != nil {
			continue
		}

		// Look for existing contact with this phone number
		var properName string
		err := store.db.QueryRow(`
			SELECT name
			FROM contacts
			WHERE phone_number = ?
			AND jid LIKE '%@s.whatsapp.net'
			AND name != ?
			AND name IS NOT NULL
			ORDER BY length(name) DESC
			LIMIT 1
		`, phoneNumber, phoneNumber).Scan(&properName)

		if err == nil && properName != "" {
			// Update the @lid entry with the proper name
			_, err = store.db.Exec(`
				UPDATE contacts
				SET name = ?
				WHERE jid = ?
			`, properName, lidJID)

			if err == nil {
				updateCount++
				fmt.Printf("Updated %s -> %s\n", lidJID, properName)
			}
		}
	}

	fmt.Printf("Resynced %d @lid contacts with existing names\n", updateCount)
	return nil
}

// UpdateMessageSenderNames updates existing messages to use proper contact names
func (store *MessageStore) UpdateMessageSenderNames() error {
	// Update messages where sender is @lid to use the contact name
	result, err := store.db.Exec(`
		UPDATE messages
		SET sender = (
			SELECT c.name
			FROM contacts c
			WHERE c.jid = messages.sender
			AND c.name != c.phone_number
		)
		WHERE sender LIKE '%@lid'
		AND EXISTS (
			SELECT 1 FROM contacts c
			WHERE c.jid = messages.sender
			AND c.name != c.phone_number
		)
	`)

	if err != nil {
		return fmt.Errorf("failed to update sender names: %v", err)
	}

	rowsAffected, _ := result.RowsAffected()
	fmt.Printf("Updated %d message sender names\n", rowsAffected)

	return nil
}

// ResolveGroupMemberName attempts to resolve a @lid ID to a real name
func (store *MessageStore) ResolveGroupMemberName(lidID string, groupJID string, client *whatsmeow.Client) string {
	// First, check if we have it in the database
	var name string
	err := store.db.QueryRow(`
		SELECT name FROM contacts WHERE jid = ? AND name != phone_number
	`, lidID).Scan(&name)

	if err == nil && name != "" {
		return name
	}

	// If not found, try to get group info and find this member
	if strings.HasSuffix(groupJID, "@g.us") {
		gJID, err := types.ParseJID(groupJID)
		if err == nil {
			groupInfo, err := client.GetGroupInfo(gJID)
			if err == nil {
				// Try to match by LID
				for _, participant := range groupInfo.Participants {
					// Check if this might be the participant
					if participant.LID.String() == lidID {
						// Found exact match - use PhoneNumber to get contact
						contact, _ := client.Store.Contacts.GetContact(context.Background(), participant.PhoneNumber)
						if contact.FullName != "" {
							// Store for future use
							store.db.Exec(`
								INSERT OR REPLACE INTO contacts (jid, name, phone_number)
								VALUES (?, ?, ?)
							`, lidID, contact.FullName, participant.PhoneNumber.User)
							return contact.FullName
						}
					}
				}
			}
		}
	}

	// Fallback to the numeric ID
	return lidID
}