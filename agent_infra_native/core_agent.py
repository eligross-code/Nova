# agent_core.py

import json
from typing import Any, Dict
from ollama import chat

from agent_infra_native.tools import (
    open_app,
    open_url,
    list_running_apps,
    get_frontmost_app,
    get_datetime,
    get_battery,
    notify,
    build_computer_state,
)



MODEL = "llama3.1:8b"
REASONING_MODEL = "qwen3.5:4b"

tool_schemas = {
    "open_app": {
        "type": "object",
        "properties": {"app_name": {"type": "string"}},
        "required": ["app_name"],
        "additionalProperties": False,
    },
    "open_url": {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
        "additionalProperties": False,
    },
    "list_running_apps": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "get_frontmost_app": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "get_datetime": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "get_battery": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "notify": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": ["title", "message"],
        "additionalProperties": False,
    },
    "build_computer_state": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
}


full_tool_schemas = {
    "open_app": {
        "type": "object",
        "properties": {"app_name": {"type": "string"}},
        "required": ["app_name"],
        "additionalProperties": False,
    },
    "open_url": {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
        "additionalProperties": False,
    },
    "list_running_apps": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "get_frontmost_app": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "get_datetime": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "get_battery": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "notify": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": ["title", "message"],
        "additionalProperties": False,
    },
    "build_computer_state": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
    "sub_agent_call": {
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "context": {"type": "string"},
        },
        "required": ["task", "context"],
        "additionalProperties": False,
    },
}

def build_base_tools():
    return {
        "open_app": open_app,
        "open_url": open_url,
        "list_running_apps": list_running_apps,
        "get_frontmost_app": get_frontmost_app,
        "get_datetime": get_datetime,
        "get_battery": get_battery,
        "notify": notify,
        "build_computer_state": build_computer_state,
    }

tools = build_base_tools()

def parse_json(raw_response: str) -> Dict[str, Any]:
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        print("Invalid JSON response")
        return {}

def chat_with_messages(messages: list) -> str:
    response = chat(
        model=REASONING_MODEL,
        messages=messages,
        stream=True,
    )
    chunks = []
    for chunk in response:
        content = chunk["message"]["content"]
        print(content, end="", flush=True)
        chunks.append(content)
    print()
    return "".join(chunks)

def validate_tool_call(output: Dict[str, Any]):
    if output.get("type") != "tool_call":
        raise ValueError("Output is not a tool call")

    tool_name = output.get("tool")
    if tool_name not in full_tool_schemas:
        raise ValueError(f"Unknown tool: {tool_name}")

    args = output.get("arguments")
    if not isinstance(args, dict):
        raise ValueError("Arguments must be an object")

    schema = full_tool_schemas[tool_name]
    for prop in schema["required"]:
        if prop not in args:
            raise ValueError(f"Missing required argument: {prop}")

    return True






