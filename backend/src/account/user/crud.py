import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Union, List
from uuid import UUID

from backend.src.account.user.schemas import ShowUser
from backend.src.account.user.schemas import UserCreate
from backend.src.account.user.dals import UserDAL
from backend.src.account.user.models import PortalRole
from backend.src.account.user.models import User
from backend.src.account.auth.hashing import Hasher


async def _get_all_users(session: AsyncSession) -> List[User]:
    query = select(User)
    res = await session.execute(query)
    return res.scalars().all()


async def _create_new_user(body: UserCreate, session: AsyncSession) -> ShowUser:
    async with session.begin():
        user_dal = UserDAL(session)
        user = await user_dal.create_user(
            name=body.name,
            surname=body.surname,
            email=body.email,
            hashed_password=Hasher.get_password_hash(body.password),
            roles=[
                PortalRole.ROLE_PORTAL_USER,
            ],
        )
        return ShowUser(
            user_id=user.user_id,
            name=user.name,
            surname=user.surname,
            email=user.email,
            is_active=user.is_active,
        )


async def _delete_user(user_id: UUID, session: AsyncSession) -> Union[UUID, None]:
    user_dal = UserDAL(session)
    deleted_user_id = await user_dal.delete_user(
        user_id=user_id,
    )
    return deleted_user_id


async def _update_user(
    updated_user_params: dict, user_id: UUID, session: AsyncSession
) -> Union[UUID, None]:
    user_dal = UserDAL(session)
    updated_user_id = await user_dal.update_user(user_id=user_id, **updated_user_params)
    return updated_user_id


async def _get_user_by_id(user_id: UUID, session: AsyncSession) -> Union[User, None]:
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    return user


def check_user_permissions(target_user: User, current_user: User) -> bool:
    if PortalRole.ROLE_PORTAL_SUPERADMIN in current_user.roles:
        return True  # Администратор с ролью "ROLE_PORTAL_SUPERADMIN" имеет права на удаление любых пользователей
    if PortalRole.ROLE_PORTAL_SUPERADMIN in target_user.roles:
        return False  # Пользователя с ролью "ROLE_PORTAL_SUPERADMIN" нельзя удалять
    if target_user.user_id != current_user.user_id:
        # Проверка роли текущего пользователя
        if not {
            PortalRole.ROLE_PORTAL_ADMIN,
            PortalRole.ROLE_PORTAL_SUPERADMIN,
        }.intersection(current_user.roles):
            return False
        # Проверка попытки администратора удалить пользователя с ролью "ROLE_PORTAL_SUPERADMIN"
        if PortalRole.ROLE_PORTAL_SUPERADMIN in target_user.roles:
            return False
        # check admin deactivate admin attempt
        if (
                PortalRole.ROLE_PORTAL_ADMIN in target_user.roles
                and PortalRole.ROLE_PORTAL_ADMIN in current_user.roles
        ):
            return False
        # check admin deactivate admin attempt
        if PortalRole.ROLE_PORTAL_ADMIN in target_user.roles and PortalRole.ROLE_PORTAL_ADMIN in current_user.roles:
            return False
    return True
