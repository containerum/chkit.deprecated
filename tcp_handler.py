import socket
import json
from bcolors import BColors
from config_json_handler import get_json_from_config
from keywords import *

config_json_data = get_json_from_config()


class TcpHandler:
    def __init__(self, uuid_v4, debug):
        self.debug = debug
        self.TCP_IP = config_json_data.get("tcp_handler").get("TCP_IP")
        self.TCP_PORT = config_json_data.get("tcp_handler").get("TCP_PORT")
        self.BUFFER_SIZE = config_json_data.get("tcp_handler").get("BUFFER_SIZE")
        self.AUTH_FORM = {
            "channel": uuid_v4,
            "token": config_json_data.get("tcp_handler").get("AUTH_FORM").get("token"),
        }

    def connect(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect((self.TCP_IP, self.TCP_PORT))
        self.s.send((json.dumps(self.AUTH_FORM) + '\n').encode('utf-8'))
        data = self.s.recv(self.BUFFER_SIZE)
        if not data:
            raise RuntimeError(TCP_RUNTIME_ERROR)
        else:
            result = json.loads(data.decode('utf-8'))

        return result

    def receive(self):
        data = ''
        while data[-1::] != '\n':
            received = self.s.recv(self.BUFFER_SIZE).decode('utf-8')
            if not received:
                raise RuntimeError(TCP_RUNTIME_ERROR)
            if self.debug:
                print('{}tcp received {} bytes...{}'.format(
                    BColors.OKBLUE,
                    len(received),
                    BColors.ENDC
                ))
            data += received
            # print(len(data))
            # print(data[-1::] == '\n')
        # data = self.s.recv(self.BUFFER_SIZE)

        try:
            result = json.loads(data)
            if self.debug:
                print('{}{}...{} {}OK{}'.format(
                    BColors.OKBLUE,
                    TCP_COMPLETE,
                    BColors.ENDC,
                    BColors.BOLD,
                    BColors.ENDC
                ))
        except Exception:
            with open('received_str', 'w', encoding='utf-8') as w:
                w.write(data.decode('utf-8'))
            result = {}
        # print(json.dumps(result, indent=4))
        # pretty_json = json.dumps(result, indent=4)

        return result

    def close(self):
        self.s.close()


def check_http_status(result, command):
    try:
        error = result.get("error")
        if error:

            print('{}{}{} {}'.format(
                BColors.FAIL,
                "Error: ",
                error,
                BColors.ENDC,
                ))
            return False
        else:
            if command != "get":
                print('{}{}...{} {}OK{}'.format(
                    BColors.WARNING,
                    command,
                    BColors.ENDC,
                    BColors.BOLD,
                    BColors.ENDC
                ))
        return True
    except AttributeError:
        print('{}{}{} {}'.format(
            BColors.FAIL,
            "Error: ",
            "TCP result is empty",
            BColors.ENDC,
        ))
        return False