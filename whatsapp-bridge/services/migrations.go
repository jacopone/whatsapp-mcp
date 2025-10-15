package services

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"

	_ "github.com/mattn/go-sqlite3"
)

// MigrationInfo represents a database migration file
type MigrationInfo struct {
	Version  string
	Filepath string
}

// RunMigrations applies all pending database migrations
func RunMigrations(dbPath string) error {
	log.Printf("Starting database migrations for: %s", dbPath)

	// Open database connection
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	// Enable foreign keys
	if _, err := db.Exec("PRAGMA foreign_keys = ON"); err != nil {
		return fmt.Errorf("failed to enable foreign keys: %w", err)
	}

	// Get applied migrations
	appliedMigrations, err := getAppliedMigrations(db)
	if err != nil {
		return fmt.Errorf("failed to get applied migrations: %w", err)
	}
	log.Printf("Found %d applied migrations", len(appliedMigrations))

	// Get migration files
	migrationFiles, err := getMigrationFiles()
	if err != nil {
		return fmt.Errorf("failed to get migration files: %w", err)
	}
	log.Printf("Found %d migration files", len(migrationFiles))

	// Apply unapplied migrations
	appliedCount := 0
	for _, migration := range migrationFiles {
		if _, exists := appliedMigrations[migration.Version]; exists {
			log.Printf("Skipping already applied migration: %s", migration.Version)
			continue
		}

		log.Printf("Applying migration: %s", migration.Version)
		if err := applyMigration(db, migration.Version, migration.Filepath); err != nil {
			return fmt.Errorf("failed to apply migration %s: %w", migration.Version, err)
		}
		appliedCount++
		log.Printf("Successfully applied migration: %s", migration.Version)
	}

	if appliedCount == 0 {
		log.Println("No new migrations to apply")
	} else {
		log.Printf("Successfully applied %d new migrations", appliedCount)
	}

	return nil
}

// getAppliedMigrations retrieves the list of already applied migrations
func getAppliedMigrations(db *sql.DB) (map[string]bool, error) {
	applied := make(map[string]bool)

	// Check if schema_migrations table exists
	var tableExists int
	err := db.QueryRow(`
		SELECT COUNT(*)
		FROM sqlite_master
		WHERE type='table' AND name='schema_migrations'
	`).Scan(&tableExists)
	if err != nil {
		return nil, fmt.Errorf("failed to check schema_migrations table: %w", err)
	}

	// If table doesn't exist, return empty map (first run)
	if tableExists == 0 {
		log.Println("schema_migrations table does not exist yet (first run)")
		return applied, nil
	}

	// Query applied migrations
	rows, err := db.Query("SELECT version FROM schema_migrations ORDER BY version")
	if err != nil {
		return nil, fmt.Errorf("failed to query schema_migrations: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var version string
		if err := rows.Scan(&version); err != nil {
			return nil, fmt.Errorf("failed to scan migration version: %w", err)
		}
		applied[version] = true
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating migration rows: %w", err)
	}

	return applied, nil
}

// getMigrationFiles scans the migrations directory and returns sorted list of migration files
func getMigrationFiles() ([]MigrationInfo, error) {
	// Get the directory of the current executable or use relative path
	migrationsDir := "migrations"

	// Check if migrations directory exists
	if _, err := os.Stat(migrationsDir); os.IsNotExist(err) {
		// Try relative to whatsapp-bridge directory
		migrationsDir = filepath.Join("whatsapp-bridge", "migrations")
		if _, err := os.Stat(migrationsDir); os.IsNotExist(err) {
			return nil, fmt.Errorf("migrations directory not found")
		}
	}

	// Read directory contents
	entries, err := os.ReadDir(migrationsDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read migrations directory: %w", err)
	}

	var migrations []MigrationInfo
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}

		filename := entry.Name()
		if !strings.HasSuffix(filename, ".sql") {
			continue
		}

		// Extract version from filename (e.g., "001_add_community_support.sql" -> "001")
		version := strings.Split(filename, "_")[0]

		migrations = append(migrations, MigrationInfo{
			Version:  version,
			Filepath: filepath.Join(migrationsDir, filename),
		})
	}

	// Sort migrations by version
	sort.Slice(migrations, func(i, j int) bool {
		return migrations[i].Version < migrations[j].Version
	})

	return migrations, nil
}

// applyMigration reads and executes a migration file
func applyMigration(db *sql.DB, version, filepath string) error {
	// Read migration file
	content, err := os.ReadFile(filepath)
	if err != nil {
		return fmt.Errorf("failed to read migration file: %w", err)
	}

	// Begin transaction
	tx, err := db.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	// Execute migration SQL
	if _, err := tx.Exec(string(content)); err != nil {
		return fmt.Errorf("failed to execute migration SQL: %w", err)
	}

	// Commit transaction
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit transaction: %w", err)
	}

	return nil
}

// ResetDatabase drops all tables (useful for testing)
func ResetDatabase(dbPath string) error {
	db, err := sql.Open("sqlite3", dbPath)
	if err != nil {
		return fmt.Errorf("failed to open database: %w", err)
	}
	defer db.Close()

	// Get all tables
	rows, err := db.Query("SELECT name FROM sqlite_master WHERE type='table'")
	if err != nil {
		return fmt.Errorf("failed to query tables: %w", err)
	}
	defer rows.Close()

	var tables []string
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return fmt.Errorf("failed to scan table name: %w", err)
		}
		tables = append(tables, name)
	}

	// Drop all tables
	for _, table := range tables {
		if _, err := db.Exec(fmt.Sprintf("DROP TABLE IF EXISTS %s", table)); err != nil {
			return fmt.Errorf("failed to drop table %s: %w", table, err)
		}
		log.Printf("Dropped table: %s", table)
	}

	log.Println("Database reset complete")
	return nil
}
