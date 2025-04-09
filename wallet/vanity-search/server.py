'''
This server manages clients looking for pi vanity wallet suffixes

Inputs:
1. suffix required to search - the longer the suffix the exponentially longer the search will likely be

ouputs:
1.a running count of search attempts - [ip of client] Total attempts: <number>
2.Public address and passphrase found. Server exits.

Notes:
1. The server runs on all network interfaces
2. These are the only valid characters: ABCDEFGHIJKLMNOPQRSTUVWXYZ234567
3. can control+c to exit the server before the clients are connected or during the process. 
'''


import socket
import threading

HOST = '0.0.0.0'
PORT = 65432
found = False
total_attempts = 0
lock = threading.Lock()

def handle_client(conn, addr, suffix):
    global found, total_attempts
    ip = addr[0]
    thread_name = threading.current_thread().name
    try:
        conn.sendall(suffix.encode())
        while not found:
            try:
                data = conn.recv(4096).decode()
                if not data:
                    break
                if "attempts made" in data:
                    try:
                        count = int(data.split()[1])
                        with lock:
                            total_attempts += count
                            print(f"[{ip}] Total attempts: {total_attempts}")
                    except (ValueError, IndexError):
                        print(f"[{ip}] [{thread_name}] Could not parse attempt count.")
                else:
                    print(f"[{ip}] [{thread_name}] {data}")

                if data.startswith("✅ MATCH FOUND"):
                    found = True
            except socket.timeout:
                break
            except (ConnectionResetError, ConnectionAbortedError):
                break
    except Exception as e:
        print(f"[ERROR] {ip}: {e}")
    finally:
        conn.close()

def main():
    suffix = input("Enter suffix to search for: ").strip().upper()
    print(f"Waiting for clients... Searching for address ending in '{suffix}'")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()

        while not found:
            try:
                conn, addr = s.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr, suffix))
                thread.start()
            except KeyboardInterrupt:
                print("Shutting down server.")
                break

if __name__ == '__main__':
    main()
