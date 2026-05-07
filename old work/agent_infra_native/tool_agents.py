from ollama import chat
from tools import open_app, open_url, list_running_apps, get_frontmost_app, get_weather, get_datetime, get_battery, notify, build_computer_state



build_tool  = [open_app, open_url, list_running_apps, get_frontmost_app, get_datetime, get_battery, notify, build_computer_state]

tool_map = {tool.__name__: tool for tool in build_tool}

MODEL = "llama3.1:8b"

RESEASONING_MODEL = "qwen3.5:4b"

DEEPSEEK = "deepseek-r1:8b"

def chat_with_tools_and_messages(messages: list):
    response = chat(
        model=RESEASONING_MODEL,
        messages=messages,
        tools=build_tool,
        stream=True,
    )
    chunks = []
    tool_calls = []

    for chunk in response:
        message = chunk["message"]

        content = message.get("content", "")
        thinking = message.get("thinking", False)
        print(thinking, end="")
        print(content, end="", flush=True)
        chunks.append(content)

        if message.get("tool_calls"):
            tool_calls.extend(message["tool_calls"])

    print()
    return {
        "content": "".join(chunks),
        "tool_calls": tool_calls,
    }



system_prompt = """
You are J.A.R.V.I.S running locally on the user's computer.

Use tools only when needed.
Do not call tools for casual conversation.

Tool rules:
- open_app(app_name): open a local desktop application by name
- move_resize_app(app_name, x, y, width, height): move and resize an app window
- open_url(url): open a website URL in the browser
- list_running_apps(): list currently running local applications
- get_frontmost_app(): get the currently focused app
- get_datetime(): get the current date and time
- get_battery(): get the current battery status
- notify(title, message): send a desktop notification
- build_computer_state(): get a summary of frontmost app, datetime, and battery

Never pass a URL to open_app.
Never pass an app name to open_url.
After tool results come back, either call another needed tool or answer the user.
"""




def native_tool_caller_agent(user_input, max_steps = 10) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "user", "content": user_input})

    for step in range(max_steps):
        response = chat_with_tools_and_messages(messages)

        print("\n STEP COMPLETE: \n ")

        tool_calls = response["tool_calls"]
        content = response["content"]

        assistant_message = {"role": "assistant", "content": content}
        if tool_calls:
            assistant_message["tool_calls"] = tool_calls
        messages.append(assistant_message)

        if tool_calls:
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                args = tool_call["function"].get("arguments", {}) or {}
                print("RUNNING TOOL:", tool_name, args)
                tool_result = tool_map[tool_name](**args)

                messages.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": str(tool_result),
                })

            continue

        return content

    return "MAX Steps reached"



def chat_with_native():
    while True:
        user_input = input("User: ")
        if user_input.lower() == "quit":
            break
        try:
            print("Agent: " + native_tool_caller_agent(user_input))
        except Exception as e:
            print("Error:", e)



chat_with_native()