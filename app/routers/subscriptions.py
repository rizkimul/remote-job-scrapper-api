from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.subscription import SubscribeRequest, SubscriptionResponse
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def get_subscription_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> SubscriptionService:
    """FastAPI dependency that returns a SubscriptionService bound to the request session."""
    return SubscriptionService(session)


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def subscribe(
    body: SubscribeRequest,
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> SubscriptionResponse:
    """Subscribe an email address to the daily remote job digest.

    Idempotent — re-subscribing an existing email updates filters and reactivates it.

    Returns:
        The created or updated subscription.
    """
    return await service.subscribe(
        email=body.email,
        tags_filter=body.tags_filter,
        min_salary=body.min_salary,
    )


@router.delete("/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe(
    email: str,
    service: Annotated[SubscriptionService, Depends(get_subscription_service)],
) -> None:
    """Unsubscribe an email address from the daily digest (soft delete).

    Returns:
        204 No Content on success.

    Raises:
        404 if the email is not found.
    """
    found = await service.unsubscribe(email.lower().strip())
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription for '{email}' not found.",
        )
