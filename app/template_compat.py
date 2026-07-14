from __future__ import annotations

from typing import Any

from fastapi.templating import Jinja2Templates as _Jinja2Templates


class Jinja2Templates(_Jinja2Templates):
    def TemplateResponse(self, *args: Any, **kwargs: Any):
        if args and isinstance(args[0], str):
            name = args[0]
            context = args[1] if len(args) > 1 else kwargs.pop("context", None)
            context = dict(context or {})
            request = context.get("request") or kwargs.pop("request", None)
            if request is None:
                raise ValueError("TemplateResponse context must include request")
            return super().TemplateResponse(request, name, context, *args[2:], **kwargs)
        return super().TemplateResponse(*args, **kwargs)
