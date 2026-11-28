# responses.py
from rest_framework.response import Response

def ok(data=None, message="Success", status=200):
    return Response({"success": True, "message": message, "data": data, "errors": None}, status=status)

def fail(errors=None, message="Request failed", status=400):
    return Response({"success": False, "message": message, "data": None, "errors": errors}, status=status)