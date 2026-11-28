from rest_framework.renderers import JSONRenderer

class EnvelopeRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = (renderer_context or {}).get("response")
        already_wrapped = isinstance(data, dict) and "success" in data and "errors" in data
        if response is None or already_wrapped or response.status_code >= 400 or response.status_code == 204:
            return super().render(data, accepted_media_type, renderer_context)
        wrapped = {"success": True, "message": "OK", "data": data, "errors": None}
        return super().render(wrapped, accepted_media_type, renderer_context)