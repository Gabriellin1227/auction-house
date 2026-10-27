from fastapi import APIRouter, Response, status

from app.auth.dependencies import CurrentUser, SessionDependency
from app.users.schemas import UserCreate, UserRead, UserUpdate
from app.users.service import UserService

router = APIRouter(prefix="/users", tags=["Usuários"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, session: SessionDependency):
    return UserService(session).create(data)


@router.get("/me", response_model=UserRead)
def read_me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserRead)
def update_me(data: UserUpdate, user: CurrentUser, session: SessionDependency):
    return UserService(session).update(user.id, data)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_me(user: CurrentUser, session: SessionDependency):
    UserService(session).deactivate(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
