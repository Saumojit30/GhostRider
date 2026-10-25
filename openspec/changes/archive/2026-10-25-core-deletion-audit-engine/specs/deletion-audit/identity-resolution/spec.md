# Spec Delta

## Purpose
Reconstructs the full identity profile and historical alias graph of the subject by joining current identity records with historical audit logs.

## ADDED Requirements

### Requirement: Historical and current identity graph reconstruction
The system SHALL resolve a subject's primary user_id and all historical identity aliases given an input email address by joining user_identities and user_audit_log records.

#### Scenario: Lookup by current primary email
- **WHEN** deletion request supplies the user's current email listed in user_identities
- **THEN** system retrieves the associated user_id, current name, phone, email_hash, and all historical email and phone values.

#### Scenario: Lookup by historical email
- **WHEN** deletion request supplies an older email that was previously changed in user_audit_log
- **THEN** system discovers the user_id from the audit log record and reconstructs the full current and historical alias set.

### Requirement: Multi-identifier matching set generation
The system SHALL aggregate all associated identifiers for a subject into a unified search profile containing user_id, all known email addresses, all known phone numbers, and all known SHA-256 email hashes.

#### Scenario: Multi-alias profile generation
- **WHEN** user_10 has changed email from nadia.ionescu@yahoo.com to nadia.petrescu@yahoo.com and then to n.petrescu@yahoo.com
- **THEN** the resolved identity profile contains all three email variants and their corresponding hashes for cross-system querying.
