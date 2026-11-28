# exceptions.py
from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data
        message = "Validation failed" if response.status_code == 400 else str(
            detail.get("detail", "Request failed")) if isinstance(detail, dict) else "Request failed"
        response.data = {"success": False, "message": message, "data": None,
                         "errors": detail if response.status_code == 400 else None}
    return response