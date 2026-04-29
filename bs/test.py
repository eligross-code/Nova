from ollama import chat

response = chat(
    model="llama3.1:8b",
    messages=[
        {'role': 'system', 'content': "You are a helpful assistant."},
        {'role': 'user', 'content': "What is the weather today?"}
    ],
)

print(response['message']['content'])