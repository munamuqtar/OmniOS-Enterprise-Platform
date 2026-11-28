import ipaddress
from . import context

def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    raw = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    try:
        return str(ipaddress.ip_address(raw))
    except (ValueError, TypeError):
        return None

class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = context.start(client_ip(request))
        try:
            return self.get_response(request)
        finally:
            context.stop(token)