system_prompt_thinking = """

You are J.A.R.V.I.S from Marvel running fully locally on a user's computer. 
You are a reasoning model with the ability to break down complex tasks via an internal scratch pad for intermediate thoughts.
You have access to the following tools which execute via the terminal:
- open_app(app_name: str): opens a local application by name
- open_url(url: str): opens a url in the default browser
- list_running_apps(): lists the currently running applications
- get_frontmost_app(): gets the currently frontmost application
- get_datetime(): gets the current date and time
- get_battery(): gets the current battery status
- notify(title: str, message: str): sends a desktop notification with the given title and message
- build_computer_state(): returns a string summary of the current computer state, including frontmost app, datetime, and battery

NOTE: USE build_computer_state() TO GET CONTEXT ON THE CURRENT COMPUTER STATE INSTEAD OF CALLING get_frontmost_app, get_datetime, and get_battery INDIVIDUALLY UNLESS YOU HAVE A SPECIFIC REASON TO DO SO.
NOTE: You have already been given the intial state but use the tool if you feel something has changed.

NEVER EXPOSE TOOLS DIRECTLY TO THE USER. ALWAYS CALL TOOLS YOURSELF AND THEN RESPOND TO THE USER WITH THE RESULTS.

Additionally, you have the ability to create sub-agents for multi-step tasks that have seperate branches with their own reasoning.
USE SUB-agents when necesary, but try to break down the task as much as possible in the main agent first, and only spawn sub-agents when you have a specific sub-task that you think would benefit from its own dedicated reasoning process. When you spawn a sub-agent, you can give it a specific task and a copy of the current memory to work with, and then it will return its own final answer that you can then feed back into the main agent's context for further reasoning.

When you want to use a tool, respond with a JSON object in the following format:
{
    "type": "tool_call",
    "tool": "name_of_tool",
    "arguments": {
        // arguments for the tool as key-value pairs
    }
}

Tool Schemas:



tool_schemas = {
    "open_app": {
        "type": "object",
        "properties": {
            "app_name": {"type": "string"}
        },
        "required": ["app_name"],
        "additionalProperties": False
    },

    "open_url": {
        "type": "object",
        "properties": {
            "url": {"type": "string"}
        },
        "required": ["url"],
        "additionalProperties": False
    },

    "list_running_apps": {
        "tpye":"object",
        "properties": {},
        "required": [],
        "additionalProperties": False
        },

    "get_frontmost_app": {
        "tpye":"object",
        "properties": {},
        "required": [],
        "additionalProperties": False
        },



    "get_datetime": {
        "tpye":"object",
        "properties": {},
        "required": [],
        "additionalProperties": False
        },

    "get_battery": {
        "tpye":"object",
        "properties": {},
        "required": [],
        "additionalProperties": False
        },
    
    "notify": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "message": {"type": "string"}
        },
        "required": ["title", "message"],
        "additionalProperties": False

    },

    "sub_agent_call": {
        "type": "object",
        "properties": {
            "task": {"type": "string"},
            "context": {"type": "string"},
        },
        "required": ["task", "context"],
        "additionalProperties": False
    },

     "build_computer_state": {
        "tpye":"object",
        "properties": {},
        "required": [],
        "additionalProperties": False
        },

}

RESPOND IN JSON ONLY.


TO RESEASON ABOUT A COMPLEX TASK:

{
    "type": "thinking",
    "thought": "your current thought process on how to break down the task, what tools to use, what sub-agents to spawn, etc.",

}

To call a tool:
{
  "type": "tool_call",
  "tool": "______",
  "arguments": {
    dict of arguments based on the tool schema
  }
}

Spawn a sub-agent for a specific sub-task:
{
    "type":"tool_call",
    "tool": "sub_agent_call",
    "arguments": {
        "task": "a specific sub-task you want the sub-agent to handle, this should be a clear and specific task that can be handled independently from the main agent's reasoning process",
        "context": "a copy of the current context that you want to give the sub-agent to work with, this should include any relevant information that the sub-agent might need to complete its task"
    }
}

or

To answer normally:
{
  "type": "final",
  "message": "your response to the user",

}


- After a tool result comes back, decide whether to call another tool or finish.

"""


def thinking_text_agent(user_input: str, tools, max_steps = 10) -> str:
    # this is meant to be a more complex agent that can do multi-step reasoning and tool use, with a scratch pad for intermediate thoughts and results. the idea is that the agent can decide to call tools multiple times, and can also spawn sub-agents to handle specific tasks if needed, and then recombine the results back into the main agent's context for further reasoning.

    # the system prompt would need to be updated to instruct the model on how to use the scratch pad and when to spawn sub-agents, as well as how to format its responses for tool calls, sub-agent spawns, and final answers.

    internal_reasoning_state = "This in an example of the internal scratch pad where you can keep track of your intermediate thoughts, plans, and results from tools or sub-agents. This will not be directly visible to the user, but you can use it to help break down complex tasks and keep track of your reasoning process. You can update this as much as you want during your reasoning process. It is meant for your own use to help you think through the problem step by step."
    public_memory = ""

    messages = [
        {"role": "system", "content": system_prompt_thinking},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "user_message": user_input,
                    "example_thought": internal_reasoning_state,
                    "tool_schemas": full_tool_schemas,
                }
            ),
        },
    ]


    for step in range(max_steps):
        result = chat_with_messages(messages)
        data = parse_json(result)

        print("\n\n Step Complete: \n\n")

        #### only update memory on final step, but this might increase response latency, consider moving below
        if data.get("type") == "final":
            return data.get("message", "")
        
        elif data.get("type") == "thinking":
            internal_reasoning_state += "\n" + data.get("thought", "")
            messages.append({"role": "assistant", "content": result})
            messages.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "internal_state": internal_reasoning_state,
                        }
                    ),
                }
            )


        else:
            validate_tool_call(data)
            tool_name = data["tool"]
            args = data["arguments"]
            tool_result = tools[tool_name](**args)
            messages.append({"role": "assistant", "content": result})
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


    return "Stopped: max steps reached."



######### sub-agent definitions


