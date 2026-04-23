import socket
import threading
import json
import sys

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5000

SEPARATOR = "-" * 50


def send_json(sock, data):
    message = json.dumps(data, ensure_ascii=False) + "\n"
    sock.sendall(message.encode("utf-8"))


def print_separator():
    print(f"\n{SEPARATOR}")


def print_channels(channels):
    if not channels:
        print("No channels available.")
        return

    for i, ch in enumerate(channels, start=1):
        print(
            f"{i}. {ch['name']} | {ch['description']} | owner={ch['owner']} | subscribers={ch['subscriber_count']}"
        )


def receiver(sock):
    file = sock.makefile("r", encoding="utf-8")
    try:
        while True:
            line = file.readline()
            if not line:
                print_separator()
                print("[INFO] Disconnected from server.")
                print(SEPARATOR)
                break

            data = json.loads(line.strip())
            msg_type = data.get("type")

            print_separator()

            if msg_type == "welcome":
                print(f"[WELCOME] {data.get('message')}")
                print("Channels available:")
                print_channels(data.get("channels", []))

            elif msg_type == "list_response":
                print("[CHANNEL LIST]")
                print_channels(data.get("channels", []))

            elif msg_type == "notification":
                print(f"[NOTIFICATION] {data.get('message')}")

            elif msg_type == "news":
                print("[NEWS]")
                print(f"Channel : {data.get('channel_name')}")
                print(f"From    : {data.get('from')}")
                print(f"Content : {data.get('content')}")

            elif msg_type == "success":
                print(f"[SUCCESS] {data.get('message')}")

            elif msg_type == "error":
                print(f"[ERROR] {data.get('message')}")

            else:
                print(f"[SERVER MESSAGE] {data}")

            print(SEPARATOR)

    except Exception as e:
        print_separator()
        print(f"[ERROR] Receiver thread stopped: {e}")
        print(SEPARATOR)


def print_help():
    print("""
Available commands:
  list
  create <channel_name> <description>
  delete <channel_name>
  subscribe <channel_name>
  unsubscribe <channel_name>
  publish <channel_name> <message>
  help
  exit

Examples:
  create sport Daily sports news
  subscribe sport
  publish sport Real Madrid won 2-0
""")


def main():
    global SERVER_HOST, SERVER_PORT

    if len(sys.argv) >= 2:
        SERVER_HOST = sys.argv[1]
    if len(sys.argv) >= 3:
        SERVER_PORT = int(sys.argv[2])

    print(SEPARATOR)
    print("News Channel Client")
    print(SEPARATOR)

    username = input("Enter username: ").strip()
    if not username:
        print("Username cannot be empty.")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER_HOST, SERVER_PORT))

    send_json(sock, {
        "type": "hello",
        "username": username
    })

    t = threading.Thread(target=receiver, args=(sock,), daemon=True)
    t.start()

    print_help()

    try:
        while True:
            command = input("\n> ").strip()
            if not command:
                continue

            if command == "help":
                print_help()
                continue

            if command == "exit":
                print("Closing client...")
                break

            if command == "list":
                send_json(sock, {"type": "list"})
                continue

            parts = command.split()

            if parts[0] == "create":
                if len(parts) < 3:
                    print("Usage: create <channel_name> <description>")
                    continue

                channel_name = parts[1]
                description = " ".join(parts[2:])

                send_json(sock, {
                    "type": "create_channel",
                    "channel_name": channel_name,
                    "description": description
                })
                continue

            if parts[0] == "delete":
                if len(parts) != 2:
                    print("Usage: delete <channel_name>")
                    continue

                send_json(sock, {
                    "type": "delete_channel",
                    "channel_name": parts[1]
                })
                continue

            if parts[0] == "subscribe":
                if len(parts) != 2:
                    print("Usage: subscribe <channel_name>")
                    continue

                send_json(sock, {
                    "type": "subscribe",
                    "channel_name": parts[1]
                })
                continue

            if parts[0] == "unsubscribe":
                if len(parts) != 2:
                    print("Usage: unsubscribe <channel_name>")
                    continue

                send_json(sock, {
                    "type": "unsubscribe",
                    "channel_name": parts[1]
                })
                continue

            if parts[0] == "publish":
                if len(parts) < 3:
                    print("Usage: publish <channel_name> <message>")
                    continue

                channel_name = parts[1]
                content = " ".join(parts[2:])

                send_json(sock, {
                    "type": "publish_news",
                    "channel_name": channel_name,
                    "content": content
                })
                continue

            print("Unknown command. Type 'help'.")

    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        try:
            sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()