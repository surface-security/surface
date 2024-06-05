# Software Composition Analysis Tool

## Overview

The Software Composition Analysis (SCA) tool is designed to help developers and organizations manage their open-source dependencies, ensuring they are up-to-date and free of vulnerabilities. The tool synchronizes Software Bill of Materials (SBOMs) from our sbom-repo (`https://github.com/surface-security/django-sbomrepo`), processes dependencies and their vulnerabilities fetched from OSV.dev database, groups them by project, and offers features to suppress or automatically remediate vulnerabilities using Renovate (`https://github.com/renovatebot/renovate`).

## Features

- **SBOM Synchronization**: Automatically syncs Software Bill of Materials (SBOMs) to keep track of all dependencies in your projects.
- **Dependency Processing**: Identifies and processes all dependencies and their associated vulnerabilities.
- **Project Grouping**: Organizes dependencies and vulnerabilities by project for better visibility and management.
- **Vulnerability Management**: Offers options to suppress or automatically remediate vulnerabilities using Renovate.
  

## Setup
| Name | Default | Description |
| ---- | -----   | -------     |
| SCA_SBOM_REPO_URL | `http://localhost:8000` | SBOM repository url |
| SCA_SOURCE_PURL_TYPES | ["github.com"] | Used to mark a dependency as a project, as we use the code repository as purl for this |
| SCA_INTERNAL_RENOVATE | None | Renovate Custom docker image, if does not exist the code will use the default one ('renovate/renovate') |
| SCA_INTERNAL_GITLAB_API | None | Internal Gitlab Endpoint |
| SURFACE_GITHUB_TOKEN | None | Gitlab API token for Renovate |
| SURFACE_GITLAB_TOKEN | None | Gitlab API token for Renovate |


### Usage

#### Synchronize SBOMs
To synchronize SBOMs across your projects, run: \
`python manage.py resync_sbom_repo`

#### Check for public dependencies
In order to mark a dependency as internal or public we use multiple repoistories to check it's existence \
`python manage.py check_public_dependencies`

#### Check if Dependencies are EndofLife
We make use of `https://endoflife.date/`to check if our dependencies are End of Life \
`python manage.py resync_endoflife`

#### Sync Vulnerability Counters for a project
In order to make the User Experience faster vulnerabily counters are calculated and stored in the database to prevent those calculations to be made on each request \
`python manage.py resync_vulns_counters`
