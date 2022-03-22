#!/usr/bin/env python3

import socket
import sys
import select
import queue
import os

from file_reader import FileReader


class Jewel:

    # Note, this starter example of using the socket is very simple and
    # insufficient for implementing the project. You will have to modify this
    # code.
    def __init__(self, port, file_path, file_reader):
        self.file_path = file_path
        self.file_reader = file_reader
        buffer_size = 2**18

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', port))
        s.setblocking(False)
        s.listen(100)

        inputs = [s]
        outputs = []
        q = {}

        while inputs:
            readable, writable, exceptional = select.select(inputs, outputs, inputs)
            # print("inputs", inputs)
            # print("outputs", outputs)

            for r in readable:
                if r is s:
                    (client, address) = r.accept()
                    print(f"[CONN] Connection from {address[0]} on port {address[1]}")
                    client.setblocking(0)
                    inputs.append(client)
                    q[client] = queue.Queue()
                else:
                    try:
                        data = r.recv(buffer_size)
                    except ConnectionResetError:
                        print("Closed")
                        inputs.remove(r)
                        if r in outputs:
                            outputs.remove(r)
                        r.close()
                        del q[r]
                    # address = r.getpeername()
                    else:
                        if data:
                            q[r].put(data)
                            if r not in outputs:
                                outputs.append(r)
                        else:
                            if r in outputs:
                                outputs.remove(r)
                            inputs.remove(r)
                            r.close()
                            print("Closed")
                            del q[r]

            for w in writable:
                try:
                    data = q[w].get_nowait().decode()
                    address = w.getpeername()
                    # m = q.get(w)
                    # if m is not None:
                    #     data = m.get_nowait()
                    #     print(data)
                except queue.Empty:
                    outputs.remove(w)
                except UnicodeDecodeError:
                    outputs.remove(w)
                    if w in inputs:
                        inputs.remove(w)
                        del q[w]
                    w.close()
                else:
                    header_end = data.find('\r\n\r\n')
                    if header_end > -1:
                        header_string = data[:header_end]
                        lines = header_string.split('\r\n')

                        request_fields = lines[0].split()
                        headers = lines[1:]

                        # print(request_fields)
                        request_type = request_fields[0]
                        request_path = request_fields[1]
                        print(request_fields)
                        if request_type == "GET":
                            print(f"[REQU] [{address[0]}:{address[1]}] {request_type} request for {request_path}")
                            file = file_reader.get(file_path + request_path, "")
                            if not file:
                                print(f"[ERRO] [{address[0]}:{address[1]}] {request_type} request returned error 404")
                                errormsg = "<html><body><h1>404 Not Found</h1></body></html>".encode()
                                w.send((request_fields[2] + f" 404 Not Found\r\nContent-Length: {len(errormsg)}\r\n\r\n").encode())
                                w.send(errormsg)
                                # q[r].put((request_fields[2] + " 404 Not Found\r\n\r\n").encode())
                            else:
                                mime_type = request_path.split('.')[-1]
                                w.send((request_fields[2] + f" 200 OK\r\nContent-Length: {len(file)}\r\nMIME-Type: {mime_type}\r\n\r\n").encode())
                                w.send(file)
                                # q[r].put((request_fields[2] + " 200 OK\r\n\r\n").encode() + file)
                            # for header in headers:
                            #     header_fields = header.split(':')
                            #     key = header_fields[0].strip()
                            #     val = header_fields[1].strip()
                            #     print('{}: {}'.format(key, val))

                        elif request_type == "HEAD":
                            print(f"[REQU] [{address[0]}:{address[1]}] {request_type} request for {request_path}")
                            file = file_reader.head(file_path + request_path, "")
                            if not file:
                                print(f"[ERRO] [{address[0]}:{address[1]}] {request_type} request returned error 404")
                                w.send((request_fields[2] + f" 404 Not Found\r\nContent-Length: 0\r\n\r\n").encode())
                                # q[r].put((request_fields[2] + " 404 Not Found\r\n\r\n").encode())
                            else:
                                w.send((request_fields[2] + f" 200 OK\r\nContent-Length: {str(file)}\r\n\r\n").encode())
                                # q[r].put((request_fields[
                                #               2] + f" 200 OK\r\nContent-Length: {str(file)}\r\n\r\n").encode())
                            # for header in headers:
                            #     header_fields = header.split(':')
                            #     key = header_fields[0].strip()
                            #     val = header_fields[1].strip()
                            #     print('{}: {}'.format(key, val))

                        else:
                            print(f"[ERRO] [{address[0]}:{address[1]}] {request_type} request returned error 501")
                            errormsg = "<html><body><h1>501 Method Unimplemented</h1></body></html>".encode()
                            w.send((request_fields[2] + f" 501 Method Unimplemented\r\nContent-Length: {len(errormsg)}\r\n\r\n").encode())
                            w.send(errormsg)
                            # q[r].put((request_fields[2] + " 501 Method Unimplemented\r\n\r\n").encode())

                    else:
                        print(f"[ERRO] [{address[0]}:{address[1]}] UNKNOWN request returned error 400")
                        errormsg = "<html><body><h1>400 Invalid Request</h1></body></html>".encode()
                        w.send((data[data.index('HTTP'):data.index('HTTP')+8]+f" 400 Invalid Request\r\nContent-Length: {len(errormsg)}\r\n\r\n").encode())
                        # q[r].put((request_fields[2] + " 400 Invalid Request\r\n\r\n").encode())
                        w.send(errormsg)

            for e in exceptional:
                inputs.remove(e)
                if e in outputs:
                    outputs.remove(e)
                e.close()
                print("Closed")
                del q[e]


        # while True:
        #     (client, address) = s.accept()
        #     print(f"[CONN] Connection from {address[0]} on port {address[1]}")
        #     data = client.recv(buffer_size).decode()
        #     if not data:
        #         break
        #     header_end = data.find('\r\n\r\n')
        #     if header_end > -1:
        #         header_string = data[:header_end]
        #         lines = header_string.split('\r\n')
        #
        #         request_fields = lines[0].split()
        #         headers = lines[1:]
        #
        #         # print(request_fields)
        #         request_type = request_fields[0]
        #         request_path = request_fields[1]
        #         print(request_fields)
        #         if request_type == "GET":
        #             print(f"[REQU] [{address[0]}:{address[1]}] {request_type} request for {request_path}")
        #             file = file_reader.get(file_path + request_path, "")
        #             if not file:
        #                 print(
        #                     f"[ERRO] [{address[0]}:{address[1]}] {request_type} request returned error 404")
        #                 client.send((request_fields[2] + " 404 Not Found\r\n\r\n").encode())
        #                 # q[r].put((request_fields[2] + " 404 Not Found\r\n\r\n").encode())
        #             else:
        #                 mime_type = request_path.split('.')[-1]
        #                 client.send((request_fields[2] + " 200 OK\r\n\r\n").encode())
        #                 client.send(file)
        #                 # q[r].put((request_fields[2] + " 200 OK\r\n\r\n").encode())
        #                 # q[r].put(file)
        #             # for header in headers:
        #             #     header_fields = header.split(':')
        #             #     key = header_fields[0].strip()
        #             #     val = header_fields[1].strip()
        #             #     print('{}: {}'.format(key, val))
        #
        #         elif request_type == "HEAD":
        #             print(f"[REQU] [{address[0]}:{address[1]}] {request_type} request for {request_path}")
        #             file = file_reader.head(file_path + request_path, "")
        #             if not file:
        #                 print(
        #                     f"[ERRO] [{address[0]}:{address[1]}] {request_type} request returned error 404")
        #                 client.send((request_fields[2] + " 404 Not Found\r\n\r\n").encode())
        #                 # q[r].put((request_fields[2] + " 404 Not Found\r\n\r\n").encode())
        #             else:
        #                 client.send((request_fields[
        #                             2] + f" 200 OK\r\nContent-Length: {str(file)}\r\n\r\n").encode())
        #                 # q[r].put((request_fields[
        #                 #               2] + f" 200 OK\r\nContent-Length: {str(file)}\r\n\r\n").encode())
        #             # for header in headers:
        #             #     header_fields = header.split(':')
        #             #     key = header_fields[0].strip()
        #             #     val = header_fields[1].strip()
        #             #     print('{}: {}'.format(key, val))
        #
        #         else:
        #             print(f"[ERRO] [{address[0]}:{address[1]}] {request_type} request returned error 501")
        #             client.send((request_fields[2] + " 501 Method Unimplemented\r\n\r\n").encode())
        #             # q[r].put((request_fields[2] + " 501 Method Unimplemented\r\n\r\n").encode())
        #
        #     else:
        #         print(f"[ERRO] [{address[0]}:{address[1]}] {request_type} request returned error 400")
        #         client.send((request_fields[2] + " 400 Invalid Request\r\n\r\n").encode())
        #         # q[r].put((request_fields[2] + " 400 Invalid Request\r\n\r\n").encode())
        #     client.close()


if __name__ == "__main__":
    # port = int(sys.argv[1])
    # file_path = sys.argv[2]

    port = os.environ.get('PORT')
    file_path = "./files"

    FR = FileReader()
    print(port, file_path)

    J = Jewel(port, file_path, FR)
