# Release Management

## ADDED Requirements

### Requirement: Git is the source of truth
The complete buildable source and release Dockerfiles SHALL be stored in Git. Every customer release SHALL be produced from an immutable Git tag using a semantic version such as `v1.2.3`.

#### Scenario: Reproducible release build
- **WHEN** a release engineer checks out tag `v1.2.3` and runs the documented release build
- **THEN** the build uses only the source, pinned dependencies, declared build arguments, and approved build secrets for that tag

### Requirement: Generated release directory is not committed
The build system SHALL generate customer artifacts under `release/` and SHALL exclude that directory from Git.

#### Scenario: Local release output
- **WHEN** the release build completes
- **THEN** `release/` contains images/checksums/license/package artifacts locally and `git status` does not report them as untracked files

### Requirement: Versioned Docker Hub images
Release images SHALL be published to the vendor Docker Hub organization using immutable version tags and architecture/runtime labels.

#### Scenario: Image publication
- **WHEN** tag `v1.2.3` is approved
- **THEN** the server, web, scanner, and model-runtime images are pushed with `v1.2.3` and digest references are recorded in the release manifest

### Requirement: Customer license distribution
A customer license SHALL be distributed through a private release channel or customer-specific private Docker Hub repository/tag. A generic public image MUST NOT contain a reusable customer license or vendor signing private key.

#### Scenario: Customer package
- **WHEN** a customer release is generated
- **THEN** the package includes the customer license, image digest manifest, checksum file, and installation instructions without exposing vendor signing secrets

### Requirement: Per-version change notes
Every released version SHALL have a committed change note at `release-notes/vX.Y.Z.md` describing features, fixes, model/runtime changes, migrations, security changes, compatibility, and known limitations.

#### Scenario: Version review
- **WHEN** a reviewer inspects tag `v1.2.3`
- **THEN** `release-notes/v1.2.3.md` is present and describes the exact source/model/image versions used by that release

### Requirement: Cross-platform release tooling
Release tooling SHALL support Windows PowerShell and Linux shells, including Windows drive paths and POSIX paths without changing artifact identity.

#### Scenario: Windows release
- **WHEN** a release engineer runs the PowerShell build from `E:\\NCKH\\WBrain`
- **THEN** the generated manifest uses the same semantic version, checksums, and image tags as the equivalent Linux build
