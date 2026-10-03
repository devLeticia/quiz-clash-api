import asyncio
import logging

from quiz_clash.core.quiz_store import (
    create_participant,
    get_participant_id,
    get_quiz,
    record_answer,
)
from quiz_clash.core.room_store import (
    MAX_HP,
    MAX_PLAYERS,
    Answer,
    Player,
    Room,
    Round,
    delete_room,
    now_ms,
    opponent_of,
)
from quiz_clash.schemas.question import Question, to_public

COUNTDOWN_MS = 3000
INTERSTITIAL_MS = 2800
REVEAL_MS = 3510
ROUND_MS = 15000
ANSWER_GRACE_MS = 500
STRIKE_MS = 1500
ROUND_END_PAUSE_MS = 1000
BASE_DAMAGE = 20
SPEED_BONUS = 10
MAX_NICKNAME = 14
PLAYABLE_HEROES = (0, 1)

logger = logging.getLogger("quiz_clash")


async def send(player: Player, message: dict) -> None:
    if player.socket is None:
        return
    try:
        await player.socket.send_json({**message, "server_now": now_ms()})
    except Exception:
        pass


async def broadcast(room: Room, message: dict) -> None:
    await asyncio.gather(*(send(player, message) for player in room.players))


async def sleep_until(timestamp: int) -> None:
    await asyncio.sleep(max(0, timestamp - now_ms()) / 1000)


def lobby_message(room: Room) -> dict:
    return {
        "type": "lobby",
        "title": room.title,
        "total": len(get_quiz(room.quiz_id) or []),
        "players": [
            {"id": p.id, "nickname": p.nickname, "hero": p.hero, "host": p.host}
            for p in room.players
        ],
    }


def start_match(room: Room, quiz_id: str, host_participant_id: str) -> None:
    host, guest = room.players
    guest_token = create_participant(quiz_id)
    host.participant_id = host_participant_id
    guest.participant_id = get_participant_id(quiz_id, guest_token)
    for player in room.players:
        player.hp = MAX_HP
    room.quiz_id = quiz_id
    room.status = "playing"
    room.winner_id = None
    room.rematch_by = None
    room.task = asyncio.create_task(run_match(room))


async def run_match(room: Room) -> None:
    try:
        questions = get_quiz(room.quiz_id) or []
        starts_at = now_ms() + COUNTDOWN_MS
        await broadcast(
            room, {"type": "match_starting", "starts_at": starts_at, "total": len(questions)}
        )
        await sleep_until(starts_at)

        for index, question in enumerate(questions):
            await play_round(room, index, question)
            if any(p.hp == 0 for p in room.players):
                break

        await finish(room, "hp" if any(p.hp == 0 for p in room.players) else "questions")
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Match crashed in room %s", room.code)


async def play_round(room: Room, index: int, question: Question) -> None:
    shows_at = now_ms() + INTERSTITIAL_MS
    opens_at = shows_at + REVEAL_MS
    ends_at = opens_at + ROUND_MS
    current = Round(question=question, ends_at=ends_at)
    room.current = current

    await broadcast(
        room,
        {
            "type": "round_start",
            "index": index,
            "question": to_public(question).model_dump(),
            "shows_at": shows_at,
            "opens_at": opens_at,
            "ends_at": ends_at,
        },
    )

    try:
        await asyncio.wait_for(current.done.wait(), (ends_at + ANSWER_GRACE_MS - now_ms()) / 1000)
    except TimeoutError:
        pass

    room.current = None
    strikes = resolve_strikes(room, current)
    await broadcast(
        room,
        {"type": "round_end", "strikes": strikes, "hp": {p.id: p.hp for p in room.players}},
    )
    await asyncio.sleep((ROUND_END_PAUSE_MS + len(strikes) * STRIKE_MS) / 1000)


