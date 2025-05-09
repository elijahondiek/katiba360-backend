from typing import Any, Callable, Dict, List, Union
from sqlalchemy.sql import expression
import os
import tempfile
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import DateTime
from sqlalchemy.orm import DeclarativeMeta
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)


def generate_response(
    status_code: int,
    response_message: str,
    customer_message: str,
    body: Union[Dict[str, Any], List[Any], None] = None,
):
    """
    Generate a standard response format for API responses.
    """

    request_ref_id = str(uuid.uuid4().int)[:10]  # Generate a unique 10-digit request reference ID
    timestamp = datetime.now(timezone.utc).isoformat()

    logger.debug(f"Generating response: status_code={status_code}, "
                 f"response_message={response_message}, customer_message={customer_message}, body={body}")
    
    return {
        "header": {
            "requestRefId": request_ref_id,
            "responseCode": status_code,
            "responseMessage": response_message,
            "customerMessage": customer_message,
            "timestamp": timestamp,
        },
        "body": body,
    }


class utcnow(expression.FunctionElement):
    type = DateTime()
    inherit_cache = True


@compiles(utcnow, "postgresql")
def pg_utcnow(element, compiler, **kw):
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


def sqlalchemy_to_dict(obj):
    if isinstance(obj.__class__, DeclarativeMeta):
        return {col.name: getattr(obj, col.name) for col in obj.__table__.columns}
    raise TypeError("Provided object is not a valid SQLAlchemy model")
