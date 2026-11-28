import contextvars

_ctx = contextvars.ContextVar("audit_ctx", default=None)

def start(ip):
    return _ctx.set({"ip": ip, "user": None})

def stop(token):
    _ctx.reset(token)

def current():
    return _ctx.get() or {"ip": None, "user": None}

def set_user(user):
    ctx = _ctx.get()
    if ctx is not None:
        ctx["user"] = user