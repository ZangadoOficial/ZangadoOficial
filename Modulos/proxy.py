#!/usr/bin/env python3
# encoding: utf-8
# SSHPLUS By @Crazy_vpn
import select
import socket
import sys
import threading
import time

print('\033c')
# conexao
IP = '0.0.0.0'
try:
    PORT = int(sys.argv[1])
except (IndexError, ValueError):
    PORT = 80
PASS = ''
BUFLEN = 8196 * 8
TIMEOUT = 60
MSG = 'SSHPLUS'
COR = '<font color="null">'
FTAG = '</font>'
DEFAULT_HOST = '0.0.0.0:22'
RESPONSE = "HTTP/1.1 200 " + str(COR) + str(MSG) + str(FTAG) + "\r\nContent-length: 0\r\n\r\n \r\n\r\n"


class Server(threading.Thread):
    def __init__(self, host, port):
        threading.Thread.__init__(self)
        self.soc = socket.socket(socket.AF_INET)
        self.running = False
        self.host = host
        self.port = port
        self.threads = []
        self.threadsLock = threading.Lock()
        self.logLock = threading.Lock()

    def run(self):
        self.soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.soc.settimeout(2)
        self.soc.bind((self.host, self.port))
        self.soc.listen(0)
        self.running = True

        try:
            while self.running:
                try:
                    c, addr = self.soc.accept()
                    c.setblocking(1)
                except socket.timeout:
                    continue

                conn = ConnectionHandler(c, self, addr)
                conn.start()
                self.add_conn(conn)
        finally:
            self.running = False
            self.soc.close()

    def print_log(self, log):
        self.logLock.acquire()
        print(log)
        self.logLock.release()

    def add_conn(self, conn):
        try:
            self.threadsLock.acquire()
            if self.running:
                self.threads.append(conn)
        finally:
            self.threadsLock.release()

    def remove_conn(self, conn):
        try:
            self.threadsLock.acquire()
            self.threads.remove(conn)
        finally:
            self.threadsLock.release()

    def close(self):
        try:
            self.running = False
            self.threadsLock.acquire()

            threads = list(self.threads)
            for c in threads:
                c.close()
        finally:
            self.threadsLock.release()


def find_header(head, header):
    aux = head.find((header + ': ').encode())

    if aux == -1:
        return ''

    aux = head.find(':', aux)
    head = head[aux+2:]
    aux = head.find('\r\n')

    if aux == -1:
        return ''

    return head[:aux]


class ConnectionHandler(threading.Thread):
    def __init__(self, soc_client, server, addr):
        threading.Thread.__init__(self)
        self.clientClosed = False
        self.targetClosed = True
        self.client = soc_client
        self.client_buffer = ''
        self.server = server
        self.log = 'Conexao: ' + str(addr)

    def close(self):
        try:
            if not self.clientClosed:
                self.client.shutdown(socket.SHUT_RDWR)
                self.client.close()
        except:
            pass
        finally:
            self.clientClosed = True

        try:
            if not self.targetClosed:
                self.target.shutdown(socket.SHUT_RDWR)
                self.target.close()
        except:
            pass
        finally:
            self.targetClosed = True

    def run(self):
        try:
            self.client_buffer = self.client.recv(BUFLEN)

            host_port = find_header(self.client_buffer, 'X-Real-Host')

            if host_port == '':
                host_port = DEFAULT_HOST

            split = find_header(self.client_buffer, 'X-Split')

            if split != '':
                self.client.recv(BUFLEN)

            if host_port != '':
                passwd = find_header(self.client_buffer, 'X-Pass')

                if len(PASS) != 0 and passwd == PASS:
                    self.method_connect(host_port)
                elif len(PASS) != 0 and passwd != PASS:
                    self.client.send('HTTP/1.1 400 WrongPass!\r\n\r\n')
                if host_port.startswith(IP):
                    self.method_connect(host_port)
                else:
                    self.client.send('HTTP/1.1 403 Forbidden!\r\n\r\n')
            else:
                print('- No X-Real-Host!')
                self.client.send('HTTP/1.1 400 NoXRealHost!\r\n\r\n')

        except Exception as e:
            self.log += ' - error: ' + str(e)
            self.server.print_log(self.log)
        finally:
            self.close()
            self.server.remove_conn(self)

    def connect_target(self, host):
        i = host.find(':')
        if i != -1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            if self.method == 'CONNECT':
                port = 443
            else:
                port = 22

        (soc_family, soc_type, proto, _, address) = socket.getaddrinfo(host, port)[0]

        self.target = socket.socket(soc_family, soc_type, proto)
        self.targetClosed = False
        self.target.connect(address)

    def method_connect(self, path):
        self.log += ' - CONNECT ' + path
        self.connect_target(path)
        self.client.sendall(RESPONSE.encode())
        self.client_buffer = ''
        self.server.print_log(self.log)
        self.do_connect()

    def do_connect(self):
        socs = [self.client, self.target]
        count = 0
        error = False
        while True:
            count += 1
            (recv, _, err) = select.select(socs, [], socs, 3)
            if err:
                error = True
            if recv:
                for in_ in recv:
                    try:
                        data = in_.recv(BUFLEN)
                        if data:
                            if in_ is self.target:
                                self.client.send(data)
                            else:
                                while data:
                                    byte = self.target.send(data)
                                    data = data[byte:]

                            count = 0
                        else:
                            break
                    except:
                        error = True
                        break
            if count == TIMEOUT:
                error = True

            if error:
                break


def main():
    print("\033[0;34m━"*8, "\033[1;32m PROXY SOCKS", "\033[0;34m━"*8, "\n")
    print("\033[1;33mIP:\033[1;32m " + IP)
    print("\033[1;33mPORTA:\033[1;32m " + str(PORT) + "\n")
    print("\033[0;34m━"*10, "\033[1;32m SSHPLUS", "\033[0;34m━\033[1;37m"*11, "\n")
    server = Server(IP, PORT)
    server.start()
    while True:
        try:
            time.sleep(4)
        except KeyboardInterrupt:
            print('\nParando...')
            server.close()
            break


if __name__ == '__main__':
    main()
