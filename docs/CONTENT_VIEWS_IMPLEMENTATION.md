# Content Views Analytics Implementation

## Overview
This implementation adds comprehensive database persistence for view tracking and analytics in Katiba360, replacing the previous cache-only approach with a robust database-backed solution.

## Components Implemented

### 1. ContentView Model (`src/models/user_models.py`)
- **Table**: `tbl_content_views`
- **Fields**:
  - `id`: Primary key (UUID)
  - `content_type`: Type of content (chapter, article, search, etc.)
  - `content_reference`: Reference identifier ("1", "1.2", "search_term")
  - `user_id`: Optional user ID for authenticated users
  - `view_count`: Number of times viewed
  - `first_viewed_at`: Timestamp of first view
  - `last_viewed_at`: Timestamp of last view
  - `device_type`: Device type (mobile, desktop, tablet)
  - `ip_address`: IP address for anonymous analytics

### 2. Database Migration (`alembic/versions/g1h2i3j4k5l6_add_content_views_table.py`)
- Creates the `tbl_content_views` table
- Adds performance indexes:
  - Individual indexes on `content_type`, `content_reference`, `user_id`, `first_viewed_at`, `last_viewed_at`
  - Composite indexes for common queries: `(content_type, content_reference)`, `(content_type, user_id)`, `(user_id, last_viewed_at)`
  - Unique constraint for user-specific content views to prevent duplicates

### 3. Enhanced Constitution Service (`src/services/constitution_service.py`)

#### Updated `track_view` Method
- **Hybrid approach**: Maintains cache performance while adding database persistence
- **Parameters**: 
  - `item_type`: Content type
  - `item_id`: Content reference
  - `user_id`: Optional user ID
  - `device_type`: Optional device type
  - `ip_address`: Optional IP address
- **Functionality**:
  - Updates cache counters for immediate performance
  - Stores/updates database records for persistent analytics
  - Handles both authenticated and anonymous users
  - Aggregates view counts for returning users

#### New Analytics Methods

##### `get_popular_content_from_db(timeframe, limit, content_type)`
- Retrieves popular content based on actual database view counts
- Supports timeframes: daily, weekly, monthly
- Returns aggregated view counts and unique viewer counts
- Can filter by content type

##### `get_view_trends(content_type, content_reference, days)`
- Provides daily view trends over specified time period
- Can filter by specific content type and reference
- Returns date-based analytics for trend analysis

##### `get_user_view_history(user_id, limit)`
- Retrieves user-specific view history
- Returns detailed viewing patterns for personalization
- Includes device type and timing information

##### `get_analytics_summary(timeframe)`
- Comprehensive analytics overview
- Returns:
  - Total views
  - Unique users
  - Content type breakdown
  - Device type breakdown
  - Time period information

#### Updated `get_popular_sections` Method
- **Replaced fake data** with real database queries
- Uses `get_popular_content_from_db` for actual analytics
- Maintains cache for performance
- Falls back to default data if no analytics available

## Database Schema

```sql
CREATE TABLE tbl_content_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type VARCHAR(50) NOT NULL,
    content_reference VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES tbl_users(id) ON DELETE CASCADE,
    view_count INTEGER NOT NULL DEFAULT 1,
    first_viewed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    last_viewed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    device_type VARCHAR(50),
    ip_address VARCHAR(45)
);

-- Performance indexes
CREATE INDEX idx_content_views_content_type ON tbl_content_views(content_type);
CREATE INDEX idx_content_views_content_reference ON tbl_content_views(content_reference);
CREATE INDEX idx_content_views_user_id ON tbl_content_views(user_id);
CREATE INDEX idx_content_views_last_viewed_at ON tbl_content_views(last_viewed_at);
CREATE INDEX idx_content_views_first_viewed_at ON tbl_content_views(first_viewed_at);

-- Composite indexes for common queries
CREATE INDEX idx_content_views_type_ref ON tbl_content_views(content_type, content_reference);
CREATE INDEX idx_content_views_type_user ON tbl_content_views(content_type, user_id);
CREATE INDEX idx_content_views_user_viewed ON tbl_content_views(user_id, last_viewed_at);

-- Unique constraint for user-specific content views
CREATE UNIQUE INDEX idx_content_views_user_content_unique 
ON tbl_content_views(user_id, content_type, content_reference) 
WHERE user_id IS NOT NULL;
```

## Key Features

### 1. Anonymous User Support
- Tracks views from non-authenticated users
- Uses IP address for basic analytics
- Prevents duplicate tracking through database constraints

### 2. Authenticated User Tracking
- Maintains user-specific view history
- Aggregates multiple views of same content
- Supports personalization features

### 3. Performance Optimization
- Hybrid cache + database approach
- Background task processing to avoid blocking
- Comprehensive indexing strategy
- Efficient query patterns

### 4. Analytics Capabilities
- Real-time popular content identification
- Historical trend analysis
- User behavior insights
- Device usage patterns
- Content performance metrics

## Usage Examples

### Tracking a View
```python
# In request handler
await constitution_service.track_view(
    item_type="chapter",
    item_id="1",
    user_id=current_user.id,
    device_type="mobile",
    ip_address=request.client.host
)
```

### Getting Popular Content
```python
# Get popular articles from last week
popular = await constitution_service.get_popular_sections(
    timeframe="weekly",
    limit=10
)
```

### Analytics Dashboard
```python
# Get comprehensive analytics
summary = await constitution_service.get_analytics_summary(
    timeframe="monthly"
)
```

## Benefits

1. **Real Analytics**: Replaces simulated data with actual user behavior
2. **Scalability**: Database-backed solution scales with user growth
3. **Flexibility**: Supports multiple analytics queries and timeframes
4. **Performance**: Maintains cache performance while adding persistence
5. **Privacy Compliant**: Handles anonymous users appropriately
6. **Comprehensive**: Tracks multiple content types and user patterns

## Migration Steps

1. **Run Migration**: `alembic upgrade head`
2. **Deploy Code**: Deploy updated constitution service
3. **Verify**: Check analytics endpoints return real data
4. **Monitor**: Watch for performance and accuracy improvements

## Testing

A test script `test_content_views.py` is provided to verify:
- Database operations work correctly
- Analytics methods return expected data
- Performance is acceptable
- Edge cases are handled properly

## Future Enhancements

1. **Real-time Dashboards**: WebSocket-based live analytics
2. **Machine Learning**: Prediction models for content recommendations
3. **Advanced Segmentation**: User cohort analysis
4. **Export Features**: CSV/PDF analytics reports
5. **A/B Testing**: Content performance comparison tools