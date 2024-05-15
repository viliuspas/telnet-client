import socket
import threading
import time
import sys
import json
import string

control_chars = {
    "^@": "\0",  # Null character
    "^A": "\1",  # Start of heading
    "^B": "\2",  # Start of text
    "^C": "\3",  # End of text
    "^D": "\4",  # End of transmission
    "^E": "\5",  # Enquiry
    "^F": "\6",  # Acknowledge
    "^G": "\a",  # Audible bell
    "^H": "\b",  # Backspace
    "^I": "\t",  # Horizontal tab
    "^J": "\n",  # Line feed
    "^K": "\v",  # Vertical tab
    "^L": "\f",  # Form feed
    "^M": "\r",  # Carriage return
    "^N": "\x0e",  # Shift out
    "^O": "\x0f",  # Shift in
    "^P": "\x10",  # Data link escape
    "^Q": "\x11",  # Device control 1
    "^R": "\x12",  # Device control 2
    "^S": "\x13",  # Device control 3
    "^T": "\x14",  # Device control 4
    "^U": "\x15",  # Negative Acknowledge
    "^V": "\x16",  # Synchronous idle
    "^W": "\x17",  # End of transmission block
    "^X": "\x18",  # Cancel
    "^Y": "\x19",  # End of medium
    "^Z": "\x1a",  # Substitute
    "^[": "\x1b",  # Escape
    "^\\": "\x1c",  # File separator
    "^]": "\x1d",  # Group separator
    "^^": "\x1e",  # Record separator
    "^-": "\x1f",  # Unit separator
}

