from core.core_manager import CoreManager

def main():
    core = CoreManager()
    print("AI Co-Partner is running. Type something. Type 'exit' to quit.")

    while True:
        text = input("> ").strip()
        if text.lower() == "exit":
            print("Goodbye.")
            break

        reply = core.handle_input(text)
        print(reply)

if __name__ == "__main__":
    main()