def resolve_strikes(room: Room, current: Round) -> list[dict]:
    hits = sorted(
        ((player_id, answer) for player_id, answer in current.answers.items() if answer.correct),
        key=lambda hit: hit[1].at,
    )
    strikes = []
    for player_id, answer in hits:
        attacker = next(p for p in room.players if p.id == player_id)
        target = opponent_of(room, attacker)
        time_left = max(0, min(ROUND_MS, current.ends_at - answer.at)) / 1000
        damage = BASE_DAMAGE + round(SPEED_BONUS * time_left / (ROUND_MS / 1000))
        target.hp = max(0, target.hp - damage)
        strikes.append({"attacker_id": attacker.id, "damage": damage})
        if target.hp == 0:
            break
    return strikes


async def finish(room: Room, reason: str, winner: Player | None = None) -> None:
    if winner is None:
        first, second = room.players
        if first.hp != second.hp:
            winner = first if first.hp > second.hp else second
    room.status = "finished"
    room.current = None
    room.winner_id = winner.id if winner else None
    await broadcast(room, {"type": "match_end", "winner_id": room.winner_id, "reason": reason})


async def handle_answer(room: Room, player: Player, question_id: str, option: int) -> None:
    current = room.current
    if (
        room.status != "playing"
        or current is None
        or current.question.id != question_id
        or player.id in current.answers
    ):
        return
    answered_at = now_ms()
    if answered_at > current.ends_at + ANSWER_GRACE_MS:
        return

    correct = option == current.question.correct_option_index
    record_answer(room.quiz_id, player.participant_id, question_id, option, correct)
    current.answers[player.id] = Answer(option=option, correct=correct, at=answered_at)

    await send(
        player,
        {"type": "answer_result", "correct_option_index": current.question.correct_option_index},
    )
    await broadcast(room, {"type": "answered", "player_id": player.id})
    if len(current.answers) == MAX_PLAYERS:
        current.done.set()


async def handle_message(room: Room, player: Player, message: dict) -> None:
    kind = message.get("type")

    if kind == "profile" and room.status == "lobby":
        player.nickname = str(message.get("nickname", "")).strip()[:MAX_NICKNAME]
        if message.get("hero") in PLAYABLE_HEROES:
            player.hero = message["hero"]
        await broadcast(room, lobby_message(room))

    elif kind == "start" and player.host and room.status == "lobby":
        if len(room.players) == MAX_PLAYERS:
            start_match(room, room.quiz_id, player.participant_id)

    elif kind == "answer":
        option = message.get("option")
        question_id = message.get("question_id")
        if isinstance(option, int) and 0 <= option <= 3 and isinstance(question_id, str):
            await handle_answer(room, player, question_id, option)

    elif kind == "rematch_request" and room.status == "finished":
        if room.rematch_by is None and room.winner_id != player.id and _both_connected(room):
            room.rematch_by = player.id
            await broadcast(room, {"type": "rematch_requested", "player_id": player.id})

    elif kind == "rematch_accept" and room.status == "finished":
        if room.rematch_by not in (None, player.id) and _both_connected(room):
            room.status = "rematch"
            await broadcast(room, {"type": "rematch_generating"})

    elif kind == "rematch_quiz" and player.host and room.status == "rematch":
        quiz_id = str(message.get("quiz_id", ""))
        participant_id = get_participant_id(quiz_id, str(message.get("token", "")))
        if participant_id is not None:
            start_match(room, quiz_id, participant_id)

    elif kind == "rematch_failed" and player.host and room.status == "rematch":
        room.status = "finished"
        room.rematch_by = None
        await broadcast(room, {"type": "rematch_failed"})


def _both_connected(room: Room) -> bool:
    return len(room.players) == MAX_PLAYERS and all(p.socket for p in room.players)


async def leave(room: Room, player: Player) -> None:
    player.socket = None

    if room.status == "lobby":
        if player.host:
            await broadcast(room, {"type": "room_closed"})
            delete_room(room)
        else:
            room.players.remove(player)
            await broadcast(room, lobby_message(room))
        return

    if room.status == "playing":
        if room.task:
            room.task.cancel()
        await finish(room, "forfeit", opponent_of(room, player))
    else:
        room.status = "finished"
        await broadcast(room, {"type": "opponent_left"})

    if not any(p.socket for p in room.players):
        delete_room(room)
