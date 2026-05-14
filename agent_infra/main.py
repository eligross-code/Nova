from agents import AgentRuntime, Model


def main():
    model = Model(level="local")
    runtime = AgentRuntime(model=model, max_steps=10)

    print("NOVA terminal runtime. Type 'exit' or 'quit' to stop.")

    while True:
        try:
            user_message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_message:
            continue

        if user_message.lower() in {"exit", "quit"}:
            break

        response = runtime.loop(user_message)
        print(f"NOVA: {response}")


if __name__ == "__main__":
    main()
