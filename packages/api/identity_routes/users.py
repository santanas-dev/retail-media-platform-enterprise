"""
Identity API — Users, Roles, Permissions, and Audit Events.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from packages.api.dependencies import (
    get_current_active_user,
    get_db,
    get_scope_context,
    require_permission,
    set_rls_context,
)
from packages.domain import repository
from packages.domain.scopes import ScopeContext
from packages.domain.schemas import (
    AssignRoleRequest,
    AssignRoleResponse,
    AuditEventOut,
    CreateLocalAdvertiserRequest,
    CreateLocalAdvertiserResponse,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    PaginatedAuditEvents,
    PaginatedUsers,
    PermissionOut,
    ResetPasswordRequest,
    ResetPasswordResponse,
    RoleOut,
    UserDetailOut,
    UserOut,
    UserRoleAssignmentOut,
    UserStatusResponse,
)

router = APIRouter()


def _is_global_system_admin_assignment(user_role) -> bool:
    return (
        user_role.scope_type is None
        and user_role.role is not None
        and user_role.role.code == "system_admin"
    )


async def _deny_user_action(
    db,
    *,
    actor_user_id: str,
    target_user_id: str,
    action: str,
    status_code: int,
    code: str,
    message: str,
    details: dict,
):
    """Audit a refused action on a user, persist the audit row, then refuse.

    The commit comes first: get_db rolls the transaction back on the
    exception, and the refusal must stay on record.
    """
    await repository.create_audit_event(
        db,
        actor_user_id=actor_user_id,
        action=action,
        target_type="user",
        target_id=target_user_id,
        details=details,
    )
    await db.commit()
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


async def _deny_role_change(
    db,
    *,
    reason: str,
    role_code: str,
    scope_type: str | None,
    scope_id: str | None,
    **kwargs,
):
    await _deny_user_action(
        db,
        details={
            "role_code": role_code,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "reason": reason,
        },
        **kwargs,
    )


async def _require_actor_covers_target(
    db, *, actor_user_id: str, target, denied_action: str
) -> None:
    """Refuse to act on an account that outranks the actor.

    Taking over or reviving an account is as good as holding its roles, and
    disabling one takes its holder out of play, so the same subset rule as
    in assign_role applies: the target's global
    permissions must be within the actor's.  A break-glass account can be
    managed by a global system_admin only.
    """
    reason = None
    if target.is_break_glass and not await repository.user_has_global_role(
        db, actor_user_id, "system_admin"
    ):
        reason = "break_glass_requires_system_admin"
    else:
        actor_perms = await repository.get_user_permissions(
            db, actor_user_id, global_only=True
        )
        target_perms = await repository.get_user_permissions(
            db, target.id, global_only=True
        )
        if not target_perms <= actor_perms:
            reason = "exceeds_actor_permissions"
    if reason is not None:
        await _deny_user_action(
            db,
            actor_user_id=actor_user_id,
            target_user_id=target.id,
            action=denied_action,
            status_code=403,
            code="TARGET_EXCEEDS_ACTOR_PERMISSIONS",
            message="Cannot manage a user whose permissions exceed your own",
            details={"reason": reason},
        )


def _generate_user_code(username: str) -> str:
    """Generate a unique, server-derived user code.

    The previous ``username.upper().replace(" ", "_")[:8]`` truncated to 8
    chars, so any two usernames sharing a prefix (e.g. every ``smoke_adv_*``)
    collided on the ``ix_users_code`` unique constraint → HTTP 500 on the
    second create. A bounded prefix (≤32) plus an 8-hex UUID suffix keeps the
    code ≤ 41 chars (well under the ``users.code`` String(64) limit) and unique
    regardless of shared prefixes.
    """
    prefix = username.upper().replace(" ", "_")[:32]
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@router.get("/users", response_model=PaginatedUsers)
async def list_users(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db=Depends(get_db, scope="function"),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.read")),
):
    items, total = await repository.list_users(db, limit=limit, offset=offset)
    return PaginatedUsers(
        items=[UserOut.model_validate(u) for u in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/users/{user_id}", response_model=UserDetailOut)
async def get_user(
    user_id: str,
    db=Depends(get_db, scope="function"),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.read")),
):
    user = await repository.get_user_detail(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    role_assignments = []
    for ur in user.roles:
        role_code = ur.role.code if ur.role else ""
        role_name = ur.role.name if ur.role else ""
        role_assignments.append(
            UserRoleAssignmentOut(
                id=ur.id,
                role_id=ur.role_id,
                role_code=role_code,
                role_name=role_name,
                scope_type=ur.scope_type,
                scope_id=ur.scope_id,
            )
        )

    must_change = False
    cred = await repository.get_user_local_credential(db, user_id)
    if cred:
        must_change = cred.must_change_password

    return UserDetailOut(
        id=user.id,
        code=user.code,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        auth_provider=user.auth_provider,
        status=user.status,
        is_break_glass=user.is_break_glass,
        must_change_password=must_change,
        roles=role_assignments,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post(
    "/users/local-advertiser",
    response_model=CreateLocalAdvertiserResponse,
    status_code=201,
)
async def create_local_advertiser(
    body: CreateLocalAdvertiserRequest,
    db=Depends(get_db, scope="function"),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    from packages.security.password import hash_password

    existing = await repository.find_user_by_username(db, body.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    org = await repository.get_advertiser_organization(db, body.advertiser_organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Advertiser organization not found")

    one_time_password: str | None = None
    if body.auto_generate_password:
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(16))
        one_time_password = password
    elif body.temporary_password:
        password = body.temporary_password
    else:
        raise HTTPException(
            status_code=422,
            detail="Either temporary_password or auto_generate_password must be provided",
        )

    password_hash = hash_password(password)

    roles = await repository.list_roles(db)
    advertiser_role = next((r for r in roles if r.code == "advertiser"), None)
    if advertiser_role is None:
        raise HTTPException(status_code=500, detail="Advertiser role not found in system")

    code = _generate_user_code(body.username)

    user_id = str(uuid.uuid4())
    user = await repository.create_local_advertiser_user(
        db,
        user_id=user_id,
        code=code,
        username=body.username,
        display_name=body.display_name,
        password_hash=password_hash,
        advertiser_organization_id=body.advertiser_organization_id,
        role_id=advertiser_role.id,
        must_change_password=body.must_change_password,
        is_active=body.is_active,
    )

    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=scope.user_id,
        action="user.created",
        target_type="user",
        target_id=user.id,
        details={"username": body.username, "org_id": body.advertiser_organization_id},
    )

    await db.commit()

    return CreateLocalAdvertiserResponse(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        one_time_password=one_time_password,
    )


@router.post("/users/{user_id}/deactivate", response_model=UserStatusResponse)
async def deactivate_user(
    user_id: str,
    db=Depends(get_db, scope="function"),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    # Serialize with concurrent deactivations / role removals before reading
    # the target, so two requests cannot each see "one more admin left".
    await repository.lock_admin_membership(db)

    user = await repository.get_user_detail(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status == "inactive":
        raise HTTPException(status_code=409, detail="User is already inactive")

    if user_id == scope.user_id:
        raise HTTPException(status_code=409, detail="Cannot deactivate your own account")

    await _require_actor_covers_target(
        db,
        actor_user_id=scope.user_id,
        target=user,
        denied_action="user.deactivate_denied",
    )

    is_admin = any(_is_global_system_admin_assignment(ur) for ur in user.roles)

    if user.is_break_glass:
        count = await repository.count_active_break_glass_users(db)
        if count <= 1:
            raise HTTPException(
                status_code=409,
                detail="Cannot deactivate the last active break-glass user",
            )
        if is_admin and await repository.count_active_break_glass_admin_users(db) <= 1:
            raise HTTPException(
                status_code=409,
                detail="Cannot deactivate the last active break-glass user",
            )

    if is_admin:
        admin_count = await repository.count_active_admin_users(db)
        if admin_count <= 1:
            raise HTTPException(
                status_code=409,
                detail="Cannot deactivate the last active system admin",
            )

    await repository.set_user_status(db, user_id, "inactive")

    from packages.auth.repository import revoke_all_sessions_for_user
    await revoke_all_sessions_for_user(db, user_id)

    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=scope.user_id,
        action="user.deactivated",
        target_type="user",
        target_id=user_id,
    )

    await db.commit()

    return UserStatusResponse(
        user_id=user_id,
        status="inactive",
        message="User deactivated. All sessions revoked.",
    )


@router.post("/users/{user_id}/activate", response_model=UserStatusResponse)
async def activate_user(
    user_id: str,
    db=Depends(get_db, scope="function"),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    user = await repository.get_user_detail(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status == "active":
        raise HTTPException(status_code=409, detail="User is already active")

    await _require_actor_covers_target(
        db,
        actor_user_id=scope.user_id,
        target=user,
        denied_action="user.activate_denied",
    )

    await repository.set_user_status(db, user_id, "active")

    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=scope.user_id,
        action="user.activated",
        target_type="user",
        target_id=user_id,
    )

    await db.commit()

    return UserStatusResponse(
        user_id=user_id,
        status="active",
        message="User activated.",
    )


@router.post(
    "/users/{user_id}/reset-password",
    response_model=ResetPasswordResponse,
)
async def reset_password(
    user_id: str,
    body: ResetPasswordRequest,
    db=Depends(get_db, scope="function"),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    user = await repository.get_user_detail(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user_id == scope.user_id:
        raise HTTPException(
            status_code=422,
            detail="Cannot reset your own password via admin endpoint. Use /auth/change-password instead.",
        )

    await _require_actor_covers_target(
        db,
        actor_user_id=scope.user_id,
        target=user,
        denied_action="user.password_reset_denied",
    )

    if not user.auth_provider.startswith("local_"):
        raise HTTPException(
            status_code=422,
            detail="Password reset is only available for local accounts, not " + user.auth_provider,
        )

    cred = await repository.get_user_local_credential(db, user_id)
    if cred is None:
        raise HTTPException(
            status_code=422,
            detail="No local credentials found for this user",
        )

    from packages.security.password import hash_password
    one_time_password: str | None = None
    if body.auto_generate_password:
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(16))
        one_time_password = password
    elif body.new_temporary_password:
        password = body.new_temporary_password
    else:
        raise HTTPException(
            status_code=422,
            detail="Either new_temporary_password or auto_generate_password must be provided",
        )

    password_hash = hash_password(password)

    await repository.update_local_credential_password(db, user_id, password_hash)

    sessions_revoked = False
    if body.revoke_sessions:
        from packages.auth.repository import revoke_all_sessions_for_user
        count = await revoke_all_sessions_for_user(db, user_id)
        sessions_revoked = count > 0

    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=scope.user_id,
        action="user.password_reset",
        target_type="user",
        target_id=user_id,
        details={"sessions_revoked": sessions_revoked},
    )

    await db.commit()

    return ResetPasswordResponse(
        user_id=user_id,
        must_change_password=True,
        sessions_revoked=sessions_revoked,
        one_time_password=one_time_password,
    )


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(
    db=Depends(get_db, scope="function"),
    _claims: dict = Depends(require_permission("roles.read")),
):
    items = await repository.list_roles(db)
    return [RoleOut.model_validate(r) for r in items]


# ---------------------------------------------------------------------------
# User Role assignments
# ---------------------------------------------------------------------------


@router.put(
    "/users/{user_id}/roles",
    response_model=AssignRoleResponse,
    status_code=201,
)
async def assign_role(
    user_id: str,
    body: AssignRoleRequest,
    db=Depends(get_db, scope="function"),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("roles.manage")),
):
    user = await repository.get_user_detail(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    role = await repository.find_role_by_code(db, body.role_code)
    if role is None:
        raise HTTPException(status_code=404, detail=f"Role '{body.role_code}' not found")

    # Validate scope consistency
    if (body.scope_type is None) != (body.scope_id is None):
        raise HTTPException(
            status_code=422,
            detail="scope_type and scope_id must be both set or both null",
        )

    if body.scope_type == "advertiser" and body.scope_id:
        org = await repository.get_advertiser_organization(db, body.scope_id)
        if org is None:
            raise HTTPException(
                status_code=404,
                detail=f"Advertiser organization '{body.scope_id}' not found",
            )

    if user_id == scope.user_id:
        await _deny_role_change(
            db,
            actor_user_id=scope.user_id,
            target_user_id=user_id,
            action="user.role_assign_denied",
            status_code=403,
            code="SELF_ROLE_ASSIGNMENT_FORBIDDEN",
            message="Cannot assign a role to yourself",
            reason="self_assign",
            role_code=role.code,
            scope_type=body.scope_type,
            scope_id=body.scope_id,
        )

    actor_perms = await repository.get_user_permissions(
        db, scope.user_id, global_only=True
    )
    role_perms = await repository.get_role_permission_codes(db, role.id)
    if not role_perms <= actor_perms:
        await _deny_role_change(
            db,
            actor_user_id=scope.user_id,
            target_user_id=user_id,
            action="user.role_assign_denied",
            status_code=403,
            code="ROLE_EXCEEDS_ACTOR_PERMISSIONS",
            message="Cannot assign a role that exceeds your own permissions",
            reason="exceeds_actor_permissions",
            role_code=role.code,
            scope_type=body.scope_type,
            scope_id=body.scope_id,
        )

    user_role = await repository.assign_user_role(
        db,
        user_id=user_id,
        role_id=role.id,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
    )

    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=scope.user_id,
        action="user.role_assigned",
        target_type="user",
        target_id=user_id,
        details={
            "role_code": body.role_code,
            "scope_type": body.scope_type,
            "scope_id": body.scope_id,
        },
    )

    await db.commit()

    return AssignRoleResponse(
        id=user_role.id,
        user_id=user_id,
        role_id=role.id,
        role_code=role.code,
        role_name=role.name,
        scope_type=body.scope_type,
        scope_id=body.scope_id,
        message="Role assigned.",
    )


@router.delete("/users/{user_id}/roles/{assignment_id}", status_code=204)
async def remove_role(
    user_id: str,
    assignment_id: str,
    db=Depends(get_db, scope="function"),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("roles.manage")),
):
    assignment = await repository.get_user_role_assignment(db, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Role assignment not found")

    if assignment.user_id != user_id:
        raise HTTPException(
            status_code=404,
            detail="Role assignment does not belong to this user",
        )

    role = await repository.get_role(db, assignment.role_id)
    role_code = role.code if role is not None else ""
    denial = dict(
        actor_user_id=scope.user_id,
        target_user_id=user_id,
        action="user.role_remove_denied",
        role_code=role_code,
        scope_type=assignment.scope_type,
        scope_id=assignment.scope_id,
    )

    actor_perms = await repository.get_user_permissions(
        db, scope.user_id, global_only=True
    )
    role_perms = await repository.get_role_permission_codes(db, assignment.role_id)
    if not role_perms <= actor_perms:
        await _deny_role_change(
            db,
            status_code=403,
            code="ROLE_EXCEEDS_ACTOR_PERMISSIONS",
            message="Cannot remove a role that exceeds your own permissions",
            reason="exceeds_actor_permissions",
            **denial,
        )

    if assignment.scope_type is None and role_code == "system_admin":
        # Lock first, read the target after: its status must not change
        # between the read and the count.
        await repository.lock_admin_membership(db)
        target = await repository.get_user_detail(db, user_id)
        if target is not None and target.status == "active":
            if await repository.count_active_admin_users(db) <= 1:
                await _deny_role_change(
                    db,
                    status_code=409,
                    code="LAST_SYSTEM_ADMIN",
                    message="Cannot remove the last active system admin role",
                    reason="last_system_admin",
                    **denial,
                )
            if (
                target.is_break_glass
                and await repository.count_active_break_glass_admin_users(db) <= 1
            ):
                await _deny_role_change(
                    db,
                    status_code=409,
                    code="LAST_BREAK_GLASS_ADMIN",
                    message=(
                        "Cannot remove the system admin role from the last "
                        "active break-glass user"
                    ),
                    reason="last_break_glass_admin",
                    **denial,
                )

    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=scope.user_id,
        action="user.role_removed",
        target_type="user",
        target_id=user_id,
        details={
            "role_id": assignment.role_id,
            "assignment_id": assignment_id,
        },
    )

    await repository.remove_user_role(db, assignment_id)
    await db.commit()


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


@router.get("/permissions", response_model=list[PermissionOut])
async def list_permissions(
    db=Depends(get_db, scope="function"),
    _claims: dict = Depends(require_permission("roles.read")),
):
    items = await repository.list_permissions(db)
    return [PermissionOut.model_validate(p) for p in items]


# ---------------------------------------------------------------------------
# Audit Events
# ---------------------------------------------------------------------------


@router.get("/audit-events", response_model=PaginatedAuditEvents)
async def list_audit_events(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
    db=Depends(get_db, scope="function"),
    _claims: dict = Depends(require_permission("audit.read")),
):
    items, total = await repository.list_audit_events(db, limit=limit, offset=offset)
    return PaginatedAuditEvents(
        items=[AuditEventOut.model_validate(e) for e in items],
        total=total,
        limit=limit,
        offset=offset,
    )
