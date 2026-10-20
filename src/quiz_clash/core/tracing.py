from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from starlette.datastructures import UploadFile


def _clean(value):
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, UploadFile):
        return value.filename
    return value


def only(*names: str):
    return lambda inputs: {name: inputs[name] for name in names if name in inputs}


def trace_inputs(inputs: dict) -> dict:
    return {
        key: _clean(value)
        for key, value in inputs.items()
        if not isinstance(value, Request | HTTPAuthorizationCredentials)
    }
