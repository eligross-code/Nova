# text_agent.py

import json 
from agent_core import (
    build_base_tools,
    chat_with_messages,
    parse_json,
    validate_tool_call,
    tool_schemas,
    thinking_sub_agent,
    thinking_text_agent
)

context = ""

def subagent(task, context):
    overall_message = "Goal: " + task + "\n\n" + "Context: " + context
    return thinking_sub_agent(overall_message, tools=build_base_tools(), max_steps=5)

tools = build_base_tools()
tools["sub_agent_call"] = subagent




tool_schemas["sub_agent_call"] = {
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "context": {"type": "string"},
        },
        "required": ["task", "context"],
        "additionalProperties": False
    }


def main_reasoning():

    while True:
        

        user_input = input("User: ")
        if user_input.lower() == "quit":
            break
        try:
            response = thinking_text_agent(user_input, tools=tools)            
            print("Agent:", response)
        except Exception as e:
            print("Error:", e)








main_reasoning()











def main_reasoning_with_prompt(prompt):
    while True:
        

        user_input = input("User: ")
        if user_input.lower() == "quit":
            break
        try:
            response = thinking_text_agent(prompt + "\n\n" + user_input)
            print("Agent:", response)
        except Exception as e:
            print("Error:", e)


main_reasoning_with_prompt("""You are helping me do a desktop situation check.

Your job:
1. First inspect the current computer state using the most efficient tool choice.
2. Decide whether I am probably in a focused work session, a casual browsing session, or an unknown state.
3. If my battery is below 35%, send me a desktop notification warning me to plug in.
4. Otherwise, send me a desktop notification containing:
   - the current frontmost app
   - the current time
   - a one-line status summary
5. Then verify your conclusion by checking the running apps list.
6. If the running apps list changes your conclusion, say so and explain why.
7. Finish with a final answer that includes:
   - what tools you used
   - what you observed
   - what action you took
   - the updated memory

Rules:
- Use as few tools as possible.
- Avoid redundant tool calls.
- Do not expose raw tool JSON in the final answer.
- Base your reasoning only on observed tool results.""")