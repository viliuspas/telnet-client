import socket
import ipaddress
import threading
import time
import sys

class TelnetClient:
    def __init__(self):
        self.connection_active = False
        self.paused_transmission = False
        self.current_host = ''
        self.sock = None
        self.receive_thread = None
        self.send_thread = None

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
            if message == '\x1d':
                self.paused_transmission = True
            else:
                try:
                    self.sock.sendall((message + '\r\n').encode('utf-8'))
                except OSError:
                    self.connection_active = False
                    break

    def connect(self, host, port):
        try:
            host = socket.gethostbyname(host)
        except Exception:
            pass

        try:
            ipaddress.ip_address(host)
            print(f'Trying {host}...')
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.sock.settimeout(3)
                self.sock.connect((host, int(port)))
                self.sock.setblocking(False)
                print(f'Connected to {host}.')
                print('Escape character is \'^]\'.')
                self.current_host = host
                self.connection_active = True
                self.receive_thread = threading.Thread(target=self.receive, daemon=True)
                self.send_thread = threading.Thread(target=self.send, daemon=True)
                self.receive_thread.start()
                self.send_thread.start()
            except Exception:
                print('telnet: Unable to connect to remote host: Network is unreachable')
        except ValueError:
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
            print('Conenction closed.')
        sys.exit()

class TelnetTerminal:
    def __init__(self, client):
        self.client = client

    def show_commands(self):
        print("close           close current connection")
        #print("logout          forcibly logout remote user and close the connection")
        #print("display         display operating parameters")
        #print("mode            try to enter line or character mode ('mode ?' for more)")
        print("open            connect to a site")
        print("quit            exit telnet")
        #print("send            transmit special characters ('send ?' for more)")
        #print("set             set operating parameters ('set ?' for more)")
        #print("unset           unset operating parameters ('unset ?' for more)")
        print("status          print status information")
        #print("toggle          toggle operating parameters ('toggle ?' for more)")
        #print("slc             set treatment of special characters")
        #print()
        #print("z               suspend telnet")
        #print("environ         change environment variables ('environ ?' for more)")

    # def com_mode(self, command):
    #     args = command.split(' ')
    #     if len(args) == 1:
    #         print("Wrong number of arguments for command.")
    #     elif len(args) == 2:
    #         if not self.client.connection_active:
    #             print("?Need to be connected first.")
    #         else:

    def com_status(self):
        if not self.client.connection_active:
            print("No connection.")
            print("Escape character is \'^]\'.")
        else:
            print(f"Connected to {self.client.current_host}.")
            print("Operating in obsolete linemode")
            #print("Local character echo")
            print("Escape character is \'^]\'.")

    def com_open(self, command):
        if self.client.paused_transmission:
            print(f'?Already connected to {self.client.current_host}')
            return

        args = command.split(' ')
        if len(args) < 2:
            print("usage: open [-l user] [-a] host-name [port]")
        elif args[1] == '?':
            print('usage: open [-l user] [-a] host-name [port]')
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
                args = command.split(' ')
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
                else:
                    print('?Invalid command')


client = TelnetClient()
terminal = TelnetTerminal(client)
terminal.start()
