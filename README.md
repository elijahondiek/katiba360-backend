# Katiba360° Backend API 🇰🇪

**Backend system powering Kenya's most accessible constitutional platform**

> 🌐 **Related Repository:** [Katiba360° Frontend App](https://github.com/elijahondiek/katiba360) - The Next.js frontend application

## 🚀 Calling All Backend Developers!

We need your expertise to build a robust backend that serves constitutional knowledge to millions of Kenyans! Whether you're experienced with **Python**, **FastAPI**, **PostgreSQL**, or **API design** – your skills can make a real impact.

### 🎯 Critical Backend Features Needed

1. **🌍 Translation Management System** (Highest Priority!)
   - API endpoints for local dialect translations
   - Translation workflow management
   - Content versioning for different languages
   - Translation validation and approval system

2. **📝 Constitution Data Completion**
   - Scripts to identify and flag missing content
   - Data validation and integrity checks
   - Import tools for official constitution updates
   - Automated content synchronization

3. **👤 Mzalendo Profile System**
   - **Achievements Engine:** Gamified constitutional learning
   - **Offline Content API:** Critical content caching endpoints
   - **Settings Management:** User preferences and personalization
   - **Overview Dashboard:** User progress and statistics
   - **Profile Analytics:** Reading patterns and engagement metrics

4. **🔊 Text-to-Speech Enhancement**
   - TTS API integration and management
   - Voice selection and customization
   - Audio caching and optimization
   - Accessibility compliance

5. **📱 Offline-First Architecture**
   - Progressive sync capabilities
   - Conflict resolution for offline changes
   - Optimized data structures for mobile
   - Background sync services

6. **⚡ Performance & Infrastructure**
   - API caching strategies
   - Database query optimization
   - Rate limiting and security
   - Monitoring and logging improvements

## 📋 Current System Overview

Katiba360 Backend provides a comprehensive user management and content delivery system for Kenya's constitutional platform, featuring Google OAuth integration, personalized reading experiences, achievement tracking, and multilingual support.

## ✨ Implemented Features

### 🔐 Authentication & User Management
- **Google OAuth Integration:** Secure authentication flow
- **JWT Token Management:** Access and refresh token handling
- **User Profiles:** Comprehensive user data management
- **Privacy Controls:** GDPR-compliant data handling

### 📚 Content Management
- **Constitution Data API:** Structured constitutional content
- **Chapter & Article Endpoints:** Organized content delivery
- **Search Infrastructure:** Full-text search capabilities
- **Multilingual Content:** English, Swahili, and local language support

### 📊 User Experience
- **Smart Reading Progress:** Content-aware completion tracking with dynamic thresholds
- **Reading History:** Complete reading journey tracking with detailed analytics
- **Achievement System:** Gamified learning progression
- **Notification System:** Personalized user engagement
- **Content-Based Completion:** Intelligent chapter completion based on word count and reading time

### 🌐 API Infrastructure
- **FastAPI Framework:** High-performance async API
- **OpenAPI Documentation:** Auto-generated API docs
- **Database Migrations:** Alembic migration management
- **Error Handling:** Comprehensive exception management

### 🆕 Recent Improvements
- **Content-Aware Completion Logic:** Dynamic completion thresholds based on chapter word count
- **Reading Time Calculation:** Intelligent reading time estimation (200 WPM baseline)
- **Optimized Progress Tracking:** Enhanced reading progress service with better caching
- **Completion Threshold Formula:** `(word_count / 200_wpm) * 0.3 = completion_threshold`
- **Minimum Threshold Protection:** Maintains 2-minute minimum for backward compatibility

## 🛠 Tech Stack

- **Framework:** FastAPI (Python 3.9+)
- **Database:** PostgreSQL with SQLAlchemy ORM
- **Authentication:** JWT tokens, Google OAuth 2.0
- **Caching:** Redis (optional)
- **Documentation:** Swagger UI / OpenAPI
- **Migrations:** Alembic
- **Testing:** pytest
- **Deployment:** Docker, Uvicorn

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL database
- Redis (optional, for caching)
- Google OAuth credentials

### 1. Clone & Setup

```bash
git clone https://github.com/elijahondiek/katiba360-backend.git
cd katiba360-backend

# Set up virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your database credentials and Google OAuth settings
```

### 3. Database Setup

```bash
# Run migrations
alembic upgrade head

# Optional: Seed with sample data
python scripts/seed_data.py
```

### 4. Start Development Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access API Documentation
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 📊 Constitution Data

### Current Status
Our constitutional content is stored in `src/data/processed/constitution_final.json`:

- ✅ **Complete:** Basic chapter and article structure
- ⚠️ **Incomplete:** Some sections missing due to programmatic extraction
- 🔍 **Needs Review:** Content accuracy verification needed

### 🤝 How You Can Help

1. **Data Validation**
   - Compare with [official constitution](https://new.kenyalaw.org/akn/ke/act/2010/constitution/eng@2010-09-03)
   - Identify missing articles, clauses, or sections
   - Verify existing content accuracy

2. **Translation Contributions**
   - Add local language translations
   - Review existing Swahili translations
   - Create language-specific terminology databases

3. **Content Enhancement**
   - Add simplified explanations for complex legal terms
   - Create practical examples for constitutional concepts
   - Develop educational content and quizzes

## 🏗 Project Architecture

```
katiba360-backend/
├── alembic/                 # Database migrations
├── src/
│   ├── core/               # Core application configuration
│   │   └── config.py       # Environment settings
│   ├── models/             # SQLAlchemy database models
│   │   ├── user_models.py  # User, profile, preferences
│   │   └── reading_progress.py # Reading tracking
│   ├── routers/            # FastAPI route handlers
│   │   ├── auth_routes.py          # Authentication endpoints
│   │   ├── constitution_routes.py  # Content delivery
│   │   ├── user_routes.py          # User management
│   │   ├── achievement_routes.py   # Gamification
│   │   └── reading_routes.py       # Progress tracking
│   ├── services/           # Business logic layer
│   │   ├── auth_service.py         # Authentication logic
│   │   ├── constitution_service.py # Content management
│   │   ├── user_service.py         # User operations
│   │   └── achievement_service.py  # Achievement engine
│   ├── schemas/            # Pydantic data models
│   ├── middleware/         # Custom middleware
│   ├── utils/              # Utility functions
│   └── data/              # Constitution data
│       └── processed/
│           └── constitution_final.json
├── main.py                 # Application entry point
└── requirements.txt        # Dependencies
```

## 🏗 Complete Backend Architecture Flow

### 🔐 Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Google

    User->>Frontend: Click "Login with Google"
    Frontend->>Google: Redirect to OAuth
    Google->>User: Show consent screen
    User->>Google: Grant permission
    Google->>Backend: Send authorization code
    Backend->>Google: Exchange code for tokens
    Google->>Backend: Return access & refresh tokens
    Backend->>Backend: Create/update user
    Backend->>Backend: Generate JWT tokens
    Backend->>Frontend: Return JWT tokens
    Frontend->>User: Login complete
```

### 🔄 Request Processing Flow

```mermaid
flowchart TD
    A[Client Request] --> B[FastAPI Application]
    B --> C[CORS Middleware]
    C --> D[Rate Limiting Middleware]
    D --> E[Logging Middleware]
    E --> F[Auth Middleware]
    F --> G[Google OAuth Middleware]
    G --> H[Route Handler]
    H --> I[Service Layer]
    I --> J{Cache Check}
    J -->|Hit| K[Return Cached Data]
    J -->|Miss| L[Database Query]
    L --> M[Update Cache]
    M --> N[Return Response]
    K --> N
    N --> O[Response Middleware]
    O --> P[Client Response]
    
    style A fill:#e1f5fe
    style P fill:#e8f5e8
    style J fill:#fff3e0
    style L fill:#fce4ec
```

### 🎯 Constitution Content Flow

```mermaid
sequenceDiagram
    participant Client
    participant Router
    participant Service
    participant Cache
    participant Database
    participant FileSystem

    Client->>Router: GET /constitution/chapters/4
    Router->>Service: constitution_service.get_chapter()
    Service->>Cache: check_cache("chapter_4")
    
    alt Cache Hit
        Cache->>Service: Return cached chapter
        Service->>Router: Chapter data
    else Cache Miss
        Service->>Database: Query user progress
        Database->>Service: Progress data
        Service->>FileSystem: Load constitution_final.json
        FileSystem->>Service: Chapter content
        Service->>Service: Process & enrich content
        Service->>Cache: cache_chapter("chapter_4", data)
        Service->>Router: Enriched chapter data
    end
    
    Router->>Client: JSON response with chapter
```

### 📖 Reading Progress Tracking

```mermaid
flowchart TD
    A[User Reads Content] --> B[Frontend Tracks Time]
    B --> C[POST /reading/progress]
    C --> D[Reading Service]
    D --> E[Validate Progress Data]
    E --> F[Update Database]
    F --> G[Invalidate Cache]
    G --> H[Calculate Statistics]
    H --> I[Update Achievements]
    I --> J[Send Notifications]
    J --> K[Background Tasks]
    K --> L[Sync Offline Data]
    L --> M[Return Success]
    
    style A fill:#e3f2fd
    style M fill:#e8f5e8
    style I fill:#fff8e1
    style K fill:#f3e5f5
```

### 🎮 User Achievement System

```mermaid
stateDiagram-v2
    [*] --> UserAction
    UserAction --> ReadingProgress: Read chapter
    UserAction --> BookmarkContent: Save article
    UserAction --> CompleteOnboarding: First login
    
    ReadingProgress --> CheckAchievements
    BookmarkContent --> CheckAchievements
    CompleteOnboarding --> CheckAchievements
    
    CheckAchievements --> EarnAchievement: Criteria met
    CheckAchievements --> NoAchievement: Not yet
    
    EarnAchievement --> UpdateDatabase
    UpdateDatabase --> SendNotification
    SendNotification --> UpdateCache
    UpdateCache --> [*]
    
    NoAchievement --> [*]
```

### 💾 Data Storage Architecture

```mermaid
erDiagram
    User {
        uuid id PK
        string email
        string name
        jsonb profile_data
        timestamp created_at
    }
    
    UserPreference {
        uuid id PK
        uuid user_id FK
        string language
        string theme
        int reading_level
    }
    
    ReadingHistory {
        uuid id PK
        uuid user_id FK
        string content_type
        string content_id
        int time_spent
        timestamp read_at
    }
    
    UserAchievement {
        uuid id PK
        uuid user_id FK
        string achievement_type
        jsonb achievement_data
        timestamp earned_at
    }
    
    SavedContent {
        uuid id PK
        uuid user_id FK
        string content_type
        string content_id
        jsonb metadata
        timestamp saved_at
    }
    
    User ||--o{ UserPreference : has
    User ||--o{ ReadingHistory : tracks
    User ||--o{ UserAchievement : earns
    User ||--o{ SavedContent : saves
```

### 🔧 Service Layer Architecture

```mermaid
flowchart LR
    subgraph "API Layer"
        A[Auth Routes]
        B[Constitution Routes]
        C[User Routes]
        D[Reading Routes]
    end
    
    subgraph "Service Layer"
        E[Auth Service]
        F[Constitution Service]
        G[User Service]
        H[Reading Service]
        I[Achievement Service]
        J[Notification Service]
    end
    
    subgraph "Data Layer"
        K[PostgreSQL]
        L[Redis Cache]
        M[File System]
        N[Google OAuth]
    end
    
    A --> E
    B --> F
    C --> G
    D --> H
    
    E --> K
    E --> L
    E --> N
    
    F --> K
    F --> L
    F --> M
    
    G --> K
    G --> L
    
    H --> K
    H --> L
    H --> I
    
    I --> J
    J --> K
    
    style E fill:#ffebee
    style F fill:#e8f5e8
    style G fill:#e3f2fd
    style H fill:#fff3e0
```

### 🛡️ Security & Rate Limiting

```mermaid
sequenceDiagram
    participant Client
    participant RateLimit
    participant Auth
    participant API
    participant Database

    Client->>RateLimit: Request with IP/User
    RateLimit->>RateLimit: Check Redis counter
    
    alt Rate Limit Exceeded
        RateLimit->>Client: 429 Too Many Requests
    else Within Limits
        RateLimit->>Auth: Forward request
        Auth->>Auth: Validate JWT token
        
        alt Invalid Token
            Auth->>Client: 401 Unauthorized
        else Valid Token
            Auth->>API: Authenticated request
            API->>Database: Process request
            Database->>API: Return data
            API->>Client: Success response
        end
    end
```

## 🤝 Contributing

### 🔥 High-Impact Contribution Areas

1. **🌍 Translation Infrastructure**
   - Build translation management APIs
   - Create content versioning system
   - Implement translation validation workflows

2. **📊 Analytics & Insights**
   - User engagement analytics
   - Reading pattern analysis
   - Content popularity tracking
   - Performance monitoring

3. **🔧 API Development**
   - New feature endpoints
   - API optimization and caching
   - Rate limiting and security
   - Documentation improvements

4. **🧪 Testing & Quality**
   - Unit and integration tests
   - API endpoint testing
   - Performance testing
   - Security auditing

### 📋 Development Workflow

1. **Fork the repository** and create feature branch from `main`
2. **Set up development environment** following Quick Start guide
3. **Check existing issues** or create new ones for features/bugs
4. **Follow Python best practices:** Type hints, docstrings, PEP 8
5. **Write comprehensive tests** for new features
6. **Update API documentation** if adding new endpoints
7. **Submit pull request** with detailed description

### 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_auth.py
```

### 📚 API Documentation

When adding new endpoints:
- Use proper FastAPI decorators and type hints
- Add comprehensive docstrings
- Include example requests/responses
- Update OpenAPI tags and descriptions

## 🌟 Join Our Mission

**Our Impact:** Your backend code directly serves constitutional knowledge to millions of Kenyans, promoting civic education and democratic participation.

**What We're Building:** A scalable, accessible platform that breaks down barriers to constitutional literacy in Kenya.

### 🔗 Get Connected

- **GitHub Issues:** [Report bugs or request features](https://github.com/elijahondiek/katiba360-backend/issues)
- **API Testing:** Use Swagger UI at http://localhost:8000/docs
- **Frontend Repository:** [Katiba360° Frontend App](https://github.com/elijahondiek/katiba360)
- **Project Lead:** [@WebShrewd](https://x.com/WebShrewd)
- **Support Development:** [Buy me a coffee](https://buymeacoffee.com/Teksad)

## 📈 Performance & Monitoring

### Current Metrics
- ⚡ **Response Time:** <200ms for most endpoints
- 🔄 **Uptime:** 99.9% target availability
- 📊 **Database:** Optimized queries with indexing
- 🔒 **Security:** JWT tokens, rate limiting, CORS protection

### Monitoring Stack
- **Logging:** Structured logging with rotation
- **Error Tracking:** Comprehensive error handling
- **Performance:** Query optimization and caching
- **Health Checks:** Endpoint monitoring

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Constitution of Kenya, 2010
- FastAPI and SQLAlchemy communities
- Google OAuth platform
- All contributors and the Kenyan developer community
- Organizations promoting digital civic education

---

**Let's build the backend that empowers constitutional literacy in Kenya! 🇰🇪**

*Your API endpoints can deliver constitutional knowledge to millions of Kenyans.*