from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Callable, Type, TypeVar, Any

from src.database import get_db
from src.services.auth_service import AuthService
from src.services.user_service import UserService
from src.services.content_service import ContentService
from src.services.reading_service import ReadingService
from src.services.achievement_service import AchievementService
from src.services.notification_service import NotificationService
from src.services.onboarding_service import OnboardingService

# Generic type for service classes
T = TypeVar('T')

def get_service(service_class: Type[T]) -> Callable[[AsyncSession], T]:
    """
    Factory function to create a service dependency
    
    Args:
        service_class: The service class to instantiate
        
    Returns:
        A dependency function that creates and returns a service instance
    """
    def _get_service(db: AsyncSession = Depends(get_db)) -> T:
        return service_class(db)
    
    return _get_service

# Service dependencies
get_auth_service = get_service(AuthService)
get_user_service = get_service(UserService)
get_content_service = get_service(ContentService)
get_reading_service = get_service(ReadingService)
get_achievement_service = get_service(AchievementService)
get_notification_service = get_service(NotificationService)
get_onboarding_service = get_service(OnboardingService)
