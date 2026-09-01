PERM_POLICY_ASK = "policy:ask"
PERM_ORDER_READ = "order:read"
PERM_ORDER_WRITE = "order:write"
PERM_ORDER_CANCEL = "order:cancel"

DEMO_USERS = {
    "tutor": {"id": 3, "password": "tutor123", "role": "tutor"},
    "admin": {"id": 1, "password": "admin123", "role": "admin"},
    "lecturer": {"id": 4, "password": "lec123", "role": "lecturer"},
}
ROLE_PERMS = {
    "guest": frozenset({PERM_POLICY_ASK}),
    "lecturer": frozenset({PERM_POLICY_ASK}),
    "tutor": frozenset({PERM_POLICY_ASK, PERM_ORDER_READ}),
    "admin": frozenset(
        {PERM_POLICY_ASK, PERM_ORDER_READ, PERM_ORDER_WRITE, PERM_ORDER_CANCEL}
    ),
}


def has_perm(user, perm) -> bool:
    if user is None:
        role = "guest"
    else:
        role = user.get("role") or "guest"
    return perm in ROLE_PERMS.get(role, ROLE_PERMS["guest"])


def assert_perm(user, perm):
    if has_perm(user, perm):
        return None
    return "您当前是…没有…权限"
