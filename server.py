import socket
import threading
import time

SERVER_ADDRESS = '127.0.0.1'
SERVER_PORT = 5378
Fsymbols = " !@#$%^,"

MAX_USERS = 16

users = {}
lock = threading.Lock()
message_queue = {}


def handle_client(client_socket):
    while True:
        try:
            data = client_socket.recv(2048).decode()
            if not data:
                break
            message_parts = data.split(" ")
            command = message_parts[0]

            if command == "HELLO-FROM":
                handle_login(client_socket, data)
            elif command == "LIST":
                handle_list(client_socket)
            elif command == "SEND":
                handle_send(client_socket, message_parts)
            else:
                send_message(client_socket, "BAD-RQST-HDR")
        except Exception as e:
            print(f"Error: {e}")
            break

    client_socket.close()


def handle_login(client_socket, data):
    global users
    data = data.split()
    username = " ".join(data[1:])
    with lock:
        if len(users) >= MAX_USERS:
            send_message(client_socket, "BUSY")
            return

        if username in users:
            send_message(client_socket, "IN-USE")
            return

        for character in username:
            if character in Fsymbols:
                send_message(client_socket, "BAD-RQST-BODY")
                return
        users[username] = client_socket
        send_message(client_socket, "HELLO")
        if username in message_queue:
            queued_messages = message_queue.pop(username)
            for msg in queued_messages:
                send_message(client_socket, msg)


def handle_list(client_socket):
    print("list")
    global users
    user_list = ",".join(users.keys())
    send_message(client_socket, f"LIST-OK {user_list}")


def handle_send(client_socket, message_parts):
    global users, message_queue

    sender = message_parts[1]
    sender_characters = list(sender)

    all_characters_in_users = all(any(char in user for user in users) for char in sender_characters)

    recipient = message_parts[2]
    message = " ".join(message_parts[3:])

    with lock:
        if recipient in users:
            send_message(users[recipient], f"DELIVERY {sender} {message}")
            send_message(client_socket, "SEND-OK")

        if message_parts[2].strip() == "":
            send_message(client_socket, "BAD-RQST-BODY")
            return
        if recipient not in users:
            send_message(client_socket, "BAD-RQST-HDR")
            return
        if not all_characters_in_users:
            send_message(client_socket, "BAD-DEST-USER")
            return


def send_message(client_socket, message):

    total_sent = 0
    while total_sent < len(message):
        try:
            sent = client_socket.send(f"{message}\n".encode())
            if sent == 0:
                raise RuntimeError("Invalid")
            total_sent += sent
        except BlockingIOError:
            time.sleep(1)


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_ADDRESS, SERVER_PORT))
    server_socket.listen()

    print("Server is on")
    try:
        while True:
            client_socket, _ = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket,))
            client_thread.start()
    except KeyboardInterrupt:
        print("Server shutting down")
    finally:
        server_socket.close()


if __name__ == "__main__":
    start_server()
