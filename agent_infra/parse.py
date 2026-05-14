import json
from typing import Any, Dict


def strip_private_reasoning(raw_response: str) -> str:
    end_tag = "</think>"
    end = raw_response.rfind(end_tag)
    if end == -1:
        return raw_response.strip()
    return raw_response[end + len(end_tag):].strip()


def extract_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found")

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(text)):
        char = text[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    raise ValueError("Unclosed JSON object")


def parse_json(raw_response: str) -> Dict[str, Any]:
    executable_text = strip_private_reasoning(raw_response)
    json_text = extract_json_object(executable_text)
    parsed = json.loads(json_text)

    if not isinstance(parsed, dict):
        raise ValueError("Executable JSON must be an object")

    return parsed


def parse_executable(raw_response: str) -> Dict[str, Any]:
    return parse_json(raw_response)
