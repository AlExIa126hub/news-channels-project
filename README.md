# News Channels Subscription System (Client-Server Application)

## Overview

This project implements a distributed **client-server application** for managing news channels and subscriptions.  
The system allows multiple clients to connect to a central server, create and manage news channels, subscribe to them, and receive real-time news updates.

The application is built using **TCP sockets** and a simple **JSON-based communication protocol**, with a **multi-threaded server** capable of handling multiple clients concurrently.

---

## Features

### Core Functionality

- Client-server communication over TCP sockets
- Concurrent server (multi-threaded)
- Channel management:
  - Create channel (unique name required)
  - Delete channel (only by owner)
- Subscription system:
  - Subscribe to channels
  - Unsubscribe from channels
- News publishing:
  - Only the channel owner can publish news
  - News is delivered only to subscribed clients

---

### Real-Time Notifications

Clients receive notifications when:

- A new channel is created
- A channel is deleted
- A new client connects

---

### Content Filtering

The server maintains a list of **forbidden words** loaded from a configuration file.

- If a news message contains any forbidden word:
  - The message is **blocked**
  - It is **NOT delivered** to subscribers

Filtering is **case-insensitive**.

---

### Disconnection Handling

When a client disconnects:

- The client is removed from all subscriptions
- All channels owned by that client are deleted
- Other connected clients are notified

---

## Technologies Used

- Python 3
- TCP Sockets
- Multithreading (`threading`)
- JSON (communication protocol)
- Docker (for server deployment)

---

## Project Architecture

### Server

The server is responsible for:

- Managing:
  - channels (name, description, owner)
  - subscriptions (channel → subscribers)
  - forbidden words
- Handling multiple clients concurrently
- Broadcasting notifications and news updates
- Filtering content before delivery
- Handling client disconnections

---

### Client

The client:

- Connects to the server via TCP
- Sends commands in JSON format
- Receives:
  - server responses
  - notifications
  - news updates

---

## Communication Protocol

The application uses a **JSON-based protocol** over TCP.  
Each message is a JSON object followed by a newline (`\n`).

---

### Client → Server Examples

```json
{"type":"hello","username":"wonder_geek"}
```

```json
{"type":"list"}
```

```json
{"type":"create_channel","channel_name":"sport","description":"Daily sports news"}
```

```json
{"type":"subscribe","channel_name":"sport"}
```

```json
{"type":"publish_news","channel_name":"sport","content":"Match ended 2-0"}
```

---

### Server → Client Examples

```json
{"type":"notification","message":"New channel created"}
```

```json
{"type":"news","channel_name":"sport","from":"wonder_geek","content":"Match ended 2-0"}
```

```json
{"type":"success","message":"Subscribed successfully"}
```

```json
{"type":"error","message":"Channel already exists"}
```

---

## Setup and Installation

### Requirements

- Python 3.x
- Docker + Docker Compose

---

### Running the Server (Docker)

```bash
docker compose up --build
```

The server will start on:

```
127.0.0.1:5000
```

---

### Running Clients

Open **two separate terminals**:

```bash
python client.py 127.0.0.1 5000
```

or on Windows:

```bash
py client.py 127.0.0.1 5000
```

---

## Available Client Commands

```
list
create <channel_name> <description>
delete <channel_name>
subscribe <channel_name>
unsubscribe <channel_name>
publish <channel_name> <message>
help
exit
```

---

## Example Usage Scenario

### 1. Start server

```bash
docker compose up --build
```

---

### 2. Connect two clients

Client 1:
```
alexia
```

Client 2:
```
maria
```

---

### 3. Create a channel

Client 1:
```
create sport Daily sports news
```

Client 2 receives a notification.

---

### 4. Subscribe to channel

Client 2:
```
subscribe sport
```

---

### 5. Publish allowed news

Client 1:
```
publish sport Team won the match
```

Client 2 receives the news.

---

### 6. Publish blocked news

Client 1:
```
publish sport This contains bomb information
```

Result:
- Message is blocked
- Subscribers receive nothing

---

### 7. Unsubscribe

Client 2:
```
unsubscribe sport
```

---

### 8. Delete channel

Client 1:
```
delete sport
```

All clients receive a notification.

---

## Data Storage

The application uses **in-memory storage** for:

- Channels
- Subscriptions
- Connected users

### Important

- Data is **NOT persistent**
- Restarting the server resets all data

This is an intentional design choice and is acceptable since persistence is not required.

---

## Concurrency

The server is **multi-threaded**:

- Each client connection is handled in a separate thread
- Shared data structures are protected using synchronization mechanisms (locks)

---

## Error Handling

The system handles:

- Duplicate usernames
- Duplicate channel names
- Invalid commands
- Unauthorized actions (non-owner operations)
- Invalid JSON messages
- Subscription errors (duplicate or missing subscriptions)
- Client disconnections

---

## Design Decisions

### Channel Ownership

- Only the creator (owner) of a channel can:
  - publish news
  - delete the channel

---

### Disconnect Behavior

When a client disconnects:

- All subscriptions are removed
- Channels owned by the client are deleted
- Other clients are notified

---

### Content Filtering

- Forbidden words are stored in `banned_words.txt`
- Filtering is case-insensitive
- Blocked messages are not delivered to subscribers

---

## Possible Improvements

- Persistent storage (database or file-based)
- Authentication and user accounts
- Graphical user interface (GUI)
- Message history per channel
- Advanced filtering (regex, NLP)

---

## Conclusion

This project demonstrates:

- Client-server architecture
- Concurrent programming
- Network communication using TCP sockets
- Real-time message distribution
- Basic content moderation

It provides a solid foundation for building more complex distributed systems.
