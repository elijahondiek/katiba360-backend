# Katiba360 Changelog

This document tracks all significant changes to the Katiba360 backend in chronological order.

## [0.1.0] - 2025-05-11

### Added
- Google OAuth authentication implementation
- User model with relationships to preferences, languages, interests, etc.
- User schemas for data validation
- AuthService for handling authentication
- UserService for user management
- ContentService for content management
- ReadingService for tracking reading history
- AchievementService for user achievements
- NotificationService for user notifications
- OnboardingService for user onboarding
- Service factory pattern for dependency injection
- JWT token generation and validation
- Environment configuration system

### Changed
- Removed all password-related functionality
- Updated authentication flow to use Google OAuth exclusively
- Simplified user creation process

### Removed
- Password hashing and verification
- Password reset functionality
- Email-based authentication
- PasswordResetToken model
- Password-related schemas
