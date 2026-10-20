from fastapi import Request
from fastapi.security import HTTPAuthorizationCredentials
from langsmith.run_helpers import get_current_run_tree
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


def score(key: str, value: float) -> None:
    run = get_current_run_tree()
    if run is not None:
        run.client.create_feedback(run.id, key, score=value, trace_id=run.trace_id)
