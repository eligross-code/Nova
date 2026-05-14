

tool_schemas = {
    "terminal": {
        "type": "object",
        "properties": {
            "line": {"type": "string"},
            "timeout": {"type": "integer"},
        },
        "required": ["line"],
        "additionalProperties": False,
    },
}


tool_call_schema = {
    "type": "object",
    "properties": {
        "type": {"const": "tool_call"},
        "tool": {"type": "string"},
        "arguments": {"type": "object"},
    },
    "required": ["type", "tool", "arguments"],
    "additionalProperties": False,
}


final_response_schema = {
    "type": "object",
    "properties": {
        "type": {"const": "final"},
        "message": {"type": "string"},
    },
    "required": ["type", "message"],
    "additionalProperties": False,
}


response_schemas = {
    "tool_call": tool_call_schema,
    "final": final_response_schema,
}
