# Katiba360 Backend - User Management System

## Overview

Katiba360 is a platform that makes the Kenyan Constitution accessible to all citizens. This backend system provides a robust user management and personalization system with Google OAuth integration, user profiles, preferences, content management, reading history tracking, achievements, and more.

## Features

### User Management
- **Google OAuth Authentication**: Secure login with Google accounts
- **User Profiles**: Manage user information and preferences
- **Multilingual Support**: User interface in multiple languages (English, Swahili, Kikuyu)
- **Accessibility Settings**: Font size, contrast, screen reader compatibility

### Reading Experience
- **Reading History**: Track reading progress and history
- **Reading Streaks**: Gamification with daily reading streaks
- **Progress Tracking**: Resume reading from where you left off

### Engagement
- **Achievements**: Earn achievements for platform engagement
- **Notifications**: Stay updated with personalized notifications
- **Onboarding Flow**: Guided setup for new users

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT tokens, Google OAuth
- **API Documentation**: Swagger UI / OpenAPI

## Prerequisites

- Python 3.9+
- PostgreSQL
- Redis (optional)

## Setup and Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/katiba360-backend.git
cd katiba360-backend
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and update it with your settings:

```bash
cp .env.example .env
```

Edit the `.env` file with your database credentials, Google OAuth credentials, and other settings.

### 5. Run Database Migrations

```bash
alembic upgrade head
```

### 6. Start the Application

```bash
uvicorn main:app --reload
```

## API Documentation

Once the application is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Constitution Data

The core constitutional content is stored in the file:

```
src/data/processed/constitution_final.json
```

- This file contains the structure and articles of the Constitution of Kenya, 2010.
- **Note:** The data was extracted programmatically from the official source, and some content may be missing or incomplete.
- If you notice missing or incomplete sections, you can help improve the dataset!

### How to Contribute to the Constitution Data
- Compare the current data with the official version at: [Kenya Law - Constitution of Kenya, 2010](https://new.kenyalaw.org/akn/ke/act/2010/constitution/eng@2010-09-03)
- Add missing articles, clauses, or correct any errors in `constitution_final.json`.
- Submit a pull request with your changes and reference the official source for verification.

## Project Structure

```
katiba360-backend/
├── alembic/               # Database migrations
├── src/
│   ├── core/              # Core application settings
│   ├── database.py        # Database configuration
│   ├── dependencies.py    # FastAPI dependencies
│   ├── middleware/        # Middleware components
│   ├── models/            # SQLAlchemy models
│   ├── routers/           # API routes
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   └── utils/             # Utility functions
├── static/                # Static files
├── .env.example          # Example environment variables
├── main.py               # Application entry point
└── requirements.txt      # Project dependencies
```

## Authentication Flow

1. **Google OAuth Login**:
   - Frontend redirects to Google OAuth
   - User authorizes the application
   - Google returns an authorization code
   - Backend exchanges code for tokens
   - User is created or updated in the database
   - JWT access and refresh tokens are issued

2. **Token Refresh**:
   - When access token expires, use refresh token to get a new one
   - Middleware automatically refreshes Google tokens when needed

## Contributing

We welcome contributions to improve Katiba360 Backend!

### Code Contributions
1. **Fork the repository** and create your branch from `main`.
2. **Follow code style guidelines** (use type hints, docstrings, and consistent formatting; PEP8 recommended).
3. **Write clear commit messages** and document your changes.
4. **Test your changes** before submitting a pull request.
5. **Open a pull request** and describe your changes in detail.

### Data Contributions
- See the [Constitution Data](#constitution-data) section above for how to help complete or correct the constitution dataset.

### Code of Conduct
- Be respectful and inclusive.
- Provide constructive feedback.
- Help us make the Constitution accessible to all.

## License

This project is licensed under the MIT License - see the LICENSE file for details.