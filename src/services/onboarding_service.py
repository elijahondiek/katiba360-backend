from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime
from fastapi import HTTPException, status, Depends
from sqlalchemy import select, func, update, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.database import get_db
from src.models.user_models import (
    User, OnboardingProgress, UserLanguage, UserInterest,
    UserPreference, UserAccessibility, InterestCategory
)
from src.schemas.user_schemas import (
    OnboardingProgressUpdate, UserLanguageCreate, UserInterestCreate,
    UserPreferenceUpdate, UserAccessibilityUpdate
)
from src.services.user_service import UserService
from src.services.achievement_service import AchievementService
from src.services.notification_service import NotificationService
from src.utils.logging.activity_logger import ActivityLogger


class OnboardingService:
    """
    Service for handling onboarding-related operations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_logger = ActivityLogger()
        self.user_service = UserService(db)
        self.achievement_service = AchievementService(db)
        self.notification_service = NotificationService(db)
    
    async def get_onboarding_progress(self, user_id: uuid.UUID) -> Optional[OnboardingProgress]:
        """
        Get onboarding progress for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Onboarding progress if found, None otherwise
        """
        query = select(OnboardingProgress).where(OnboardingProgress.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def initialize_onboarding(self, user_id: uuid.UUID) -> OnboardingProgress:
        """
        Initialize onboarding progress for a new user
        
        Args:
            user_id: User ID
            
        Returns:
            Created onboarding progress
            
        Raises:
            HTTPException: If onboarding progress already exists
        """
        # Check if onboarding progress already exists
        existing_progress = await self.get_onboarding_progress(user_id)
        if existing_progress:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Onboarding progress already exists"
            )
        
        # Create onboarding progress
        progress = OnboardingProgress(
            user_id=user_id,
            current_step=1,
            progress_percentage=0
        )
        
        self.db.add(progress)
        await self.db.commit()
        await self.db.refresh(progress)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"Onboarding initialized for user",
            user_id=str(user_id),
            activity_type="onboarding_initialized"
        )
        
        return progress
    
    async def update_onboarding_progress(
        self, user_id: uuid.UUID, progress_data: OnboardingProgressUpdate
    ) -> OnboardingProgress:
        """
        Update onboarding progress
        
        Args:
            user_id: User ID
            progress_data: Progress update data
            
        Returns:
            Updated onboarding progress
            
        Raises:
            HTTPException: If onboarding progress not found
        """
        # Get existing progress
        progress = await self.get_onboarding_progress(user_id)
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Onboarding progress not found"
            )
        
        # Update fields if provided
        update_data = progress_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(progress, key, value)
        
        # Calculate progress percentage
        total_steps = 6  # Total number of onboarding steps
        completed_steps = sum([
            progress.step_language_selection,
            progress.step_interests_selection,
            progress.step_reading_level,
            progress.step_accessibility,
            progress.step_feature_tour,
            progress.step_celebration
        ])
        
        progress.progress_percentage = int((completed_steps / total_steps) * 100)
        
        # Set completed_at if all steps are done
        if completed_steps == total_steps and not progress.completed_at:
            progress.completed_at = datetime.now()
            
            # Also update user.onboarding_completed
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            user = result.scalars().first()
            
            if user:
                user.onboarding_completed = True
                
                # Check for achievement
                await self.achievement_service.check_and_award_achievements(user_id)
        
        progress.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(progress)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"Onboarding progress updated to {progress.progress_percentage}%",
            user_id=str(user_id),
            activity_type="onboarding_progress_updated",
            metadata={
                "updated_fields": list(update_data.keys()),
                "progress_percentage": progress.progress_percentage,
                "current_step": progress.current_step,
                "completed": progress.completed_at is not None
            }
        )
        
        return progress
    
    async def complete_onboarding_step(
        self, user_id: uuid.UUID, step_name: str
    ) -> OnboardingProgress:
        """
        Complete a specific onboarding step
        
        Args:
            user_id: User ID
            step_name: Step name (e.g., 'step_language_selection')
            
        Returns:
            Updated onboarding progress
            
        Raises:
            HTTPException: If onboarding progress not found or invalid step name
        """
        valid_steps = [
            "step_language_selection",
            "step_interests_selection",
            "step_reading_level",
            "step_accessibility",
            "step_feature_tour",
            "step_celebration"
        ]
        
        if step_name not in valid_steps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid step name. Must be one of: {', '.join(valid_steps)}"
            )
        
        # Get existing progress
        progress = await self.get_onboarding_progress(user_id)
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Onboarding progress not found"
            )
        
        # Set step to completed
        setattr(progress, step_name, True)
        
        # Update current step to next step
        current_index = valid_steps.index(step_name)
        if current_index < len(valid_steps) - 1:
            progress.current_step = current_index + 2  # +2 because steps are 1-indexed
        
        # Calculate progress percentage
        total_steps = len(valid_steps)
        completed_steps = sum([getattr(progress, step) for step in valid_steps])
        
        progress.progress_percentage = int((completed_steps / total_steps) * 100)
        
        # Set completed_at if all steps are done
        if completed_steps == total_steps and not progress.completed_at:
            progress.completed_at = datetime.now()
            
            # Also update user.onboarding_completed
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            user = result.scalars().first()
            
            if user:
                user.onboarding_completed = True
                
                # Check for achievement
                await self.achievement_service.check_and_award_achievements(user_id)
                
                # Create notification
                await self.notification_service.create_notification(
                    user_id=user_id,
                    notification_data={
                        "title": "Onboarding Complete!",
                        "message": "You've completed the onboarding process. Welcome to Katiba360!",
                        "notification_type": "achievement",
                        "priority": 1
                    }
                )
        
        progress.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(progress)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User completed onboarding step '{step_name}'",
            user_id=str(user_id),
            activity_type="onboarding_step_completed",
            metadata={
                "step_name": step_name,
                "progress_percentage": progress.progress_percentage,
                "current_step": progress.current_step,
                "completed": progress.completed_at is not None
            }
        )
        
        return progress
    
    async def set_language_preferences(
        self, user_id: uuid.UUID, language_codes: List[str], primary_language_code: str
    ) -> Dict[str, Any]:
        """
        Set language preferences during onboarding
        
        Args:
            user_id: User ID
            language_codes: List of language codes
            primary_language_code: Primary language code
            
        Returns:
            Dictionary with updated languages and onboarding progress
            
        Raises:
            HTTPException: If language codes are invalid
        """
        # Validate language codes
        valid_language_codes = ["en", "sw", "ki"]  # English, Swahili, Kikuyu
        
        for code in language_codes:
            if code not in valid_language_codes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid language code: {code}"
                )
        
        if primary_language_code not in language_codes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Primary language code must be in the list of language codes"
            )
        
        # Get existing languages
        existing_languages = await self.user_service.get_user_languages(user_id)
        existing_codes = {lang.language_code for lang in existing_languages}
        
        # Add new languages
        added_languages = []
        for code in language_codes:
            if code not in existing_codes:
                language_data = UserLanguageCreate(
                    language_code=code,
                    is_primary=(code == primary_language_code),
                    proficiency_level="intermediate"
                )
                language = await self.user_service.add_user_language(user_id, language_data)
                added_languages.append(language)
            elif code == primary_language_code:
                # Set existing language as primary
                for lang in existing_languages:
                    if lang.language_code == code:
                        await self.user_service.set_primary_language(user_id, lang.id)
                        break
        
        # Update user preferences
        preferences = await self.user_service.get_user_preferences(user_id)
        if preferences:
            preferences_data = UserPreferenceUpdate(primary_language=primary_language_code)
            await self.user_service.update_user_preferences(user_id, preferences_data)
        
        # Complete onboarding step
        progress = await self.complete_onboarding_step(user_id, "step_language_selection")
        
        # Get updated languages
        updated_languages = await self.user_service.get_user_languages(user_id)
        
        return {
            "languages": updated_languages,
            "onboarding_progress": progress
        }
    
    async def set_interest_preferences(
        self, user_id: uuid.UUID, interest_category_ids: List[uuid.UUID]
    ) -> Dict[str, Any]:
        """
        Set interest preferences during onboarding
        
        Args:
            user_id: User ID
            interest_category_ids: List of interest category IDs
            
        Returns:
            Dictionary with updated interests and onboarding progress
            
        Raises:
            HTTPException: If interest categories are invalid
        """
        # Validate interest categories
        for category_id in interest_category_ids:
            query = select(InterestCategory).where(
                InterestCategory.id == category_id,
                InterestCategory.is_active == True
            )
            result = await self.db.execute(query)
            category = result.scalars().first()
            
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Interest category not found or inactive: {category_id}"
                )
        
        # Get existing interests
        existing_interests = await self.user_service.get_user_interests(user_id)
        existing_category_ids = {interest.interest_category_id for interest in existing_interests}
        
        # Add new interests
        added_interests = []
        for category_id in interest_category_ids:
            if category_id not in existing_category_ids:
                interest = await self.user_service.add_user_interest(user_id, category_id)
                added_interests.append(interest)
        
        # Complete onboarding step
        progress = await self.complete_onboarding_step(user_id, "step_interests_selection")
        
        # Get updated interests
        updated_interests = await self.user_service.get_user_interests(user_id)
        
        return {
            "interests": updated_interests,
            "onboarding_progress": progress
        }
    
    async def set_reading_level(
        self, user_id: uuid.UUID, reading_level: str
    ) -> Dict[str, Any]:
        """
        Set reading level during onboarding
        
        Args:
            user_id: User ID
            reading_level: Reading level
            
        Returns:
            Dictionary with updated preferences and onboarding progress
            
        Raises:
            HTTPException: If reading level is invalid
        """
        # Validate reading level
        valid_reading_levels = ["basic", "intermediate", "advanced"]
        
        if reading_level not in valid_reading_levels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid reading level: {reading_level}"
            )
        
        # Update user preferences
        preferences = await self.user_service.get_user_preferences(user_id)
        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found"
            )
        
        preferences_data = UserPreferenceUpdate(reading_level=reading_level)
        updated_preferences = await self.user_service.update_user_preferences(user_id, preferences_data)
        
        # Complete onboarding step
        progress = await self.complete_onboarding_step(user_id, "step_reading_level")
        
        return {
            "preferences": updated_preferences,
            "onboarding_progress": progress
        }
    
    async def set_accessibility_settings(
        self, user_id: uuid.UUID, accessibility_data: UserAccessibilityUpdate
    ) -> Dict[str, Any]:
        """
        Set accessibility settings during onboarding
        
        Args:
            user_id: User ID
            accessibility_data: Accessibility settings
            
        Returns:
            Dictionary with updated accessibility settings and onboarding progress
        """
        # Get or create accessibility settings
        accessibility = await self.user_service.get_user_accessibility(user_id)
        
        if accessibility:
            # Update existing settings
            updated_accessibility = await self.user_service.update_user_accessibility(
                user_id, accessibility_data
            )
        else:
            # Create new settings
            accessibility_create_data = UserAccessibilityCreate(**accessibility_data.dict(exclude_unset=True))
            updated_accessibility = await self.user_service.create_user_accessibility(
                user_id, accessibility_create_data
            )
        
        # Complete onboarding step
        progress = await self.complete_onboarding_step(user_id, "step_accessibility")
        
        return {
            "accessibility": updated_accessibility,
            "onboarding_progress": progress
        }
    
    async def complete_feature_tour(self, user_id: uuid.UUID) -> OnboardingProgress:
        """
        Complete feature tour step
        
        Args:
            user_id: User ID
            
        Returns:
            Updated onboarding progress
        """
        return await self.complete_onboarding_step(user_id, "step_feature_tour")
    
    async def complete_celebration(self, user_id: uuid.UUID) -> OnboardingProgress:
        """
        Complete celebration step (final step)
        
        Args:
            user_id: User ID
            
        Returns:
            Updated onboarding progress
        """
        return await self.complete_onboarding_step(user_id, "step_celebration")
    
    async def get_onboarding_state(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """
        Get complete onboarding state for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with onboarding state
            
        Raises:
            HTTPException: If user not found
        """
        # Get user with related data
        query = (
            select(User)
            .options(
                selectinload(User.preferences),
                selectinload(User.languages),
                selectinload(User.interests).selectinload(UserInterest.interest_category),
                selectinload(User.accessibility),
                selectinload(User.onboarding_progress)
            )
            .where(User.id == user_id)
        )
        result = await self.db.execute(query)
        user = result.scalars().first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get available interest categories
        query = select(InterestCategory).where(InterestCategory.is_active == True)
        result = await self.db.execute(query)
        interest_categories = result.scalars().all()
        
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "onboarding_completed": user.onboarding_completed
            },
            "preferences": user.preferences,
            "languages": user.languages,
            "interests": user.interests,
            "accessibility": user.accessibility,
            "onboarding_progress": user.onboarding_progress,
            "available_interest_categories": interest_categories,
            "available_languages": [
                {"code": "en", "name": "English"},
                {"code": "sw", "name": "Swahili"},
                {"code": "ki", "name": "Kikuyu"}
            ]
        }


# Dependency to get OnboardingService
async def get_onboarding_service(db: AsyncSession = Depends(get_db)) -> OnboardingService:
    """
    Dependency to get OnboardingService instance
    
    Args:
        db: Database session
        
    Returns:
        OnboardingService instance
    """
    return OnboardingService(db)
