import json

import use_model
from parse import parse_json
from prompts import system_prompt, user_prompt_template
from val_and_runtool import run_tool_call, validate_tool_call


class Model:
    def __init__(self, level="local", sys_prompt=system_prompt):
        self.level = level
        self.sys_prompt = sys_prompt

    def call(self, messages):
        return use_model.run_messages(messages)

    def parse_call(self, raw_text):
        return parse_json(raw_text)

    def val_and_run(self, parsed_text):
        valid, error = validate_tool_call(parsed_text)
        if not valid:
            return {
                "ok": False,
                "error": error,
                "tool": parsed_text.get("tool") if isinstance(parsed_text, dict) else None,
                "result": None,
            }
        return run_tool_call(parsed_text)

    def display_creds(self):
        print(self.level)


class AgentRuntime:
    def __init__(self, model=None, max_steps=10):
        self.model = model or Model()
        self.max_steps = max_steps

    def build_messages(self, user_message, computer_context=""):
        return [
            {"role": "system", "content": self.model.sys_prompt},
            {
                "role": "user",
                "content": user_prompt_template.format(
                    user_message=user_message,
                    computer_context=computer_context,
                ),
            },
        ]

    def append_tool_result(self, messages, raw_response, tool_result):
        messages.append({"role": "assistant", "content": raw_response})
        messages.append(
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "tool_result": tool_result,
                    }
                ),
            }
        )

    def append_parse_error(self, messages, raw_response, error):
        messages.append({"role": "assistant", "content": raw_response})
        messages.append(
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "parse_error": str(error),
                        "instruction": "Return valid JSON after the thinking block.",
                    }
                ),
            }
        )

    def loop(self, user_message, computer_context=""):
        messages = self.build_messages(user_message, computer_context)

        for _ in range(self.max_steps):
            raw_response = self.model.call(messages)

            try:
                data = self.model.parse_call(raw_response)
            except ValueError as error:
                self.append_parse_error(messages, raw_response, error)
                continue

            if data.get("type") == "final":
                return data.get("message", "")

            if data.get("type") == "tool_call":
                tool_result = self.model.val_and_run(data)
                self.append_tool_result(messages, raw_response, tool_result)
                continue

            self.append_parse_error(
                messages,
                raw_response,
                f"Unknown response type: {data.get('type')}",
            )

        return "Stopped: max steps reached."

    def run(self, user_message, computer_context=""):
        return self.loop(user_message, computer_context)
