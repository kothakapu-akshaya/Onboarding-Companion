# Validation Rules Documentation

This document outlines all validation rules implemented in the Corpus Collection API backend. These rules ensure data integrity, security, and consistent user experience across all client applications.

## Table of Contents
- [User Registration & Profile Validation](#user-registration--profile-validation)
- [Content Submission Validation](#content-submission-validation)
- [File Upload Validation](#file-upload-validation)
- [Validation Architecture](#validation-architecture)
- [Error Response Format](#error-response-format)
- [Frontend Integration](#frontend-integration)

## User Registration & Profile Validation

### Core Required Fields
All users must provide these mandatory fields during registration:

### Phone Number (Required)
- **Format**: Must be a valid Indian phone number
- **Length**: Exactly 10 digits (after country code normalization)
- **Pattern**: Must start with digit > 5 (Indian mobile number requirement)
- **Normalization**: Automatically formatted to `+91XXXXXXXXXX`
- **Database**: Unique constraint enforced
- **Examples**:
  - Valid: `9876543210`, `+919876543210`, `91 9876543210`
  - Invalid: `5876543210` (starts with 5), `123456789` (too short)

### Name (Required)
- **Length**: 2-100 characters
- **Pattern**: Letters, spaces, periods, hyphens, and apostrophes only
- **Validation**: Must contain meaningful content (not just repeated characters)
- **Database**: NOT NULL constraint enforced
- **Examples**:
  - Valid: `John Doe`, `Mary O'Connor`, `Jean-Luc Picard`
  - Invalid: `J`, `123 Name`, `!!!Name!!!`

### Password (Required)
- **Length**: 8-100 characters
- **Storage**: Always stored as hashed_password (bcrypt)
- **Database**: NOT NULL constraint enforced
- **Requirements**:
  - At least one uppercase letter (A-Z)
  - At least one lowercase letter (a-z)
  - At least one digit (0-9)
  - At least one special character (!@#$%^&*(),.?":{}|<>)
- **Security**: Common weak passwords are rejected
- **Examples**:
  - Valid: `SecurePass123!`, `MyStr0ng#Pwd`
  - Invalid: `password123`, `12345678`, `PASSWORD`

### Email (Optional)
- **Requirement**: Optional for registration but validated if provided
- **Format**: Standard RFC 5322 email format
- **Normalization**: Converted to lowercase, trimmed
- **Length Limits**: Local part ≤ 64 chars, domain ≤ 255 chars
- **Database**: Unique constraint enforced, nullable allowed
- **Additional Checks**: Must contain exactly one @ symbol, blocks temporary email services
- **Examples**:
  - Valid: `user@example.com`, `test.email+tag@domain.co.uk`
  - Invalid: `invalid.email`, `user@`, `@domain.com`, temporary email services

### Gender (Required)
- **Options**: Exactly 3 predefined values
  - `male`: Male gender
  - `female`: Female gender  
  - `other`: Other/non-binary gender
- **Requirement**: Must be selected, cannot be null or empty
- **Validation**: Enforced by database enum constraint
- **Examples**:
  - Valid: `male`, `female`, `other`
  - Invalid: `m`, `f`, `Male`, `FEMALE` (case sensitive)

### Date of Birth (Required)
- **Requirement**: Must be provided, cannot be null
- **Minimum Age**: 13 years old
- **Maximum Age**: 120 years old
- **Date Validation**: Birth date cannot be in the future
- **Format**: ISO date format (YYYY-MM-DD)
- **Examples**:
  - Valid: `1990-01-15`, `2005-12-31`
  - Invalid: `2025-01-01` (future), `2010-01-01` (under 13)

### Place/Location (Required)
- **Requirement**: Must be provided, cannot be null or empty
- **Length**: 2-200 characters (minimum increased from optional version)
- **Pattern**: Letters, numbers, spaces, commas, periods, hyphens, apostrophes, and parentheses
- **Enhanced Validations**:
  - **Content Quality**: Must contain meaningful content (≥2 unique characters)
  - **Anti-Spam**: Maximum 10 words, each word ≤50 characters
  - **Punctuation Limit**: ≤30% of total characters
  - **Gibberish Detection**: Long words (>8 chars) must contain vowels
  - **Format Validation**: Proper comma-separated format, balanced parentheses
- **Prohibited Values**:
  - Test/placeholder values: `test`, `dummy`, `fake`, `sample`, `temp`, `placeholder`
  - Repeated characters: `aaa`, `xxx`, `111`
  - System values: `null`, `undefined`, `na`, `n/a`, `none`
  - Numeric-only: `123456`, `90210` (zip codes alone not allowed)
- **Examples**:
  - Valid: `Hyderabad, India`, `Mumbai, India`, `San Francisco (Bay Area)`, `London, UK`
  - Invalid: `test`, `City@123`, `aaaaaa`, `12345`, `xxx`, `A` (too short)

### User Consent (Required)
- **Requirement**: Must be `true` to create account
- **Validation**: Explicitly required for GDPR compliance
- **Database**: NOT NULL with default `false`, but validated to be `true` at registration
- **Tracking**: Consent timestamp is captured via `created_at` field (signup timestamp)

### System Fields (Auto-Generated)
These fields are automatically managed by the system:

### User ID (System Generated)
- **Type**: UUID v4 (Universally Unique Identifier)
- **Generation**: Automatically generated on user creation
- **Database**: Primary key, NOT NULL, unique
- **Usage**: Used for all internal references and API operations

### Account Status (System Managed)
- **Field**: `is_active` boolean
- **Default**: `true` for new accounts
- **Database**: NOT NULL with default `true`
- **Usage**: Controls user access to the system

### Timestamps (System Managed)
- **Created At**: Automatically set to current UTC timestamp on user creation
- **Updated At**: Automatically updated to current UTC timestamp on any user modification  
- **Database**: Both NOT NULL with automatic defaults
- **Usage**: Audit trail and system monitoring

## Content Submission Validation

### Title
- **Length**: 8-200 characters
- **Quality Checks**:
  - Must contain meaningful content (≥3 unique characters)
  - Cannot be mostly repeated characters
  - Discourages ALL CAPS formatting
- **Examples**:
  - Valid: `Recording of Traditional Folk Song`, `Daily Weather Report`
  - Invalid: `Title`, `AAAAAAAAAA`, `RECORDING OF FOLK SONG` (all caps)

### Description
- **Length**: 32-2000 characters
- **Quality Checks**:
  - Must contain varied content (≥10 unique characters excluding spaces/punctuation)
  - Should provide meaningful information about the content
- **Examples**:
  - Valid: `This recording captures a traditional folk song performed by local artists during the harvest festival celebration.`
  - Invalid: `Good recording`, `aaaaaaa this is a description`

### Geographic Location
- **Latitude**: -90.0 to 90.0 degrees
- **Longitude**: -180.0 to 180.0 degrees
- **Validation**: Cannot be (0,0) as this appears invalid
- **Requirement**: Location is mandatory for all submissions
- **Format**: Decimal degrees with up to 6 decimal places precision

### Release Rights
- **Options**:
  - `creator`: Content created by the user
  - `family_or_friend`: Content created with permission
  - `downloaded`: **NOT ALLOWED** - automatically rejected
- **Validation**: Must be explicitly declared, cannot be `NA`
- **Business Rule**: Only original content or content with explicit permission is accepted

### Language
- **Options**: 22 Indian languages supported
- **Requirement**: Must be selected from predefined enum
- **Supported Languages**: Assamese, Bengali, Bodo, Dogri, Gujarati, Hindi, Kannada, Kashmiri, Konkani, Maithili, Malayalam, Marathi, Meitei, Nepali, Odia, Punjabi, Sanskrit, Santali, Sindhi, Tamil, Telugu, Urdu

## File Upload Validation

### Audio Files
- **Formats**: WAV, MP3, OGG, WebM, FLAC
- **Size Limit**: 500MB maximum
- **Duration**: 5 seconds minimum, 15 minutes maximum
- **Quality Checks**: 
  - Automatic silence detection
  - Noise level analysis
  - File corruption detection

### Video Files
- **Formats**: MP4, WebM, AVI, MOV, MKV
- **Size Limit**: 2GB maximum
- **Duration**: Configurable limits based on content type
- **Additional Validation**: Container format verification

### Image Files
- **Formats**: JPEG, JPG, PNG, GIF, BMP, WebP
- **Size Limit**: 50MB maximum
- **Resolution**: No specific limits, but file size constraint applies
- **Quality**: Basic format validation and corruption detection

### Text Files
- **Size Limit**: 10MB maximum
- **Content Validation**: Must contain meaningful text (≥50 characters)
- **Quality**: Checks for repetitive content patterns

### File Security
- **Forbidden Types**: ZIP, TAR, GZIP, 7Z, RAR archives are rejected
- **MIME Type Validation**: Server-side MIME type verification
- **File Hash**: Automatic hash generation for duplicate detection

## Validation Architecture

The Corpus Collection API implements a sophisticated, multi-layered validation architecture designed for consistency, maintainability, and security.

### Core Validation Components

#### 1. **Centralized Validators** (`app/core/validators.py`)
Atomic, reusable validation functions that handle specific data types:
- `validate_phone()` - Phone number formatting and validation
- `validate_email_address()` - Email format and normalization
- `validate_password_strength()` - Password security requirements
- `validate_place_name()` - Comprehensive place/location validation
- `validate_age_from_birthdate()` - Age calculation and limits

#### 2. **Pydantic Schema Validators**
Field-level validators within Pydantic models:
- **Location**: `app/schemas/auth_validation.py`, `app/schemas/validation.py`
- **Validation Strategy**: Use centralized validators for consistency
- **Error Handling**: Descriptive, user-friendly error messages

#### 3. **Database Constraints**
Database-level enforcement for critical business rules:
- **Gender Enum**: Check constraint ensures only `male`, `female`, `other`
- **NOT NULL Constraints**: Required fields enforced at DB level
- **Unique Constraints**: Phone and email uniqueness
- **Data Migration**: Automatic backfill of default values for required fields

### Validation Layers

#### **Layer 1: Pydantic Field Validation**
- **Purpose**: Input sanitization and basic format validation
- **Location**: Schema classes with `@field_validator` decorators  
- **Benefits**: Immediate feedback, type conversion, normalization

#### **Layer 2: Cross-Field Validation**
- **Purpose**: Business logic requiring multiple field values
- **Location**: `@model_validator` decorators in Pydantic models
- **Examples**: Password confirmation matching, release rights validation

#### **Layer 3: Database Constraints**
- **Purpose**: Data integrity enforcement at storage level
- **Location**: SQLModel/SQLAlchemy models and Alembic migrations
- **Benefits**: Prevents data corruption, ensures consistency

#### **Layer 4: Business Logic Validation**
- **Purpose**: Complex business rules and external dependencies
- **Location**: Service layer and API endpoints
- **Examples**: User permissions, content policy enforcement

### Validation Patterns

#### **Required vs Optional Fields**
Recent updates have made core user profile fields required with comprehensive database constraints:

```python
# Required fields (NOT NULL database constraints)
id: UUID                         # Primary key, auto-generated UUID
phone: str                       # Unique Indian phone number  
name: str                        # 2-100 chars, meaningful content
gender: Gender                   # Enum: male, female, other with DB check constraint
date_of_birth: date              # Valid date, age 13-120
place: str                       # Enhanced validation, 2-200 chars
hashed_password: str             # Bcrypt hash, never stored as plaintext
is_active: bool                  # Default True, controls account access
has_given_consent: bool          # Default False, must be True for registration
created_at: datetime             # Auto-set on creation
updated_at: datetime             # Auto-updated on modification

# Optional fields (nullable allowed)
email: Optional[str] = None      # Email format validated if provided
profile_picture_path: Optional[str] = None  # File path if uploaded
last_login_at: Optional[datetime] = None    # Set after successful login
```

#### **Centralized Validation Pattern**
```python
# Schema validator delegates to centralized function
@field_validator("place")
@classmethod
def validate_place(cls, v: str) -> str:
    return validate_place_name(v)  # Uses app.core.validators
```

#### **Profile Update Flexibility**
```python
# Profile updates: optional but validated if provided
@field_validator("place")  
@classmethod
def validate_place(cls, v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    if v.strip() == "":
        raise ValueError("Place cannot be empty. Provide valid location or leave unchanged.")
    return validate_place_name(v)
```

### Enhanced Place Validation

The place field implements the most comprehensive validation in the system:

#### **Multi-Stage Validation Process**
1. **Basic Checks**: Length (2-200), required field validation
2. **Character Validation**: Allowed characters, encoding issues
3. **Content Quality**: Meaningful content, uniqueness of characters  
4. **Anti-Spam Detection**: Word limits, character repetition, gibberish
5. **Business Rules**: No test values, no numeric-only entries
6. **Format Validation**: Comma separation, balanced parentheses

#### **Validation Function Architecture**
```python
def validate_place_name(place: str) -> str:
    # 1. Basic validation (null, length)
    # 2. Character pattern matching
    # 3. Content quality assessment
    # 4. Spam/fake value detection
    # 5. Format structure validation
    # 6. Return cleaned, validated value
```

### Migration Strategy

When updating validation rules:

#### **Database Migrations**
Recent migration (`update_user_required_fields_and_constraints`) implemented:

1. **Backfill Default Values**: 
   - `gender = 'other'` for NULL values
   - `place = 'Not specified'` for NULL/empty values
   - `date_of_birth = '1990-01-01'` for NULL values
   - `hashed_password = 'INVALID_HASH_REQUIRES_PASSWORD_RESET'` for NULL values
   - `created_at/updated_at = NOW()` for NULL timestamps

2. **Add NOT NULL Constraints**: All core user fields now have database-level constraints
3. **Add Check Constraints**: Gender enum constraint ensures only valid values
4. **Rollback Support**: Complete downgrade functions for safe rollbacks

#### **Code Updates** 
1. **Update Models**: Change Optional to Required types
2. **Update Schemas**: Add/modify Pydantic validators
3. **Update Documentation**: Keep validation rules documentation current
4. **Test Thoroughly**: Validate all user flows and edge cases

### Best Practices

#### **Validation Design Principles**
1. **Backend Authority**: All validation logic authoritative on backend
2. **Fail Fast**: Validate early in request processing
3. **Clear Messages**: User-friendly, actionable error descriptions  
4. **Consistent Behavior**: Same validation across all endpoints
5. **Security First**: Treat all input as potentially malicious

#### **Error Message Guidelines**
- **Specific**: Tell user exactly what's wrong
- **Actionable**: Provide clear guidance on how to fix
- **Consistent**: Use same terminology across similar validations
- **No Technical Jargon**: User-facing language, not developer terms

#### **Performance Considerations**
- **Efficient Patterns**: Compile regex once, reuse validation functions
- **Early Termination**: Fail on first major error for expensive validations
- **Caching**: Cache validation results where appropriate
- **Database Efficiency**: Use constraints to avoid application-level checks

## Error Response Format

All validation errors return a consistent JSON response format:

```json
{
  "success": false,
  "error_type": "validation_error",
  "message": "Please correct the following errors and try again:",
  "errors": [
    {
      "field": "title",
      "message": "Title must be at least 8 characters long",
      "error_type": "string_too_short",
      "invalid_value": "Short"
    }
  ],
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### Error Types
- `validation_error`: Field validation failures
- `business_logic_error`: Business rule violations
- `file_validation_error`: File-specific validation issues
- `http_error`: HTTP-level errors (404, 403, etc.)

### HTTP Status Codes
- `422 Unprocessable Entity`: Validation errors
- `400 Bad Request`: Business logic violations
- `413 Payload Too Large`: File size exceeded
- `415 Unsupported Media Type`: Invalid file format

## Frontend Integration

### Validation Strategy
1. **Backend-First**: All validation logic is authoritative on the backend
2. **Frontend UX**: Optional client-side validation for immediate feedback
3. **Consistent Messages**: Frontend should display backend error messages as-is
4. **Progressive Enhancement**: Forms work without JavaScript validation

### Error Handling
Frontend applications should:

1. **Parse Error Response**: Extract `errors` array from response
2. **Display Field Errors**: Map each error to the corresponding form field
3. **Show Summary**: Display main `message` for multiple errors
4. **Maintain State**: Keep form data on validation failure
5. **Retry Logic**: Allow users to correct and resubmit

### Example Frontend Error Handling
```javascript
// Handle validation error response
const handleValidationError = (errorResponse) => {
  const { message, errors } = errorResponse.data;
  
  // Clear previous errors
  clearFormErrors();
  
  // Display field-specific errors
  errors.forEach(error => {
    displayFieldError(error.field, error.message);
  });
  
  // Show general message if multiple errors
  if (errors.length > 1) {
    showNotification(message, 'error');
  }
};
```

### Best Practices
1. **Trust Backend**: Always validate on backend regardless of frontend validation
2. **User Feedback**: Provide clear, actionable error messages
3. **Accessibility**: Ensure error messages are accessible to screen readers
4. **Performance**: Use debouncing for real-time validation feedback
5. **Security**: Never bypass backend validation for "trusted" inputs

## Migration Guide

### Removing Frontend Validations
When removing redundant frontend validations:

1. **Keep UX Validations**: Retain client-side validations that improve user experience
2. **Remove Business Logic**: Remove validations that duplicate backend rules
3. **Update Error Handling**: Ensure backend errors are properly displayed
4. **Test Thoroughly**: Verify all validation scenarios work correctly
5. **Update Documentation**: Keep frontend validation docs in sync

### Example Migration
```javascript
// BEFORE: Frontend title validation
const validateTitle = (title) => {
  if (title.length < 8) {
    return "Title must be at least 8 characters";
  }
  return null;
};

// AFTER: Only UX feedback, rely on backend for authoritative validation
const provideTitleFeedback = (title) => {
  // Optional: Show character count for UX
  return title.length < 8 ? `${8 - title.length} more characters needed` : null;
};
```

This centralized validation approach ensures data integrity, consistent user experience, and simplified maintenance across all client applications.