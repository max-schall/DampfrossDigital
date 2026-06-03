"""
Network message type constants and builder helpers.

All messages are JSON objects with a mandatory "type" field.

Host → All clients
  state_update     – full serialized GameState
  map_data         – base64-encoded .dmpfmap bytes (once at game start)
  player_joined    – {slot, name, color}
  game_start       – {player_configs: list[{name,color,is_bot,slot}]}
  player_disconnected – {slot}

Client → Host
  join_lobby       – {name, color}
  action           – {type, ...params}

Host → Client (error)
  error            – {text}
"""
from __future__ import annotations
import base64
import json

MSG_STATE_UPDATE        = "state_update"
MSG_MAP_DATA            = "map_data"
MSG_PLAYER_JOINED       = "player_joined"
MSG_GAME_START          = "game_start"
MSG_PLAYER_DISCONNECTED = "player_disconnected"
MSG_JOIN_LOBBY          = "join_lobby"
MSG_ACTION              = "action"
MSG_ERROR               = "error"


def build_state_update(state_dict: dict) -> str:
    return json.dumps({"type": MSG_STATE_UPDATE, "state": state_dict})


def build_map_data(map_bytes: bytes) -> str:
    return json.dumps({
        "type": MSG_MAP_DATA,
        "data": base64.b64encode(map_bytes).decode("ascii"),
    })


def build_player_joined(slot: int, name: str, color: str) -> str:
    return json.dumps({"type": MSG_PLAYER_JOINED, "slot": slot, "name": name, "color": color})


def build_game_start(player_configs: list) -> str:
    return json.dumps({"type": MSG_GAME_START, "player_configs": player_configs})


def build_player_disconnected(slot: int) -> str:
    return json.dumps({"type": MSG_PLAYER_DISCONNECTED, "slot": slot})


def build_join_lobby(name: str, color: str) -> str:
    return json.dumps({"type": MSG_JOIN_LOBBY, "name": name, "color": color})


def build_action(action_dict: dict) -> str:
    return json.dumps({"type": MSG_ACTION, "payload": action_dict})


def build_error(text: str) -> str:
    return json.dumps({"type": MSG_ERROR, "text": text})