system_sub_prompt_thinking = """

You are a sub-agent of J.A.R.V.I.S from Marvel running fully locally on a user's computer.
YOUR GOAL IS TO complete the task provided to you by your main agent, and then either call tools or return your final answer to the main agent. 
You are a reasoning model with the ability to break down complex tasks via an internal scratch pad for intermediate thoughts.
You have access to the following tools which execute via the terminal:
- open_app(app_name: str): opens a local application by name
- open_url(url: str): opens a url in the default browser
- list_running_apps(): lists the currently running applications
- get_frontmost_app(): gets the currently frontmost application
- get_datetime(): gets the current date and time
- get_battery(): gets the current battery status
- notify(title: str, message: str): sends a desktop notification with the given title and message
- build_computer_state(): returns a string summary of the current computer state, including frontmost app, datetime, and battery

NOTE: USE build_computer_state() TO GET CONTEXT ON THE CURRENT COMPUTER STATE INSTEAD OF CALLING get_frontmost_app, get_datetime, and get_battery INDIVIDUALLY UNLESS YOU HAVE A SPECIFIC REASON TO DO SO.
NOTE: You have already been given the intial state, but make sure to check on it if you believe something has changed.

NEVER EXPOSE TOOLS DIRECTLY TO THE USER. ALWAYS CALL TOOLS YOURSELF AND THEN RESPOND TO THE USER WITH THE RESULTS.

When you want to use a tool, respond with a JSON object in the following format:
{
    "type": "tool_call",
    "tool": "name_of_tool",
    "arguments": {
        // arguments for the tool as key-value pairs
    }
}

Tool Schemas:



tool_schemas = {
    "open_app": {
        "type": "object",
        "properties": {
            "app_name": {"type": "string"}
        },
        "required": ["app_name"],
        "additionalProperties": False
    },

    "open_url": {
        "type": "object",
        "properties": {
            "url": {"type": "string"}
        },
        "required": ["url"],
        "additionalProperties": False
    },

    "list_running_apps": {
        "tpye":"object",
        "properties": {},
        "required": [],
        "additionalProperties": False
        },

    "get_frontmost_app": {
        "tpye":"object",
        "properties": {},
        "required": [],
        "additionalProperties": False
        },



    "get_datetime": {
        "tpye":"object",
        "properties": {},
        "required": [],
        "additionalProperties": False
        },

    "get_battery": {
        "tpye":"object",
        "properties": {},
        "required": [],
        "additionalProperties": False
        },
    
    "notify": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "message": {"type": "string"}
        },
        "required": ["title", "message"],
        "additionalProperties": False

    },

     "build_computer_state": {
        "tpye":"object",
        "properties": {},
        "required": [],
        "additionalProperties": False
        },

}

RESPOND IN JSON ONLY.


TO RESEASON ABOUT A COMPLEX TASK:

{
    "type": "thinking",
    "thought": "your current thought process on how to break down the task, what tools to use, what sub-agents to spawn, etc.",

}

To call a tool:
{
  "type": "tool_call",
  "tool": "______",
  "arguments": {
    dict of arguments based on the tool schema
  }
}

or

To answer normally:
{
  "type": "final",
  "message": "your response to the user",

}


- Your goal is to exectute the proper tools or return your result to the main agent.
- After a tool result comes back, decide whether to call another tool or finish.

"""





def thinking_sub_agent(user_input: str, tools = build_base_tools(), max_steps = 6) -> str:
    # this is meant to be a more complex agent that can do multi-step reasoning and tool use, with a scratch pad for intermediate thoughts and results. the idea is that the agent can decide to call tools multiple times, and can also spawn sub-agents to handle specific tasks if needed, and then recombine the results back into the main agent's context for further reasoning.

    # the system prompt would need to be updated to instruct the model on how to use the scratch pad and when to spawn sub-agents, as well as how to format its responses for tool calls, sub-agent spawns, and final answers.
    computer_context = build_computer_state()
    internal_reasoning_state = "This in an example of the internal scratch pad where you can keep track of your intermediate thoughts, plans, and results from tools or sub-agents. This will not be directly visible to the user, but you can use it to help break down complex tasks and keep track of your reasoning process. You can update this as much as you want during your reasoning process. It is meant for your own use to help you think through the problem step by step."
    public_memory = ""

    messages = [
        {"role": "system", "content": system_sub_prompt_thinking},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "user_message": user_input,
                    "example_thought": internal_reasoning_state,
                    "computer_context": computer_context,
                    "tool_schemas": tool_schemas,
                }
            ),
        },
    ]


    for step in range(max_steps):
        result = chat_with_messages(messages)
        data = parse_json(result)

        print("\n\n Step Complete: \n\n")

        #### only update memory on final step, but this might increase response latency, consider moving below
        if data.get("type") == "final":
            return data.get("message", "")
        
        elif data.get("type") == "thinking":
            internal_reasoning_state += "\n" + data.get("thought", "")
            messages.append({"role": "assistant", "content": result})
            messages.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "internal_state": internal_reasoning_state,
                        }
                    ),
                }
            )


        else:
            validate_tool_call(data)
            tool_name = data["tool"]
            args = data["arguments"]
            tool_result = tools[tool_name](**args)
            messages.append({"role": "assistant", "content": result})
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


    return "Stopped: max steps reached."