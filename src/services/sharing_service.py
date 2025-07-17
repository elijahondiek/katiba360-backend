from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid
import logging
from fastapi import Depends

from src.models.user_models import SharingEvent, User
from src.schemas.user_schemas import SharingEventCreate, SharingEventResponse
from src.database import get_db
from src.utils.custom_utils import utcnow

logger = logging.getLogger(__name__)


class SharingService:
    """Service for handling sharing events"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_sharing_event(self, user_id: uuid.UUID, sharing_data: SharingEventCreate) -> SharingEvent:
        """
        Create a new sharing event
        
        Args:
            user_id: UUID of the user who shared
            sharing_data: SharingEventCreate object with sharing details
            
        Returns:
            SharingEvent: The created sharing event
        """
        try:
            # Create the sharing event
            sharing_event = SharingEvent(
                user_id=user_id,
                content_type=sharing_data.content_type,
                content_id=sharing_data.content_id,
                share_method=sharing_data.share_method,
                content_url=sharing_data.content_url,
                shared_at=utcnow()
            )
            
            self.db.add(sharing_event)
            await self.db.commit()
            await self.db.refresh(sharing_event)
            
            logger.info(f"Created sharing event for user {user_id}: {sharing_data.content_type}:{sharing_data.content_id} via {sharing_data.share_method}")
            
            return sharing_event
            
        except Exception as e:
            logger.error(f"Error creating sharing event for user {user_id}: {str(e)}")
            await self.db.rollback()
            raise
    
    async def get_user_sharing_events(self, user_id: uuid.UUID, limit: int = 50, offset: int = 0) -> List[SharingEvent]:
        """
        Get sharing events for a specific user
        
        Args:
            user_id: UUID of the user
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            List[SharingEvent]: List of sharing events
        """
        try:
            query = select(SharingEvent).where(
                SharingEvent.user_id == user_id
            ).order_by(SharingEvent.shared_at.desc()).limit(limit).offset(offset)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting sharing events for user {user_id}: {str(e)}")
            raise
    
    async def get_sharing_analytics(self, user_id: uuid.UUID, days: int = 30) -> Dict[str, Any]:
        """
        Get sharing analytics for a user
        
        Args:
            user_id: UUID of the user
            days: Number of days to look back for analytics
            
        Returns:
            Dict with sharing analytics
        """
        try:
            since_date = utcnow() - timedelta(days=days)
            
            # Total shares in the period
            total_shares_query = select(func.count(SharingEvent.id)).where(
                and_(
                    SharingEvent.user_id == user_id,
                    SharingEvent.shared_at >= since_date
                )
            )
            total_shares_result = await self.db.execute(total_shares_query)
            total_shares = total_shares_result.scalar() or 0
            
            # Shares by method
            shares_by_method_query = select(
                SharingEvent.share_method,
                func.count(SharingEvent.id).label('count')
            ).where(
                and_(
                    SharingEvent.user_id == user_id,
                    SharingEvent.shared_at >= since_date
                )
            ).group_by(SharingEvent.share_method)
            
            shares_by_method_result = await self.db.execute(shares_by_method_query)
            shares_by_method = {row.share_method: row.count for row in shares_by_method_result}
            
            # Shares by content type
            shares_by_content_type_query = select(
                SharingEvent.content_type,
                func.count(SharingEvent.id).label('count')
            ).where(
                and_(
                    SharingEvent.user_id == user_id,
                    SharingEvent.shared_at >= since_date
                )
            ).group_by(SharingEvent.content_type)
            
            shares_by_content_type_result = await self.db.execute(shares_by_content_type_query)
            shares_by_content_type = {row.content_type: row.count for row in shares_by_content_type_result}
            
            # Most recent sharing event
            most_recent_query = select(SharingEvent).where(
                SharingEvent.user_id == user_id
            ).order_by(SharingEvent.shared_at.desc()).limit(1)
            
            most_recent_result = await self.db.execute(most_recent_query)
            most_recent = most_recent_result.scalar_one_or_none()
            
            return {
                "total_shares": total_shares,
                "shares_by_method": shares_by_method,
                "shares_by_content_type": shares_by_content_type,
                "most_recent_share": most_recent.shared_at if most_recent else None,
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Error getting sharing analytics for user {user_id}: {str(e)}")
            # Return empty analytics instead of raising error
            return {
                "total_shares": 0,
                "shares_by_method": {},
                "shares_by_content_type": {},
                "most_recent_share": None,
                "period_days": days
            }
    
    async def check_sharing_citizen_achievement(self, user_id: uuid.UUID) -> bool:
        """
        Check if user qualifies for "Sharing Citizen" achievement
        
        Args:
            user_id: UUID of the user
            
        Returns:
            bool: True if user qualifies for the achievement
        """
        try:
            # Count total shares for the user
            total_shares_query = select(func.count(SharingEvent.id)).where(
                SharingEvent.user_id == user_id
            )
            total_shares_result = await self.db.execute(total_shares_query)
            total_shares = total_shares_result.scalar() or 0
            
            # Sharing Citizen achievement requires 10 shares (you can adjust this threshold)
            return total_shares >= 10
            
        except Exception as e:
            logger.error(f"Error checking sharing citizen achievement for user {user_id}: {str(e)}")
            raise


async def get_sharing_service(db: AsyncSession = Depends(get_db)) -> SharingService:
    """
    Dependency to get SharingService instance
    
    Args:
        db: Database session
        
    Returns:
        SharingService: Service instance
    """
    return SharingService(db)