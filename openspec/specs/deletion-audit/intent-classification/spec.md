# deletion-audit/intent-classification Specification

## Purpose
Distinguishes between valid account deletion requests and non-deletion customer inquiries across multiple languages, mapping non-deletion requests to the NOT_APPLICABLE disposition.

## Requirements

### Requirement: Multilingual intent classification
The system SHALL evaluate the customer's request text across all supported languages (including English, French, Spanish, Portuguese, German, Japanese, Korean, and Arabic) to determine whether the user intends to permanently delete or erase their account and personal data.

#### Scenario: Explicit account deletion request in English
- **WHEN** request text is "Please close my account and process the associated personal-data deletion."
- **THEN** system classifies the intent as an authorized deletion request.

#### Scenario: Explicit account deletion request in French
- **WHEN** request text is "Je demande la suppression définitive du compte associé à cette adresse e-mail."
- **THEN** system classifies the intent as an authorized deletion request.

#### Scenario: Explicit account deletion request in Japanese
- **WHEN** request text contains "このメールアドレスに関連するアカウントの完全な削除を依頼します。"
- **THEN** system classifies the intent as an authorized deletion request.

### Requirement: Non-deletion request filtering
The system SHALL classify requests that seek data access, data export, invoice retrieval, credential resets, marketing unsubscribe, or profile updates without deletion as NOT_APPLICABLE with an empty steps array.

#### Scenario: Data export request without deletion
- **WHEN** request text is "I'd like to download my account information in a portable format. Please keep the account as it is."
- **THEN** system assigns deletion_status as NOT_APPLICABLE and steps_json as "[]".

#### Scenario: Invoice copy request
- **WHEN** request text is "I need a copy of last year's invoices for my records. Please leave my profile and purchase history in place."
- **THEN** system assigns deletion_status as NOT_APPLICABLE and steps_json as "[]".

#### Scenario: Marketing list opt-out only
- **WHEN** request text is "Please remove me from marketing lists only. I still want receipts and service messages for this account."
- **THEN** system assigns deletion_status as NOT_APPLICABLE and steps_json as "[]".
