import os
import json
import yaml
import re
from data import deployment_json, service_json
from parser import *
from tcp_handler import TcpHandler, check_http_status
from api_handler import ApiHandler
from bcolors import BColors
from getpass import getpass
from config_json_handler import get_json_from_config, set_token_to_json_config,set_default_namespace_to_json_config,\
    show_namespace_token_from_config
from answer_parsers import TcpApiParser
import uuid
from keywords import JSON_TEMPLATES_RUN_FILE, LOWER_CASE_ERROR, NO_IMAGE_AND_CONFIGURE_ERROR, JSON_TEMPLATES_EXPOSE_FILE
from run_configure import RunConfigure
from datetime import datetime
from hashlib import sha256, md5


config_json_data = get_json_from_config()


class Client:
    def __init__(self, version):
        self.path = os.getcwd()
        self.version = version
        self.parser = create_parser(self.version)
        uuid_v4 = str(uuid.uuid4())
        self.args = vars(self.parser.parse_args())
        self.debug = self.args.get("debug")
        self.tcp_handler = TcpHandler(uuid_v4, self.args.get("debug"))
        self.api_handler = ApiHandler(uuid_v4)

    def go_config(self):
            if self.args.get("set_token"):
                set_token_to_json_config(self.args.get("set_token"))
            elif self.args.get("set_default_namespace"):
                if not self.test_namespace(self.args.get("set_default_namespace")):
                    return
                set_default_namespace_to_json_config(self.args.get("set_default_namespace"))
            else:
                show_namespace_token_from_config()

    @staticmethod
    def logout():
        set_token_to_json_config("")
        print("Bye!")

    def login(self):
        email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        is_valid = re.compile(email_regex)
        try:
            email = input('Enter your email: ')
        except KeyboardInterrupt:
            return
        if not is_valid.findall(email):
            print("Email is not valid")
            return
        try:
            pwd = getpass()
        except KeyboardInterrupt:
            return
        json_to_send = {"username": email, "password": md5((email+pwd).encode()).hexdigest()}
        if self.args.get("debug"):
            self.log_time()
        self.tcp_connect()
        api_result = self.api_handler.login(json_to_send)
        if 'ok' in api_result:
            set_token_to_json_config(api_result['token'])
        if not self.handle_api_result(api_result):
            return

        json_result = self.get_and_handle_tcp_result('post')
        self.tcp_handler.close()
        if not check_http_status(json_result, self.args.get("command")):
            return

    def go(self):
        self.check_file_existence()
        self.check_arguments()

        if self.args.get("kind") in ("deployments", "deploy", "deployment"):
            self.args["kind"] = "deployments"
        elif self.args.get("kind") in ("po", "pods", "pod"):
            self.args["kind"] = "pods"
        elif self.args.get("kind") in ("service", "services", "svc"):
            self.args["kind"] = "services"
        else:
            self.args["kind"] = "namespaces"

        if self.args['command'] == 'run':
            self.go_run()

        elif self.args['command'] == 'create':
            self.go_create()

        elif self.args['command'] == 'get':
            self.go_get()

        elif self.args['command'] == 'delete':
            self.go_delete()

        elif self.args['command'] == 'replace':
            self.go_replace()

        elif self.args['command'] == 'config':
            self.go_config()

        elif self.args['command'] == 'expose':
            self.go_expose()

        elif self.args['command'] == 'login':
            self.login()

        elif self.args['command'] == 'logout':
            self.logout()

        elif self.args['command'] == 'set':
            self.go_set()

        elif self.args['command'] == 'restart':
            self.go_restart()

        elif self.args['command'] == 'scale':
            self.go_scale()

    def go_restart(self):
        self.log_time()
        self.tcp_connect()

        namespace = self.args['namespace']
        if not namespace:
            namespace = config_json_data.get("default_namespace")
        api_result = self.api_handler.delete("deployments", self.args["name"], namespace, True)
        if not self.handle_api_result(api_result):
            return

        json_result = self.get_and_handle_tcp_result('restart')
        self.tcp_handler.close()
        if not check_http_status(json_result, self.args.get("command")):
            return

    def go_scale(self):
        if self.args.get("debug"):
            self.log_time()
        self.tcp_connect()

        namespace = self.args.get('namespace')
        if not namespace:
            namespace = config_json_data.get("default_namespace")

        count = self.args.get("count")
        try:
            replicas_count = int(count)
            json_to_send = {"replicas": replicas_count}
            api_result = self.api_handler.scale(json_to_send, self.args.get("name"), namespace)
        except (ValueError, TypeError):
            print('{}{}{} {}'.format(
                BColors.FAIL,
                "Error: ",
                "Count is not integer",
                BColors.ENDC,
            ))
            return
        if not self.handle_api_result(api_result):
            return

        json_result = self.get_and_handle_tcp_result('scale')
        self.tcp_handler.close()
        if not check_http_status(json_result, self.args.get("command")):
            return

    def go_set(self):
        if self.args.get("debug"):
            self.log_time()
        self.tcp_connect()

        namespace = self.args.get('namespace')
        if not namespace:
            namespace = config_json_data.get("default_namespace")

        args = self.args.get("args")
        if args:
            if '=' in args:
                container_name, image = args.split('=')
                json_to_send = {"name": self.args.get("name"), "image": image}
                api_result = self.api_handler.set(json_to_send, container_name, namespace)
            else:
                try:
                    replicas_count = int(args)
                    json_to_send = {"replicas": replicas_count}
                    api_result = self.api_handler.set(json_to_send, self.args.get("name"), namespace)
                except (ValueError, TypeError):
                    print('{}{}{} {}'.format(
                        BColors.FAIL,
                        "Error: ",
                        "Count is not integer",
                        BColors.ENDC,
                    ))
                    return

            if not self.handle_api_result(api_result):
                return

            json_result = self.get_and_handle_tcp_result('set')
            self.tcp_handler.close()
            if not check_http_status(json_result, self.args.get("command")):
                return
        else:
            print('{}{}{} {}'.format(
                BColors.FAIL,
                "Error: ",
                "Empty args",
                BColors.ENDC,
            ))
            return

    def go_run(self):
        json_to_send = self.construct_run()
        if not json_to_send:
            return
        if self.debug:
            self.log_time()

        self.tcp_connect()
        namespace = self.args.get('namespace')
        if not namespace:
            namespace = config_json_data.get("default_namespace")
        api_result = self.api_handler.run(json_to_send, namespace)
        if not self.handle_api_result(api_result):
            return
        json_result = self.get_and_handle_tcp_result('run')

        self.tcp_handler.close()
        if not check_http_status(json_result, self.args.get("command")):
            return

    def go_expose(self):
        namespace = self.args.get('namespace')
        if not namespace:
            namespace = config_json_data.get("default_namespace")

        json_to_send = self.construct_expose(namespace)
        if self.debug:
            self.log_time()

        if not json_to_send:
            return
        self.tcp_connect()

        api_result = self.api_handler.expose(json_to_send, namespace)
        if not self.handle_api_result(api_result):
            return

        json_result = self.get_and_handle_tcp_result('expose')
        self.tcp_handler.close()
        if not check_http_status(json_result, self.args.get("command")):
            return

    def go_create(self):
        if self.args.get("debug"):
            self.log_time()
        self.tcp_connect()

        json_to_send = self.get_json_from_file()
        namespace = json_to_send["metadata"].get("namespace")
        if not namespace:
            namespace = self.args.get('namespace')
            if not namespace:
                namespace = config_json_data.get("default_namespace")

        api_result = self.api_handler.create(json_to_send, namespace)
        if not self.handle_api_result(api_result):
            return

        json_result = self.get_and_handle_tcp_result('create')
        self.tcp_handler.close()
        if not check_http_status(json_result, self.args.get("command")):
            return

    def test_namespace(self, namespace):
        if self.debug:
            self.log_time()
        self.tcp_connect()

        api_result = self.api_handler.get_namespaces(namespace)

        if not self.handle_api_result(api_result):
            return

        json_result = self.get_and_handle_tcp_result('check namespace')
        self.tcp_handler.close()
        if not check_http_status(json_result, "check namespace"):
            return
        return True

    def go_get(self):
        kind, name = self.construct_get()
        if self.debug:
            self.log_time()
        self.tcp_connect()

        self.namespace = self.args.get('namespace')
        if not self.namespace:
            self.namespace = config_json_data.get("default_namespace")

        if kind == "namespaces":
            if self.args.get("name"):
                api_result = self.api_handler.get_namespaces(self.args.get("name"))
            else:
                api_result = self.api_handler.get_namespaces()
        else:
            api_result = self.api_handler.get(kind, name, self.namespace)
        if not self.handle_api_result(api_result):
            return

        json_result = self.get_and_handle_tcp_result('get')
        self.tcp_handler.close()
        if not check_http_status(json_result, "get"):
            return
        return json_result

    def get_and_handle_tcp_result(self, command_name):
        try:
            tcp_result = self.tcp_handler.receive()
            if command_name == 'get':
                if not tcp_result.get('status') == 'Failure':
                    if self.args.get("debug"):

                        print('{}{}{}'.format(
                            BColors.OKBLUE,
                            'get result:\n',
                            BColors.ENDC
                        ))
                    self.print_result(tcp_result)

            return tcp_result

        except RuntimeError as e:
            print('{}{}{}'.format(
                BColors.FAIL,
                e,
                BColors.ENDC
            ))
            return None

    def go_delete(self):
        kind, name = self.construct_delete()

        self.log_time()
        self.tcp_connect()

        self.args['output'] = 'yaml'
        namespace = self.args['namespace']
        if not namespace:
            namespace = config_json_data.get("default_namespace")
        if kind != 'namespaces':
            api_result = self.api_handler.delete(kind, name, namespace, self.args.get("pods"))
        else:
            api_result = self.api_handler.delete_namespaces(name)
        if not self.handle_api_result(api_result):
            return

        json_result = self.get_and_handle_tcp_result('delete')
        self.tcp_handler.close()
        if not check_http_status(json_result, self.args.get("command")):
            return

    def go_replace(self):
        self.log_time()
        self.tcp_connect()

        self.args['output'] = 'yaml'
        namespace = self.args['namespace']

        json_to_send = self.get_json_from_file()
        kind = '{}s'.format(json_to_send.get('kind')).lower()

        if kind != 'namespaces':
            api_result = self.api_handler.replace(json_to_send, namespace)
        else:
            api_result = self.api_handler.replace_namespaces(json_to_send)
        if not self.handle_api_result(api_result):
            return

        json_result = self.get_and_handle_tcp_result('replace')

        self.tcp_handler.close()
        if not check_http_status(json_result, self.args.get("command")):
            return

    def check_file_existence(self):
        if 'file' in self.args:
            if self.args.get('file'):
                if not os.path.isfile(os.path.join(self.path, self.args.get('file'))):
                    self.parser.error('no such file: {}'.format(
                        os.path.join(self.path, self.args.get('file'))
                    ))

    def check_arguments(self):
        if not (self.args.get('version') or self.args.get('help') or self.args.get('command')):
            self.parser.print_help()

    def handle_api_result(self, api_result):
        if api_result.get('id'):
            if self.debug:
                print('{}{}...{} {}OK{}'.format(
                    BColors.OKBLUE,
                    'api connection',
                    BColors.ENDC,
                    BColors.BOLD,
                    BColors.ENDC
                ))
                print('{}{}{}{}'.format(
                    BColors.OKGREEN,
                    'Command Id: ',
                    api_result.get('id'),
                    BColors.ENDC,

                ))
            return True
        elif 'error' in api_result:
            print('{}api error: {}{}'.format(
                BColors.FAIL,
                api_result.get('error'),
                BColors.ENDC
            ))
            self.tcp_handler.close()
            return

    def tcp_connect(self):
        try:
            tcp_auth_result = self.tcp_handler.connect()
            if tcp_auth_result.get('ok') and self.debug:
                # print(tcp_auth_result)
                print('{}{}...{} {}OK{}'.format(
                    BColors.OKBLUE,
                    'tcp authorization',
                    BColors.ENDC,
                    BColors.BOLD,
                    BColors.ENDC
                ))
        except RuntimeError as e:
            print('{}{}{}'.format(
                BColors.FAIL,
                e,
                BColors.ENDC
            ))

    def print_result(self, result):
        if self.args.get("command") != "expose":
            if self.args.get('output') == 'yaml':
                result = result["results"]
                print(yaml.dump(result, default_flow_style=False))
            elif self.args['output'] == 'json':
                result = result["results"]
                print(json.dumps(result, indent=4))
            else:
                deploy = self.args.get("deploy")
                TcpApiParser(result, deploy=deploy)

    def log_time(self):
        if self.args["debug"]:
            print('{}{}{}'.format(
                BColors.WARNING,
                str(datetime.now())[11:19:],
                BColors.ENDC
            ))

    def construct_run(self):
        json_to_send = deployment_json
        if not self.args["name"].islower():
            e = LOWER_CASE_ERROR
            print('{}{}{} {}'.format(
            BColors.FAIL,
            "Error: ",
            e,
            BColors.ENDC,
            ))
            return
        json_to_send['metadata']['name'] = self.args['name']

        if self.args["configure"] and not self.args.get("image"):
            runconfigure = RunConfigure()
            param_dict = runconfigure.get_data_from_console()
            if not param_dict:
                return
            image = param_dict["image"]
            ports = param_dict["ports"]
            labels = param_dict["labels"]
            env = param_dict["env"]
            cpu = param_dict["cpu"]
            memory = param_dict["memory"]
            replicas = param_dict["replicas"]
            commands = param_dict["commands"]

        elif self.args.get("image") and not self.args["configure"]:
            image = self.args["image"]
            ports = self.args["ports"]
            labels = self.args["labels"]
            env = self.args["env"]
            cpu = self.args["cpu"]
            memory = self.args["memory"]
            replicas = self.args["replicas"]
            commands = self.args["commands"]

        if not self.args["configure"] and not self.args["image"]:
            self.parser.error(NO_IMAGE_AND_CONFIGURE_ERROR)
            return

        json_to_send['spec']['replicas'] = replicas
        json_to_send['spec']['template']['spec']['containers'][0]['name'] = self.args['name']
        json_to_send['spec']['template']['spec']['containers'][0]['image'] = image
        if commands:
            json_to_send['spec']['template']['spec']['containers'][0]['command'] = commands
        if ports:
            json_to_send['spec']['template']['spec']['containers'][0]['ports'] = []
            for port in ports:
                json_to_send['spec']['template']['spec']['containers'][0]['ports'].append({
                    'containerPort': port
                })
        if labels:
            for key, value in labels.items():
                json_to_send['metadata']['labels'].update({key: value})
                json_to_send['spec']['template']['metadata']['labels'].update({key: value})
        if env:
            json_to_send['spec']['template']['spec']['containers'][0]['env'] = [
                {
                    "name": key,
                    "value": value
                }
                for key, value in env.items()]
        json_to_send['spec']['template']['spec']['containers'][0]['resources']["requests"]['cpu'] = cpu
        json_to_send['spec']['template']['spec']['containers'][0]['resources']["requests"]['memory'] = memory
        with open(os.path.join(os.getenv("HOME") + "/.containerum/src/", JSON_TEMPLATES_RUN_FILE), 'w', encoding='utf-8') as w:
            json.dump(json_to_send, w, indent=4)

        return json_to_send

    def get_json_from_file(self):
        file_name = os.path.join(self.path, self.args['file'])
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                body = json.load(f)
                return body
        except FileNotFoundError:
            self.parser.error('no such file: {}'.format(
                file_name
            ))
        except json.decoder.JSONDecodeError as e:
            pass

        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                body = yaml.load(f)
                return body
        except FileNotFoundError:
            self.parser.error('no such file: {}'.format(
                file_name
            ))
        except yaml.YAMLError as e:
            self.parser.error('bad json or yaml: {}'.format(
                e
            ))

    def construct_delete(self):
        if self.args['file'] and self.args['kind'] == "namespaces" and not self.args['name']:
            body = self.get_json_from_file()
            name = body['metadata']['name']
            kind = '{}s'.format(body['kind'].lower())
            return kind, name

        elif not self.args['file'] and self.args['kind'] != "namespaces" and self.args['name']:
            kind = self.args['kind']
            name = self.args['name']
            return kind, name

        elif not self.args['file'] and self.args['kind'] == "namespaces":
            self.parser.error(ONE_REQUIRED_ARGUMENT_ERROR)
        elif self.args['file'] and self.args['kind'] == "namespaces":
            self.parser.error(KIND_OR_FILE_BOTH_ERROR)
        elif self.args['file'] and self.args['name']:
            self.parser.error(NAME_OR_FILE_BOTH_ERROR)
        elif self.args['kind'] != "namespaces" and not self.args['name']:
            self.parser.error(NAME_WITH_KIND_ERROR)

    def construct_get(self):
        if self.args.get('file') and not self.args.get('kind') and not self.args.get('name'):
            body = self.get_json_from_file()
            name = body['metadata']['name']
            kind = '{}s'.format(body['kind'].lower())
            return kind, name

        elif not self.args.get('file') and self.args.get('kind'):
            kind = self.args['kind']
            name = self.args.get('name')
            return kind, name

        elif not self.args['file'] and not self.args['kind']:
            self.parser.error(ONE_REQUIRED_ARGUMENT_ERROR)
        elif self.args['file'] and self.args['kind']:
            self.parser.error(KIND_OR_FILE_BOTH_ERROR)
        elif self.args['file'] and self.args['name']:
            self.parser.error(NAME_OR_FILE_BOTH_ERROR)

    def construct_expose(self, namespace):
        labels = {}
        is_external = {"external": "true"}
        json_to_send = service_json
        ports = self.args.get("ports")
        self.args["kind"] = "deployments"
        if ports:
            for p in ports:
                p = p.split(":")
                if len(p) == 3:
                    if p[2].upper() == "TCP" or p[2].upper() == "UDP":
                        json_to_send["spec"]["ports"].append({"name": p[0], "protocol": p[2].upper(), "targetPort": int(p[1])})
                    else:
                        json_to_send["spec"]["ports"].append({"name": p[0],"protocol": "TCP", "port": int(p[2]), "targetPort": int(p[1])})
                        is_external["external"] = "false"
                if len(p) == 4:
                    json_to_send["spec"]["ports"].append({"name": p[0], "port": int(p[2]), "protocol": p[3].upper(),
                                                         "targetPort": int(p[1])})
                    is_external["external"] = "false"
                elif len(p) == 2:
                    json_to_send["spec"]["ports"].append({"name": p[0], "protocol": "TCP", "targetPort": int(p[1])})
        result = self.go_get()
        if not result:
            return
        namespace_hash = sha256(namespace.encode('utf-8')).hexdigest()[:32]
        labels.update({namespace_hash: self.args.get("name")})
        json_to_send["metadata"]["labels"].update(labels)

        json_to_send["metadata"]["labels"].update(is_external)
        json_to_send["metadata"]["name"] = self.args["name"] + "-" + \
                                           md5((self.args.get("name")+str(datetime.now()))
                                               .encode("utf-8")).hexdigest()[:4]
        json_to_send["spec"]["selector"].update(labels)
        with open(os.path.join(os.getenv("HOME") + "/.containerum/src/", JSON_TEMPLATES_EXPOSE_FILE), 'w', encoding='utf-8') as w:
                json.dump(json_to_send, w, indent=4)
        return json_to_send


