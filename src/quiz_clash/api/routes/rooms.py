from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from quiz_clash.api.routes.quiz import bearer_scheme, require_participant
from quiz_clash.core.exceptions import QuizNotFoundError
from quiz_clash.core.quiz_store import get_quiz
from quiz_clash.core.rate_limiter import limiter
from quiz_clash.core.room_store import create_room, get_room, seat_player
from quiz_clash.services.match import broadcast, handle_message, leave, lobby_message, send

router = APIRouter()

ROOM_NOT_FOUND = 4404
ROOM_UNAVAILABLE = 4409


class RoomCreateRequest(BaseModel):
    quiz_id: str
    title: str = Field(default="", max_length=200)


class RoomCreateResponse(BaseModel):
    code: str
    token: str


@router.post("", response_model=RoomCreateResponse)
@limiter.limit("10/minute")
async def create_quiz_room(
    request: Request,
    body: RoomCreateRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if get_quiz(body.quiz_id) is None:
        raise QuizNotFoundError(f"Quiz '{body.quiz_id}' not found.")
    participant_id = require_participant(body.quiz_id, credentials)
    room, token = create_room(body.quiz_id, body.title, participant_id)
    return RoomCreateResponse(code=room.code, token=token)


@router.websocket("/{code}/ws")
async def room_socket(websocket: WebSocket, code: str, token: str | None = None):
    await websocket.accept()
    room = get_room(code)
    if room is None:
        await websocket.close(ROOM_NOT_FOUND)
        return
    player = seat_player(room, token)
    if player is None:
        await websocket.close(ROOM_UNAVAILABLE)
        return

    player.socket = websocket
    await send(player, {"type": "welcome", "player_id": player.id, "code": room.code})
    await broadcast(room, lobby_message(room))

    try:
        while True:
            message = await websocket.receive_json()
            if isinstance(message, dict):
                await handle_message(room, player, message)
    except (WebSocketDisconnect, ValueError):
        pass
    finally:
        await leave(room, player)
