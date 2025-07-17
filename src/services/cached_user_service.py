"""
Cached User Service with Redis caching and proper revoke mechanisms.
Extends the base UserService with caching capabilities.
"""

from typing import Optional, List, Dict, Any, Union
import uuid
import json
from datetime import datetime, date, timedelta
from fastapi import HTTPException, status, Depends, BackgroundTasks
from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from src.database import get_db
from src.models.user_models import (
    User, UserPreference, UserLanguage, UserAccessibility,
    InterestCategory, UserInterest, OnboardingProgress
)
from src.schemas.user_schemas import (
    UserUpdateRequest, UserPreferenceCreate, UserPreferenceUpdate,
    UserLanguageCreate, UserAccessibilityCreate, UserAccessibilityUpdate,
    OnboardingProgressUpdate
)
from src.utils.logging.activity_logger import ActivityLogger
from src.utils.cache import CacheManager, HOUR, MINUTE, DAY
from src.services.user_service import UserService

# Fix import for typing
from typing import Optional


class CachedUserService(UserService):
    """
    Enhanced User Service with Redis caching and proper cache invalidation.
    Extends the base UserService with caching capabilities.
    """
    
    def __init__(self, db: AsyncSession, cache_manager: CacheManager):
        super().__init__(db)
        self.cache = cache_manager
        self.cache_prefix = "user"
        
    def _get_cache_key(self, key_type: str, user_id: str, additional: str = "") -> str:
        """Generate cache key for user data"""
        base_key = f"{self.cache_prefix}:{user_id}:{key_type}"
        return f"{base_key}:{additional}" if additional else base_key
    
    async def _invalidate_user_cache(self, user_id: str, background_tasks: Optional[BackgroundTasks] = None):
        """Invalidate all cached data for a user"""
        cache_patterns = [
            f"{self.cache_prefix}:{user_id}:profile",
            f"{self.cache_prefix}:{user_id}:preferences",
            f"{self.cache_prefix}:{user_id}:languages",
            f"{self.cache_prefix}:{user_id}:accessibility",
            f"{self.cache_prefix}:{user_id}:interests",
            f"{self.cache_prefix}:{user_id}:onboarding",
            f"{self.cache_prefix}:{user_id}:full_profile",
            f"{self.cache_prefix}:{user_id}:stats",
        ]
        
        for pattern in cache_patterns:
            await self.cache.delete(pattern)
            
        # Log cache invalidation
        await self.activity_logger.log_activity(
            user_id=user_id,
            action="cache_invalidation",
            details={"cache_patterns": cache_patterns}
        )
    
    async def get_user_with_preferences_cached(self, user_id: uuid.UUID,
                                              background_tasks: Optional[BackgroundTasks] = None) -> Optional[User]:
        """
        Get a user with preferences (cached version)
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            User with preferences if found, None otherwise
        """
        # For now, use the basic user method - this can be enhanced later
        return await self.get_user_by_id_cached(user_id, background_tasks)
    
    async def get_user_by_id_cached(self, user_id: uuid.UUID, 
                                   background_tasks: Optional[BackgroundTasks] = None) -> Optional[User]:
        """
        Get a user by ID with caching
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks for cache warming
            
        Returns:
            User if found, None otherwise
        """
        user_id_str = str(user_id)
        cache_key = self._get_cache_key("profile", user_id_str)
        
        # Try to get from cache first
        cached_user = await self.cache.get(cache_key)
        if cached_user:
            return User(**json.loads(cached_user))
        
        # Get from database
        user = await self.get_user_by_id(user_id)
        
        # Cache the result if user exists
        if user:
            user_dict = {
                "id": str(user.id),
                "email": user.email,
                "google_id": user.google_id,
                "name": user.name,
                "profile_picture": user.profile_picture,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "is_active": user.is_active,
                "privacy_settings": user.privacy_settings,
                "notification_settings": user.notification_settings,
            }
            
            # Cache for 1 hour
            await self.cache.set(cache_key, json.dumps(user_dict), expire=HOUR)
            
            # Warm cache in background if requested
            if background_tasks:
                background_tasks.add_task(self._warm_user_cache, user_id_str)
        
        return user
    
    async def get_user_preferences_cached(self, user_id: uuid.UUID,
                                        background_tasks: Optional[BackgroundTasks] = None) -> List[UserPreference]:
        """
        Get user preferences with caching
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            List of user preferences
        """
        user_id_str = str(user_id)
        cache_key = self._get_cache_key("preferences", user_id_str)
        
        # Try cache first
        cached_prefs = await self.cache.get(cache_key)
        if cached_prefs:
            prefs_data = json.loads(cached_prefs)
            return [UserPreference(**pref) for pref in prefs_data]
        
        # Get from database
        query = select(UserPreference).where(UserPreference.user_id == user_id)
        result = await self.db.execute(query)
        preferences = result.scalars().all()
        
        # Cache the result
        if preferences:
            prefs_dict = [
                {
                    "id": str(pref.id),
                    "user_id": str(pref.user_id),
                    "preference_key": pref.preference_key,
                    "preference_value": pref.preference_value,
                    "created_at": pref.created_at.isoformat() if pref.created_at else None,
                    "updated_at": pref.updated_at.isoformat() if pref.updated_at else None,
                }
                for pref in preferences
            ]
            await self.cache.set(cache_key, json.dumps(prefs_dict), expire=HOUR)
        
        return preferences
    
    async def get_user_languages_cached(self, user_id: uuid.UUID,
                                      background_tasks: Optional[BackgroundTasks] = None) -> List[UserLanguage]:
        """
        Get user languages with caching
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            List of user languages
        """
        user_id_str = str(user_id)
        cache_key = self._get_cache_key("languages", user_id_str)
        
        # Try cache first
        cached_langs = await self.cache.get(cache_key)
        if cached_langs:
            langs_data = json.loads(cached_langs)
            return [UserLanguage(**lang) for lang in langs_data]
        
        # Get from database
        query = select(UserLanguage).where(UserLanguage.user_id == user_id)
        result = await self.db.execute(query)
        languages = result.scalars().all()
        
        # Cache the result
        if languages:
            langs_dict = [
                {
                    "id": str(lang.id),
                    "user_id": str(lang.user_id),
                    "language_code": lang.language_code,
                    "is_primary": lang.is_primary,
                    "proficiency_level": lang.proficiency_level,
                    "created_at": lang.created_at.isoformat() if lang.created_at else None,
                }
                for lang in languages
            ]
            await self.cache.set(cache_key, json.dumps(langs_dict), expire=HOUR)
        
        return languages
    
    async def get_user_accessibility_cached(self, user_id: uuid.UUID,
                                          background_tasks: Optional[BackgroundTasks] = None) -> Optional[UserAccessibility]:
        """
        Get user accessibility settings with caching
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            User accessibility settings if found
        """
        user_id_str = str(user_id)
        cache_key = self._get_cache_key("accessibility", user_id_str)
        
        # Try cache first
        cached_access = await self.cache.get(cache_key)
        if cached_access:
            access_data = json.loads(cached_access)
            return UserAccessibility(**access_data)
        
        # Get from database
        query = select(UserAccessibility).where(UserAccessibility.user_id == user_id)
        result = await self.db.execute(query)
        accessibility = result.scalars().first()
        
        # Cache the result
        if accessibility:
            access_dict = {
                "id": str(accessibility.id),
                "user_id": str(accessibility.user_id),
                "high_contrast": accessibility.high_contrast,
                "large_text": accessibility.large_text,
                "screen_reader": accessibility.screen_reader,
                "reduced_motion": accessibility.reduced_motion,
                "keyboard_navigation": accessibility.keyboard_navigation,
                "created_at": accessibility.created_at.isoformat() if accessibility.created_at else None,
                "updated_at": accessibility.updated_at.isoformat() if accessibility.updated_at else None,
            }
            await self.cache.set(cache_key, json.dumps(access_dict), expire=HOUR)
        
        return accessibility
    
    async def get_user_interests_cached(self, user_id: uuid.UUID,
                                      background_tasks: Optional[BackgroundTasks] = None) -> List[UserInterest]:
        """
        Get user interests with caching
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            List of user interests
        """
        user_id_str = str(user_id)
        cache_key = self._get_cache_key("interests", user_id_str)
        
        # Try cache first
        cached_interests = await self.cache.get(cache_key)
        if cached_interests:
            interests_data = json.loads(cached_interests)
            return [UserInterest(**interest) for interest in interests_data]
        
        # Get from database
        query = (
            select(UserInterest)
            .options(selectinload(UserInterest.category))
            .where(UserInterest.user_id == user_id)
        )
        result = await self.db.execute(query)
        interests = result.scalars().all()
        
        # Cache the result
        if interests:
            interests_dict = [
                {
                    "id": str(interest.id),
                    "user_id": str(interest.user_id),
                    "category_id": str(interest.category_id),
                    "interest_level": interest.interest_level,
                    "created_at": interest.created_at.isoformat() if interest.created_at else None,
                    "category": {
                        "id": str(interest.category.id),
                        "name": interest.category.name,
                        "description": interest.category.description,
                    } if interest.category else None,
                }
                for interest in interests
            ]
            await self.cache.set(cache_key, json.dumps(interests_dict), expire=HOUR)
        
        return interests
    
    async def get_full_user_profile_cached(self, user_id: uuid.UUID,
                                         background_tasks: Optional[BackgroundTasks] = None) -> Dict[str, Any]:
        """
        Get complete user profile with all related data, cached
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            Complete user profile dictionary
        """
        user_id_str = str(user_id)
        cache_key = self._get_cache_key("full_profile", user_id_str)
        
        # Try cache first
        cached_profile = await self.cache.get(cache_key)
        if cached_profile:
            return json.loads(cached_profile)
        
        # Get all data from individual cached methods
        user = await self.get_user_by_id_cached(user_id, background_tasks)
        preferences = await self.get_user_preferences_cached(user_id, background_tasks)
        languages = await self.get_user_languages_cached(user_id, background_tasks)
        accessibility = await self.get_user_accessibility_cached(user_id, background_tasks)
        interests = await self.get_user_interests_cached(user_id, background_tasks)
        
        # Build complete profile
        profile_data = {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "profile_picture": user.profile_picture,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "is_active": user.is_active,
                "privacy_settings": user.privacy_settings,
                "notification_settings": user.notification_settings,
            } if user else None,
            "preferences": [
                {
                    "preference_key": pref.preference_key,
                    "preference_value": pref.preference_value,
                }
                for pref in preferences
            ],
            "languages": [
                {
                    "language_code": lang.language_code,
                    "is_primary": lang.is_primary,
                    "proficiency_level": lang.proficiency_level,
                }
                for lang in languages
            ],
            "accessibility": {
                "high_contrast": accessibility.high_contrast,
                "large_text": accessibility.large_text,
                "screen_reader": accessibility.screen_reader,
                "reduced_motion": accessibility.reduced_motion,
                "keyboard_navigation": accessibility.keyboard_navigation,
            } if accessibility else None,
            "interests": [
                {
                    "category_name": interest.category.name if interest.category else None,
                    "interest_level": interest.interest_level,
                }
                for interest in interests
            ],
        }
        
        # Cache the complete profile for 1 hour
        await self.cache.set(cache_key, json.dumps(profile_data), expire=HOUR)
        
        return profile_data
    
    async def update_user_profile_cached(self, user_id: uuid.UUID, update_data: UserUpdateRequest,
                                       background_tasks: Optional[BackgroundTasks] = None) -> User:
        """
        Update user profile and invalidate cache
        
        Args:
            user_id: User ID
            update_data: Update data
            background_tasks: Optional background tasks
            
        Returns:
            Updated user
        """
        # Update in database using parent method
        user = await self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user fields
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        
        # Invalidate cache
        await self._invalidate_user_cache(str(user_id), background_tasks)
        
        return user
    
    async def update_user_preferences_cached(self, user_id: uuid.UUID, preferences: List[UserPreferenceUpdate],
                                           background_tasks: Optional[BackgroundTasks] = None) -> List[UserPreference]:
        """
        Update user preferences and invalidate cache
        
        Args:
            user_id: User ID
            preferences: List of preference updates
            background_tasks: Optional background tasks
            
        Returns:
            Updated preferences
        """
        # Update preferences in database
        for pref_update in preferences:
            query = (
                update(UserPreference)
                .where(and_(
                    UserPreference.user_id == user_id,
                    UserPreference.preference_key == pref_update.preference_key
                ))
                .values(
                    preference_value=pref_update.preference_value,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(query)
        
        await self.db.commit()
        
        # Invalidate cache
        await self._invalidate_user_cache(str(user_id), background_tasks)
        
        # Return updated preferences
        return await self.get_user_preferences_cached(user_id, background_tasks)
    
    async def update_user_accessibility_cached(self, user_id: uuid.UUID, accessibility_data: UserAccessibilityUpdate,
                                             background_tasks: Optional[BackgroundTasks] = None) -> UserAccessibility:
        """
        Update user accessibility settings and invalidate cache
        
        Args:
            user_id: User ID
            accessibility_data: Accessibility update data
            background_tasks: Optional background tasks
            
        Returns:
            Updated accessibility settings
        """
        # Update in database
        query = (
            update(UserAccessibility)
            .where(UserAccessibility.user_id == user_id)
            .values(**accessibility_data.dict(exclude_unset=True), updated_at=datetime.utcnow())
        )
        await self.db.execute(query)
        await self.db.commit()
        
        # Invalidate cache
        await self._invalidate_user_cache(str(user_id), background_tasks)
        
        # Return updated accessibility settings
        return await self.get_user_accessibility_cached(user_id, background_tasks)
    
    async def _warm_user_cache(self, user_id_str: str):
        """
        Warm up user cache by preloading commonly accessed data
        
        Args:
            user_id_str: User ID as string
        """
        try:
            user_id = uuid.UUID(user_id_str)
            
            # Preload commonly accessed data
            await self.get_user_preferences_cached(user_id)
            await self.get_user_languages_cached(user_id)
            await self.get_user_accessibility_cached(user_id)
            
        except Exception as e:
            # Log but don't fail - cache warming is optional
            print(f"Cache warming failed for user {user_id_str}: {e}")
    
    async def get_user_stats_cached(self, user_id: uuid.UUID,
                                  background_tasks: Optional[BackgroundTasks] = None) -> Dict[str, Any]:
        """
        Get user statistics with caching
        
        Args:
            user_id: User ID
            background_tasks: Optional background tasks
            
        Returns:
            User statistics dictionary
        """
        user_id_str = str(user_id)
        cache_key = self._get_cache_key("stats", user_id_str)
        
        # Try cache first
        cached_stats = await self.cache.get(cache_key)
        if cached_stats:
            return json.loads(cached_stats)
        
        # Calculate stats (this would involve complex queries)
        # For now, return basic stats - extend as needed
        stats = {
            "profile_completion": 0,
            "preferences_count": 0,
            "languages_count": 0,
            "accessibility_enabled": False,
            "interests_count": 0,
            "last_updated": datetime.utcnow().isoformat(),
        }
        
        # Get actual counts
        preferences = await self.get_user_preferences_cached(user_id, background_tasks)
        languages = await self.get_user_languages_cached(user_id, background_tasks)
        accessibility = await self.get_user_accessibility_cached(user_id, background_tasks)
        interests = await self.get_user_interests_cached(user_id, background_tasks)
        
        stats.update({
            "preferences_count": len(preferences),
            "languages_count": len(languages),
            "accessibility_enabled": accessibility is not None,
            "interests_count": len(interests),
            "profile_completion": self._calculate_profile_completion(preferences, languages, accessibility, interests),
        })
        
        # Cache stats for 1 hour
        await self.cache.set(cache_key, json.dumps(stats), expire=HOUR)
        
        return stats
    
    def _calculate_profile_completion(self, preferences: List, languages: List, 
                                    accessibility: Optional[Any], interests: List) -> int:
        """Calculate profile completion percentage"""
        completion_factors = [
            len(preferences) > 0,  # Has preferences
            len(languages) > 0,    # Has languages
            accessibility is not None,  # Has accessibility settings
            len(interests) > 0,    # Has interests
        ]
        
        return int((sum(completion_factors) / len(completion_factors)) * 100)


# Note: Dependency function is defined in the routes file