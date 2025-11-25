# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v1.2.0] - 2025-11-25

### Added

- Docker support with Dockerfile, docker-compose.yaml, and .dockerignore for production-ready deployment
- Nornir and nornir-netmiko dependencies for enhanced network automation capabilities
- Updated requirements.txt with Nornir dependencies

### Changed

- Migrated from direct netmiko usage to Nornir framework with nornir-netmiko plugin for better network device management
- Refactored tools into separate modules and added generic executor
- Simplified devices.py and removed inconsistent commands.py (KISS Implementation)
- Cleaned up dependencies and disabled Nornir logging
- Updated README.md with new architecture details and Docker usage guide

### Fixed

- Updated docs and added comments

## [v1.1.0] - 2025-11-24

### Changed

- Updated README for new features and architecture
- Updated project structure to show move from single files to directories
- Added CLI usage examples for natural language processing and batch configuration commands

## [v1.0.0] - 2025-11-20

### Added

- Initial stable release of Network AI Agent
- Type hints throughout the codebase for better type safety
- Error handling for authentication and timeout issues in network commands
- Enhanced documentation and typing for better maintainability
