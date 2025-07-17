from typing import Optional, List, Dict, Any, Union
import uuid
from datetime import datetime, date, timedelta
from fastapi import HTTPException, status, Depends
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


class UserService:
    """
    Service for handling user-related operations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.activity_logger = ActivityLogger()
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Get a user by ID
        
        Args:
            user_id: User ID
            
        Returns:
            User if found, None otherwise
        """
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email
        
        Args:
            email: User email
            
        Returns:
            User if found, None otherwise
        """
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_user_with_preferences(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Get a user with preferences
        
        Args:
            user_id: User ID
            
        Returns:
            User with preferences if found, None otherwise
        """
        query = (
            select(User)
            .options(selectinload(User.preferences))
            .where(User.id == user_id)
        )
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def get_user_complete_profile(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Get a user with all related data
        
        Args:
            user_id: User ID
            
        Returns:
            User with complete profile if found, None otherwise
        """
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
        return result.scalars().first()
    
    async def update_user_profile(self, user_id: uuid.UUID, user_data: UserUpdateRequest) -> User:
        """
        Update a user's profile
        
        Args:
            user_id: User ID
            user_data: User update data
            
        Returns:
            Updated user
            
        Raises:
            HTTPException: If user not found
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update fields if provided
        if user_data.display_name is not None:
            user.display_name = user_data.display_name
        
        if user_data.bio is not None:
            user.bio = user_data.bio
        
        if user_data.avatar_url is not None:
            user.avatar_url = user_data.avatar_url
        
        if user_data.phone is not None:
            # Check if phone already exists for another user
            if user_data.phone != user.phone:
                query = select(User).where(
                    User.phone == user_data.phone,
                    User.id != user_id
                )
                result = await self.db.execute(query)
                existing_user = result.scalars().first()
                
                if existing_user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Phone number already registered"
                    )
                
                user.phone = user_data.phone
                user.phone_verified = False  # Reset verification when phone changes
        
        user.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(user)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User {user.email} updated their profile",
            user_id=str(user_id),
            activity_type="profile_update",
            metadata={
                "updated_fields": [k for k, v in user_data.dict(exclude_unset=True).items() if v is not None]
            }
        )
        
        return user
    
    async def get_user_preferences(self, user_id: uuid.UUID) -> Optional[UserPreference]:
        """
        Get a user's preferences
        
        Args:
            user_id: User ID
            
        Returns:
            User preferences if found, None otherwise
        """
        query = select(UserPreference).where(UserPreference.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def create_user_preferences(
        self, user_id: uuid.UUID, preferences_data: UserPreferenceCreate
    ) -> UserPreference:
        """
        Create user preferences
        
        Args:
            user_id: User ID
            preferences_data: Preferences data
            
        Returns:
            Created user preferences
            
        Raises:
            HTTPException: If preferences already exist
        """
        # Check if preferences already exist
        existing_prefs = await self.get_user_preferences(user_id)
        if existing_prefs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User preferences already exist"
            )
        
        # Create preferences
        preferences = UserPreference(
            user_id=user_id,
            **preferences_data.dict()
        )
        
        self.db.add(preferences)
        await self.db.commit()
        await self.db.refresh(preferences)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User created preferences with primary language '{preferences.primary_language}' and reading level '{preferences.reading_level}'",
            user_id=str(user_id),
            activity_type="preferences_created",
            metadata=preferences_data.dict()
        )
        
        return preferences
    
    async def update_user_preferences(
        self, user_id: uuid.UUID, preferences_data: UserPreferenceUpdate
    ) -> UserPreference:
        """
        Update user preferences
        
        Args:
            user_id: User ID
            preferences_data: Preferences update data
            
        Returns:
            Updated user preferences
            
        Raises:
            HTTPException: If preferences not found
        """
        # Get existing preferences
        preferences = await self.get_user_preferences(user_id)
        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found"
            )
        
        # Update fields if provided
        update_data = preferences_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(preferences, key, value)
        
        preferences.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(preferences)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User updated preferences",
            user_id=str(user_id),
            activity_type="preferences_updated",
            metadata={
                "updated_fields": list(update_data.keys()),
                "new_values": update_data
            }
        )
        
        return preferences
    
    async def get_user_languages(self, user_id: uuid.UUID) -> List[UserLanguage]:
        """
        Get a user's languages
        
        Args:
            user_id: User ID
            
        Returns:
            List of user languages
        """
        query = select(UserLanguage).where(UserLanguage.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def add_user_language(
        self, user_id: uuid.UUID, language_data: UserLanguageCreate
    ) -> UserLanguage:
        """
        Add a language to a user
        
        Args:
            user_id: User ID
            language_data: Language data
            
        Returns:
            Created user language
            
        Raises:
            HTTPException: If language already exists for user
        """
        # Check if language already exists for user
        query = select(UserLanguage).where(
            UserLanguage.user_id == user_id,
            UserLanguage.language_code == language_data.language_code
        )
        result = await self.db.execute(query)
        existing_language = result.scalars().first()
        
        if existing_language:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Language {language_data.language_code} already added for user"
            )
        
        # If this is set as primary, unset any existing primary language
        if language_data.is_primary:
            await self._unset_primary_languages(user_id)
        
        # Create language
        language = UserLanguage(
            user_id=user_id,
            **language_data.dict()
        )
        
        self.db.add(language)
        await self.db.commit()
        await self.db.refresh(language)
        
        # Update user preferences if this is primary
        if language_data.is_primary:
            preferences = await self.get_user_preferences(user_id)
            if preferences:
                preferences.primary_language = language_data.language_code
                await self.db.commit()
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User added language '{language_data.language_code}' with proficiency '{language_data.proficiency_level}'",
            user_id=str(user_id),
            activity_type="language_added",
            metadata=language_data.dict()
        )
        
        return language
    
    async def remove_user_language(self, user_id: uuid.UUID, language_id: uuid.UUID) -> bool:
        """
        Remove a language from a user
        
        Args:
            user_id: User ID
            language_id: Language ID
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If language not found
        """
        # Get language
        query = select(UserLanguage).where(
            UserLanguage.id == language_id,
            UserLanguage.user_id == user_id
        )
        result = await self.db.execute(query)
        language = result.scalars().first()
        
        if not language:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Language not found"
            )
        
        # Check if this is the only language
        query = select(func.count()).select_from(UserLanguage).where(UserLanguage.user_id == user_id)
        result = await self.db.execute(query)
        count = result.scalar()
        
        if count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the only language"
            )
        
        was_primary = language.is_primary
        language_code = language.language_code
        
        # Delete language
        await self.db.delete(language)
        await self.db.commit()
        
        # If this was primary, set another language as primary
        if was_primary:
            query = select(UserLanguage).where(UserLanguage.user_id == user_id)
            result = await self.db.execute(query)
            remaining_language = result.scalars().first()
            
            if remaining_language:
                remaining_language.is_primary = True
                
                # Update user preferences
                preferences = await self.get_user_preferences(user_id)
                if preferences:
                    preferences.primary_language = remaining_language.language_code
                
                await self.db.commit()
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User removed language '{language_code}'",
            user_id=str(user_id),
            activity_type="language_removed",
            metadata={
                "language_code": language_code,
                "was_primary": was_primary
            }
        )
        
        return True
    
    async def set_primary_language(self, user_id: uuid.UUID, language_id: uuid.UUID) -> UserLanguage:
        """
        Set a language as primary for a user
        
        Args:
            user_id: User ID
            language_id: Language ID
            
        Returns:
            Updated language
            
        Raises:
            HTTPException: If language not found
        """
        # Get language
        query = select(UserLanguage).where(
            UserLanguage.id == language_id,
            UserLanguage.user_id == user_id
        )
        result = await self.db.execute(query)
        language = result.scalars().first()
        
        if not language:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Language not found"
            )
        
        # Unset any existing primary languages
        await self._unset_primary_languages(user_id)
        
        # Set this language as primary
        language.is_primary = True
        
        # Update user preferences
        preferences = await self.get_user_preferences(user_id)
        if preferences:
            preferences.primary_language = language.language_code
        
        await self.db.commit()
        await self.db.refresh(language)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User set language '{language.language_code}' as primary",
            user_id=str(user_id),
            activity_type="primary_language_set",
            metadata={
                "language_code": language.language_code,
                "language_id": str(language_id)
            }
        )
        
        return language
    
    async def _unset_primary_languages(self, user_id: uuid.UUID) -> None:
        """
        Unset all primary languages for a user
        
        Args:
            user_id: User ID
        """
        query = (
            update(UserLanguage)
            .where(
                UserLanguage.user_id == user_id,
                UserLanguage.is_primary == True
            )
            .values(is_primary=False)
        )
        await self.db.execute(query)
    
    async def get_interest_categories(self, active_only: bool = True) -> List[InterestCategory]:
        """
        Get all interest categories
        
        Args:
            active_only: Only return active categories
            
        Returns:
            List of interest categories
        """
        query = select(InterestCategory)
        
        if active_only:
            query = query.where(InterestCategory.is_active == True)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_user_interests(self, user_id: uuid.UUID) -> List[UserInterest]:
        """
        Get a user's interests with categories
        
        Args:
            user_id: User ID
            
        Returns:
            List of user interests with categories
        """
        query = (
            select(UserInterest)
            .options(selectinload(UserInterest.interest_category))
            .where(UserInterest.user_id == user_id)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def add_user_interest(
        self, user_id: uuid.UUID, interest_category_id: uuid.UUID
    ) -> UserInterest:
        """
        Add an interest to a user
        
        Args:
            user_id: User ID
            interest_category_id: Interest category ID
            
        Returns:
            Created user interest
            
        Raises:
            HTTPException: If interest already exists for user or category not found
        """
        # Check if category exists
        query = select(InterestCategory).where(
            InterestCategory.id == interest_category_id,
            InterestCategory.is_active == True
        )
        result = await self.db.execute(query)
        category = result.scalars().first()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interest category not found or inactive"
            )
        
        # Check if interest already exists for user
        query = select(UserInterest).where(
            UserInterest.user_id == user_id,
            UserInterest.interest_category_id == interest_category_id
        )
        result = await self.db.execute(query)
        existing_interest = result.scalars().first()
        
        if existing_interest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Interest {category.name} already added for user"
            )
        
        # Create interest
        interest = UserInterest(
            user_id=user_id,
            interest_category_id=interest_category_id
        )
        
        self.db.add(interest)
        await self.db.commit()
        await self.db.refresh(interest)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User added interest '{category.name}'",
            user_id=str(user_id),
            activity_type="interest_added",
            metadata={
                "interest_category_id": str(interest_category_id),
                "interest_name": category.name
            }
        )
        
        return interest
    
    async def remove_user_interest(self, user_id: uuid.UUID, interest_id: uuid.UUID) -> bool:
        """
        Remove an interest from a user
        
        Args:
            user_id: User ID
            interest_id: Interest ID
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If interest not found
        """
        # Get interest with category
        query = (
            select(UserInterest)
            .options(selectinload(UserInterest.interest_category))
            .where(
                UserInterest.id == interest_id,
                UserInterest.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        interest = result.scalars().first()
        
        if not interest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interest not found"
            )
        
        category_name = interest.interest_category.name if interest.interest_category else "Unknown"
        
        # Delete interest
        await self.db.delete(interest)
        await self.db.commit()
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User removed interest '{category_name}'",
            user_id=str(user_id),
            activity_type="interest_removed",
            metadata={
                "interest_id": str(interest_id),
                "interest_name": category_name
            }
        )
        
        return True
    
    async def get_user_accessibility(self, user_id: uuid.UUID) -> Optional[UserAccessibility]:
        """
        Get a user's accessibility settings
        
        Args:
            user_id: User ID
            
        Returns:
            User accessibility settings if found, None otherwise
        """
        query = select(UserAccessibility).where(UserAccessibility.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
    async def create_user_accessibility(
        self, user_id: uuid.UUID, accessibility_data: UserAccessibilityCreate
    ) -> UserAccessibility:
        """
        Create user accessibility settings
        
        Args:
            user_id: User ID
            accessibility_data: Accessibility data
            
        Returns:
            Created user accessibility settings
            
        Raises:
            HTTPException: If settings already exist
        """
        # Check if settings already exist
        existing_settings = await self.get_user_accessibility(user_id)
        if existing_settings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User accessibility settings already exist"
            )
        
        # Create settings
        accessibility = UserAccessibility(
            user_id=user_id,
            **accessibility_data.dict()
        )
        
        self.db.add(accessibility)
        await self.db.commit()
        await self.db.refresh(accessibility)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User created accessibility settings",
            user_id=str(user_id),
            activity_type="accessibility_created",
            metadata=accessibility_data.dict()
        )
        
        return accessibility
    
    async def update_user_accessibility(
        self, user_id: uuid.UUID, accessibility_data: UserAccessibilityUpdate
    ) -> UserAccessibility:
        """
        Update user accessibility settings
        
        Args:
            user_id: User ID
            accessibility_data: Accessibility update data
            
        Returns:
            Updated user accessibility settings
            
        Raises:
            HTTPException: If settings not found
        """
        # Get existing settings
        accessibility = await self.get_user_accessibility(user_id)
        if not accessibility:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User accessibility settings not found"
            )
        
        # Update fields if provided
        update_data = accessibility_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(accessibility, key, value)
        
        accessibility.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(accessibility)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User updated accessibility settings",
            user_id=str(user_id),
            activity_type="accessibility_updated",
            metadata={
                "updated_fields": list(update_data.keys()),
                "new_values": update_data
            }
        )
        
        return accessibility
    
    async def get_onboarding_progress(self, user_id: uuid.UUID) -> Optional[OnboardingProgress]:
        """
        Get a user's onboarding progress
        
        Args:
            user_id: User ID
            
        Returns:
            Onboarding progress if found, None otherwise
        """
        query = select(OnboardingProgress).where(OnboardingProgress.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalars().first()
    
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
            HTTPException: If progress not found
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
            user = await self.get_user_by_id(user_id)
            if user:
                user.onboarding_completed = True
        
        progress.updated_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(progress)
        
        # Log activity
        await self.activity_logger.log_activity(
            f"User updated onboarding progress to {progress.progress_percentage}%",
            user_id=str(user_id),
            activity_type="onboarding_progress",
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
            HTTPException: If progress not found or invalid step name
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
            user = await self.get_user_by_id(user_id)
            if user:
                user.onboarding_completed = True
        
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


# Dependency to get UserService
def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """
    Dependency to get UserService instance
    
    Args:
        db: Database session
        
    Returns:
        UserService instance
    """
    return UserService(db)
