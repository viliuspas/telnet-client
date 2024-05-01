import socket
import threading
import time
import sys

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
        self.current_host = ''
        self.sock = None
        self.receive_thread = None
        self.send_thread = None
        self.escape_character = '\x1d'

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
            if self.paused_transmission:
                time.sleep(1)
                continue

            message = input()
            if message == self.escape_character:
                self.paused_transmission = True
            else:
                try:
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
        else:
            print('Need to be connected first for `bye\'.')

    def remote_end(self):
        if self.connection_active:
            self.sock.close()
        print("Connection closed by foreign host.")
        sys.exit()

    def end(self):
        if self.connection_active:
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
                command = input('telnet> ')
                if command == '' and self.client.paused_transmission:
                    self.client.paused_transmission = False
                elif command == '' and not self.client.connection_active:
                    continue
                elif command.startswith('open'):
                    self.com_open(command)
                elif command == 'quit':
                    self.client.end()
                    sys.exit()
                elif command == 'close':
                    self.client.close()
                elif command == '?':
                    self.show_commands()
                elif command == 'status':
                    self.com_status()
                elif command == 'display':
                    self.com_display()
                elif command.startswith('set'):
                    self.com_set(command)
                else:
                    print('?Invalid command')


client = TelnetClient()
terminal = TelnetTerminal(client)
terminal.start()
