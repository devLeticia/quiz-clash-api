import asyncio
import hashlib
import secrets
import time
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket

from quiz_clash.schemas.question import Question

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 5
MAX_PLAYERS = 2
MAX_HP = 100
ROOM_TTL_SECONDS = 2 * 60 * 60


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class Player:
    id: str
    host: bool
    nickname: str = ""
    hero: int = 0
    hp: int = MAX_HP
    socket: WebSocket | None = None
    participant_id: str | None = None


@dataclass
class Answer:
    option: int
    correct: bool
    at: int


@dataclass
class Round:
    question: Question
    ends_at: int
    answers: dict[str, Answer] = field(default_factory=dict)
    done: asyncio.Event = field(default_factory=asyncio.Event)


@dataclass
class Room:
    code: str
    quiz_id: str
    title: str
    host_token_hash: str
    players: list[Player]
    status: str = "lobby"
    task: asyncio.Task | None = None
    current: Round | None = None
    winner_id: str | None = None
    rematch_by: str | None = None
    created_at: float = field(default_factory=time.time)


_rooms: dict[str, Room] = {}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _new_code() -> str:
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if code not in _rooms:
            return code


def _purge_expired() -> None:
    limit = time.time() - ROOM_TTL_SECONDS
    for code in [code for code, room in _rooms.items() if room.created_at < limit]:
        room = _rooms.pop(code)
        if room.task:
            room.task.cancel()


def create_room(quiz_id: str, title: str, host_participant_id: str) -> tuple[Room, str]:
    _purge_expired()
    token = secrets.token_urlsafe(32)
    host = Player(id=uuid.uuid4().hex, host=True, participant_id=host_participant_id)
    room = Room(
        code=_new_code(),
        quiz_id=quiz_id,
        title=title,
        host_token_hash=_hash(token),
        players=[host],
    )
    _rooms[room.code] = room
    return room, token


def get_room(code: str) -> Room | None:
    return _rooms.get(code.upper())


def delete_room(room: Room) -> None:
    _rooms.pop(room.code, None)
    if room.task:
        room.task.cancel()


def seat_player(room: Room, token: str | None) -> Player | None:
    if token is not None:
        host = room.players[0]
        if _hash(token) != room.host_token_hash or host.socket is not None:
            return None
        return host

    if room.status != "lobby" or len(room.players) >= MAX_PLAYERS:
        return None
    guest = Player(id=uuid.uuid4().hex, host=False)
    room.players.append(guest)
    return guest


def opponent_of(room: Room, player: Player) -> Player | None:
    return next((p for p in room.players if p is not player), None)