class TelnetClient:
    def __init__(self):
        self.connection_active = False
        self.paused_transmission = False
        self.cached_message = ''
        self.current_host = ''
        self.sock = None
        self.receive_thread = None
        self.send_thread = None
        self.escape_character = '\x1d'
        self.connections_cache = {}
        self.message_cache = {}
        self.load_connections_cache()

    def load_connections_cache(self):
        try:
            with open("cache.json", "r") as f:
                data = json.load(f)
                self.connections_cache = data.get("connections_cache", {})
                self.message_cache = data.get("message_cache", {})
        except FileNotFoundError:
            self.connections_cache = {}
            self.message_cache = {}

    def save_connections_cache(self):
        data = {"connections_cache": self.connections_cache, "message_cache": self.message_cache}
        with open("cache.json", "w") as f:
            json.dump(data, f)


    def get_key(self, val):
        for key, value in control_chars.items():
            if val == value:
                return key
        return val

    def active_interface(self):
        if self.connection_active and not self.paused_transmission:
            return False
        return True

    def receive(self):
        self.sock.settimeout(1)
        while True:
            try:
                if self.paused_transmission:
                    time.sleep(1)
                    continue
                data = self.sock.recv(1024)
                if not data:
                    self.remote_end()
                print(data.decode('utf-8').strip())
            except socket.timeout:
                continue
            except OSError:
                self.connection_active = False
                break
    
    def send(self):
        while True:
            if self.cached_message != '':
                self.paused_transmission = False

            if self.paused_transmission:
                time.sleep(1)
                continue
            
            if self.cached_message == '':
                message = input()
            else:
                message = self.cached_message
                self.cached_message = ''
                
            if message == self.escape_character:
                self.paused_transmission = True
            else:
                try:
                    if message != '':
                        if self.current_host in self.message_cache:
                            if message not in self.message_cache[self.current_host]:
                                self.message_cache[self.current_host].append(message)
                        else:
                            self.message_cache[self.current_host] = [message]

                    self.sock.sendall((message + '\r\n').encode('utf-8'))
                except OSError:
                    self.connection_active = False
                    break

    def connect(self, host, port):
        global control_chars
        try:
            host = socket.gethostbyname(host)
        except Exception:
            pass

        try:
            print(f'Trying {host}...')
            addrinfo = socket.getaddrinfo(host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
            for res in addrinfo:
                af, socktype, proto, canonname, sa = res
                try:
                    self.sock = socket.socket(af, socktype, proto)
                    self.sock.settimeout(3)
                    self.sock.connect(sa)
                    self.sock.setblocking(False)
                    print(f'Connected to {sa[0]}.')
                    if self.get_key(self.escape_character) in control_chars:
                        print(f'Escape character is \'{self.get_key(self.escape_character)}\'.')
                    else:
                        print(f'Escape character is \'{self.escape_character}\'.')
                    self.current_host = sa[0]
                    self.connection_active = True
                    self.receive_thread = threading.Thread(target=self.receive, daemon=True)
                    self.send_thread = threading.Thread(target=self.send, daemon=True)
                    self.receive_thread.start()
                    self.send_thread.start()
                    self.connections_cache[self.current_host] = port
                    self.save_connections_cache()
                    break
                except OSError:
                    if self.sock:
                        self.sock.close()
                    continue
            else:
                print('telnet: Unable to connect to remote host: Network is unreachable')
        except Exception:
            print(f'telnet: could not resolve {host}/{port}: Name or service not known')


    def close(self):
        if self.connection_active:
            self.paused_transmission = False
            self.sock.close()
            self.connection_active = False
            print('Connection closed.')
            self.receive_thread.join()
            self.send_thread.join()
            if self.current_host in self.connections_cache:
                self.save_connections_cache()
        else:
            print('Need to be connected first for `bye\'.')

    def remote_end(self):
        if self.connection_active:
            self.sock.close()
        print("Connection closed by foreign host.")
        sys.exit()

    def end(self):
        if self.connection_active:
            if self.connection_active:
                self.save_connections_cache()
            self.sock.close()
            print('Connection closed.')
        sys.exit()

class TelnetTerminal:
    def __init__(self, client):
        self.client = client

    def show_commands(self):
        print("close           close current connection")
        print("display         display operating parameters")
        print("open            connect to a site")
        print("quit            exit telnet")
        print("status          print status information")
        print("list            list saved connections")
        print("s               connect to a server from the list")

    def com_display(self):
        if self.client.get_key(self.client.escape_character) in control_chars:
            escape = self.client.get_key(self.client.escape_character)
        else:
            escape = self.client.escape_character
            
        print(f"escape          [{escape}]")

    def com_set(self, command):
        args = command.split(' ')
        if len(args) == 1:
            print("Format is \'set Name Value\'")
            print("\'set ?\' for help.")
        elif args[1] == '?':
            print("escape          character to escape back to telnet command mode")
        elif len(args) == 3 and args[1] == 'escape':
            if args[2] in control_chars:
                self.client.escape_character = control_chars[f"{args[2]}"]
            else:
                self.client.escape_character = args[2]
            if self.client.get_key(self.client.escape_character) in control_chars:
                print(f'Escape character is \'{self.client.get_key(self.client.escape_character)}\'.')
            else:
                print(f'Escape character is \'{self.client.escape_character}\'.')
        else:
            print("Format is \'set Name Value\'")
            print("\'set ?\' for help.")

    def com_status(self):
        if not self.client.connection_active:
            print("No connection.")
        else:
            print(f"Connected to {self.client.current_host}.")
            print("Operating in obsolete linemode")
        if self.client.get_key(self.client.escape_character) in control_chars:
            print(f'Escape character is \'{self.client.get_key(self.client.escape_character)}\'.')
        else:
            print(f'Escape character is \'{self.client.escape_character}\'.')

    def com_open(self, command):
        if self.client.paused_transmission:
            print(f'?Already connected to {self.client.current_host}')
            return

        args = command.split(' ')
        if len(args) < 2:
            print("usage: open host-name [port]")
        elif args[1] == '?':
            print('usage: open host-name [port]')
        elif len(args) == 2:
            self.client.connect(args[1], 'telnet')
        else:
            self.client.connect(args[1], args[2])

    def connect_to_numbered_connection(self, number):
        try:
            for index, (host, port) in enumerate(self.client.connections_cache.items()):
                if index+1 == int(number):
                    self.client.connect(host, port)
                    return
            print("Invalid index.")
        except:
            print("Invalid index.")

    def send_numbered_message(self, number):
        try:
            index = int(number) - 1
            if self.client.current_host in self.client.message_cache:
                if index < len(self.client.message_cache[self.client.current_host]):
                    message = self.client.message_cache[self.client.current_host][index]
                    self.client.cached_message = message
                    print(message)
                else:
                    print("Invalid index.")
            else:
                print("No messages cached for the current connection.")
        except ValueError:
            print("Invalid index.")

    def display_msg_cache(self):
        if self.client.current_host in self.client.message_cache:
            print(f"Messages sent to {self.client.current_host}:")
            for index, message in enumerate(self.client.message_cache[self.client.current_host], start=1):
                print(f"{index} - {message}")
        else:
            print("No messages cached for the current connection.")

    def display_con_cache(self):
        index = 1
        if len(self.client.connections_cache.items()) != 0:
            for host, port in self.client.connections_cache.items():
                print(f"{index} - {host}:{port}")
                index += 1
        else:
            print("No cached connections.")

    def com_l1(self, command):
        args = command.split(' ')
        if len(args) < 2:
            print("usage: L1 [%list] [%<index>]")
        elif args[1] == '?':
            print("usage: L1 [%list] [%<index>]")
        elif len(args) == 2 and args[1] == '%list':
            self.display_con_cache()
        elif len(args) == 2 and args[1].startswith('%'):
            if self.client.paused_transmission:
                print(f'?Already connected to {self.client.current_host}')
                return
            
            args[1] = args[1].replace('%', '')
            self.connect_to_numbered_connection(args[1])
        else:
            print("usage: L1 [%list] [%<index>]")

    def com_l2(self, command):
        if self.client.connection_active:
            args = command.split(' ')
            if len(args) < 2:
                print("usage: L2 [%list] [%<index>]")
            elif args[1] == '?':
                print("usage: L2 [%list] [%<index>]")
            elif len(args) == 2 and args[1] == '%list':
                self.display_msg_cache()
            elif len(args) == 2 and args[1].startswith('%'):
                args[1] = args[1].replace('%', '')
                self.send_numbered_message(args[1])
            else:
                print("usage: L2 [%list] [%<index>]")
        else:
            print("No active connection.")

    def start(self):
        port = 'telnet'
        if len(sys.argv) == 3:
            host = sys.argv[1]
            port = sys.argv[2]
            self.com_open('_ ' + host + ' ' + port)
        elif len(sys.argv) == 2:
            host = sys.argv[1]
            self.com_open('_ ' + host + ' ' + port)

        while True:
            if self.client.active_interface():
                if self.client.cached_message != '':
                    command = ''
                else:
                    command = input('telnet> ')

                if command == '' and self.client.paused_transmission:
                    self.client.paused_transmission = False
                elif command == '' and not self.client.connection_active:
                    continue
                elif command.lower().startswith('open'):
                    self.com_open(command)
                elif command.lower() == 'quit':
                    self.client.end()
                    sys.exit()
                elif command == 'close':
                    self.client.close()
                elif command == '?':
                    self.show_commands()
                elif command.lower() == 'status':
                    self.com_status()
                elif command.lower() == 'display':
                    self.com_display()
                elif command.lower().startswith('set'):
                    self.com_set(command)
                elif command.lower().startswith('l1'):
                    self.com_l1(command)
                elif command.lower().startswith('l2'):
                    self.com_l2(command)
                else:
                    print('?Invalid command')


client = TelnetClient()
terminal = TelnetTerminal(client)
terminal.start()
