# Secrets Manager

A Django app for managing and tracking secrets discovered in source code and git repositories.

## Models

### Secret
Stores information about discovered secrets:
- Secret value and hash
- Source and type of secret
- Status (new/triaged/false_positive)
- Criticality level
- Team ownership
- Verification status
- Git source reference

### SecretLocation
Tracks where secrets were found:
- File path
- Git commit
- Repository URL
- Timestamp
- Author
- Line number

### SecretHistory
Maintains audit trail of changes to secrets:
- Changed fields
- User who made changes
- Timestamp
- Version number

## Management Commands

### import_secrets.py
Imports secrets from TruffleHog JSON output:

```python manage.py import_secrets path/to/secrets.json```

### import_git_secrets.py
Scans git repositories for sensitive files (certificates, keystores, etc.):

```python manage.py import_git_secrets path/to/git/repo --org your-org```

Supported sensitive file extensions:

### Cryptographic & Certificate Files
- .jks (Java KeyStore)
- .p12, .pfx (PKCS#12/Personal Exchange Format)
- .pem (Privacy Enhanced Mail certificate)
- .crt, .cer (Certificate files)
- .key, .keystore (Private Keys)
- .csr (Certificate Signing Request)
- .der (Distinguished Encoding Rules certificate)
- .spc (Software Publisher Certificate)

### Mobile & App Signing
- .mobileprovision (iOS Provisioning Profile)
- .keychain (macOS Keychain)
- .provisionprofile (iOS/macOS Provisioning Profile)
- .apk.sign (Android App Signing)
- .aab.sign (Android App Bundle Signing)

### Configuration & Credentials
- .env, .env.* (Environment files)
- .conf, .config (Configuration files)
- .ini (Configuration files)
- .properties (Java Properties)
- .secret, .secrets (Generic Secrets)
- .credentials, .creds (Credential files)
- .htpasswd (Apache Password files)
- .netrc (Network credentials)

### Cloud & Infrastructure
- .aws (AWS credentials)
- .kube/config (Kubernetes config)
- .npmrc (NPM registry auth)
- terraform.tfstate (Terraform state)
- .terraform.tfvars (Terraform variables)

## Admin Interface

The app provides a Django admin interface with:
- List and detail views for secrets
- Filtering by status, criticality, team
- Direct links to secret locations in GitHub
- Audit history tracking
- Bulk update capabilities

## Usage

1. Run migrations:

2. Import secrets using either:
   - TruffleHog JSON output via `import_secrets`
   - Direct git scanning via `import_git_secrets`

3. Access the admin interface to:
   - Triage discovered secrets
   - Set criticality levels
   - Assign team ownership
   - Track remediation status
