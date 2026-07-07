"""
User endpoints. Only the "me" profile route is implemented here —
add admin/user-management routes as the product requires them.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.user import UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_active_user)):
    return current_user
