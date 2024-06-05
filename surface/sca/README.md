# Software Composition Analysis Tool

## Overview

The Software Composition Analysis (SCA) tool is designed to help developers and organizations manage their open-source dependencies, ensuring they are up-to-date and free of vulnerabilities. The tool synchronizes Software Bill of Materials (SBOMs) from our sbom-repo (https://github.com/surface-security/django-sbomrepo), processes dependencies and their vulnerabilities fetched from OSV.dev database, groups them by project, and offers features to suppress or automatically remediate vulnerabilities using Renovate (https://github.com/renovatebot/renovate).

## Features

- **SBOM Synchronization**: Automatically syncs Software Bill of Materials (SBOMs) to keep track of all dependencies in your projects.
- **Dependency Processing**: Identifies and processes all dependencies and their associated vulnerabilities.
- **Project Grouping**: Organizes dependencies and vulnerabilities by project for better visibility and management.
- **Vulnerability Management**: Offers options to suppress or automatically remediate vulnerabilities using Renovate.
  

### Usage

#### Synchronize SBOMs
To synchronize SBOMs across your projects, run:
python manage.py resync_sbom_repo
