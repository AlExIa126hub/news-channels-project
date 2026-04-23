import socket
import threading
import json
from dataclasses import dataclass, field

HOST = "0.0.0.0"
PORT = 5000
BANNED_WORDS_FILE = "banned_words.txt"


@dataclass
class ClientInfo:
    sock: socket.socket
    username: str
    address: tuple
    subscriptions: set = field(default_factory=set)


@dataclass
class ChannelInfo:
    name: str
    description: str
    owner: str
    subscribers: set = field(default_factory=set)


clients = {}           # sock -> ClientInfo
channels = {}          # channel_name -> ChannelInfo
username_to_sock = {}  # username -> sock
lock = threading.Lock()


def load_banned_words():
    words = set()
    try:
        with open(BANNED_WORDS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().lower()
                if word:
                    words.add(word)
    except FileNotFoundError:
        print(f"[WARN] {BANNED_WORDS_FILE} not found. No banned words loaded.")
    return words


BANNED_WORDS = load_banned_words()


def send_json(sock, data):
    try:
        message = json.dumps(data, ensure_ascii=False) + "\n"
        sock.sendall(message.encode("utf-8"))
        return True
    except Exception:
        return False


def broadcast(data, exclude_sock=None):
    dead_sockets = []
    with lock:
        all_sockets = list(clients.keys())

    for sock in all_sockets:
        if sock == exclude_sock:
            continue
        ok = send_json(sock, data)
        if not ok:
            dead_sockets.append(sock)

    for sock in dead_sockets:
        cleanup_client(sock)


def contains_banned_word(text):
    text_lower = text.lower()
    for word in BANNED_WORDS:
        if word in text_lower:
            return True, word
    return False, None


def get_channel_list():
    result = []
    with lock:
        for ch in channels.values():
            result.append({
                "name": ch.name,
                "description": ch.description,
                "owner": ch.owner,
                "subscriber_count": len(ch.subscribers)
            })
    return result


def cleanup_client(sock):
    with lock:
        if sock not in clients:
            return

        client = clients[sock]
        username = client.username

        # remove client from subscriptions
        for ch_name in list(client.subscriptions):
            if ch_name in channels:
                channels[ch_name].subscribers.discard(username)

        # delete channels owned by this user
        owned_channels = [ch_name for ch_name, ch in channels.items() if ch.owner == username]
        for ch_name in owned_channels:
            del channels[ch_name]

        # remove client
        del clients[sock]
        if username in username_to_sock:
            del username_to_sock[username]

    try:
        sock.close()
    except Exception:
        pass

    for ch_name in owned_channels:
        broadcast({
            "type": "notification",
            "message": f"Channel '{ch_name}' was deleted because owner '{username}' disconnected."
        })

    print(f"[DISCONNECT] {username}")


def handle_list(sock):
    send_json(sock, {
        "type": "list_response",
        "channels": get_channel_list()
    })


def handle_create(sock, data):
    name = data.get("channel_name", "").strip()
    description = data.get("description", "").strip()

    if not name or not description:
        send_json(sock, {"type": "error", "message": "Channel name and description are required."})
        return

    with lock:
        client = clients[sock]

        if name in channels:
            send_json(sock, {"type": "error", "message": f"Channel '{name}' already exists."})
            return

        channels[name] = ChannelInfo(name=name, description=description, owner=client.username)

    send_json(sock, {"type": "success", "message": f"Channel '{name}' created successfully."})

    broadcast({
        "type": "notification",
        "message": f"New channel created: '{name}' by '{client.username}'. Description: {description}"
    }, exclude_sock=None)


def handle_delete(sock, data):
    name = data.get("channel_name", "").strip()

    if not name:
        send_json(sock, {"type": "error", "message": "Channel name is required."})
        return

    with lock:
        client = clients[sock]

        if name not in channels:
            send_json(sock, {"type": "error", "message": f"Channel '{name}' does not exist."})
            return

        channel = channels[name]
        if channel.owner != client.username:
            send_json(sock, {"type": "error", "message": "Only the owner can delete this channel."})
            return

        # remove subscriptions from clients
        for username in list(channel.subscribers):
            sub_sock = username_to_sock.get(username)
            if sub_sock and sub_sock in clients:
                clients[sub_sock].subscriptions.discard(name)

        del channels[name]

    send_json(sock, {"type": "success", "message": f"Channel '{name}' deleted successfully."})

    broadcast({
        "type": "notification",
        "message": f"Channel '{name}' was deleted by '{client.username}'."
    }, exclude_sock=None)


def handle_subscribe(sock, data):
    name = data.get("channel_name", "").strip()

    if not name:
        send_json(sock, {"type": "error", "message": "Channel name is required."})
        return

    with lock:
        client = clients[sock]

        if name not in channels:
            send_json(sock, {"type": "error", "message": f"Channel '{name}' does not exist."})
            return

        channel = channels[name]

        if client.username in channel.subscribers:
            send_json(sock, {"type": "error", "message": f"You are already subscribed to '{name}'."})
            return

        channel.subscribers.add(client.username)
        client.subscriptions.add(name)

    send_json(sock, {"type": "success", "message": f"Subscribed to '{name}' successfully."})


def handle_unsubscribe(sock, data):
    name = data.get("channel_name", "").strip()

    if not name:
        send_json(sock, {"type": "error", "message": "Channel name is required."})
        return

    with lock:
        client = clients[sock]

        if name not in channels:
            send_json(sock, {"type": "error", "message": f"Channel '{name}' does not exist."})
            return

        channel = channels[name]

        if client.username not in channel.subscribers:
            send_json(sock, {"type": "error", "message": f"You are not subscribed to '{name}'."})
            return

        channel.subscribers.discard(client.username)
        client.subscriptions.discard(name)

    send_json(sock, {"type": "success", "message": f"Unsubscribed from '{name}' successfully."})


def handle_publish(sock, data):
    name = data.get("channel_name", "").strip()
    content = data.get("content", "").strip()

    if not name or not content:
        send_json(sock, {"type": "error", "message": "Channel name and content are required."})
        return

    with lock:
        client = clients[sock]

        if name not in channels:
            send_json(sock, {"type": "error", "message": f"Channel '{name}' does not exist."})
            return

        channel = channels[name]

        if channel.owner != client.username:
            send_json(sock, {"type": "error", "message": "Only the owner can publish on this channel."})
            return

    blocked, bad_word = contains_banned_word(content)
    if blocked:
        send_json(sock, {
            "type": "success",
            "message": f"News blocked by filter. Forbidden word detected: '{bad_word}'."
        })
        print(f"[FILTER BLOCKED] Channel={name}, Owner={client.username}, Word={bad_word}, Content={content}")
        return

    with lock:
        recipients = []
        for username in channel.subscribers:
            sub_sock = username_to_sock.get(username)
            if sub_sock and sub_sock in clients:
                recipients.append(sub_sock)

    for rsock in recipients:
        send_json(rsock, {
            "type": "news",
            "channel_name": name,
            "from": client.username,
            "content": content
        })

    send_json(sock, {
        "type": "success",
        "message": f"News sent to {len(recipients)} subscriber(s)."
    })


def handle_client(sock, addr):
    file = sock.makefile("r", encoding="utf-8")

    try:
        hello_line = file.readline()
        if not hello_line:
            sock.close()
            return

        try:
            hello = json.loads(hello_line.strip())
        except json.JSONDecodeError:
            send_json(sock, {"type": "error", "message": "Invalid JSON."})
            sock.close()
            return

        if hello.get("type") != "hello":
            send_json(sock, {"type": "error", "message": "First message must be of type 'hello'."})
            sock.close()
            return

        username = hello.get("username", "").strip()
        if not username:
            send_json(sock, {"type": "error", "message": "Username is required."})
            sock.close()
            return

        with lock:
            if username in username_to_sock:
                send_json(sock, {"type": "error", "message": f"Username '{username}' is already connected."})
                sock.close()
                return

            clients[sock] = ClientInfo(sock=sock, username=username, address=addr)
            username_to_sock[username] = sock

        print(f"[CONNECT] {username} from {addr}")

        send_json(sock, {
            "type": "welcome",
            "message": f"Welcome, {username}!",
            "channels": get_channel_list()
        })

        broadcast({
            "type": "notification",
            "message": f"Client '{username}' connected."
        }, exclude_sock=sock)

        while True:
            line = file.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                send_json(sock, {"type": "error", "message": "Invalid JSON."})
                continue

            msg_type = data.get("type")

            if msg_type == "list":
                handle_list(sock)
            elif msg_type == "create_channel":
                handle_create(sock, data)
            elif msg_type == "delete_channel":
                handle_delete(sock, data)
            elif msg_type == "subscribe":
                handle_subscribe(sock, data)
            elif msg_type == "unsubscribe":
                handle_unsubscribe(sock, data)
            elif msg_type == "publish_news":
                handle_publish(sock, data)
            else:
                send_json(sock, {"type": "error", "message": f"Unknown command type: {msg_type}"})

    except Exception as e:
        print(f"[ERROR] Client handler exception: {e}")
    finally:
        cleanup_client(sock)


def main():
    print(f"[START] Server running on {HOST}:{PORT}")
    print(f"[INFO] Forbidden words: {sorted(BANNED_WORDS)}")

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen()

    while True:
        client_sock, addr = server_sock.accept()
        t = threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True)
        t.start()


if __name__ == "__main__":
    main()