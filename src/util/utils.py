import paramiko
import re
from datetime import date
from util.logger import get_logger

backend_logger = get_logger(name='backend', log_level='INFO', save_path="./log/backend")


def cloud_init_creator(server_name: str,
                       password: str,
                       user_data: str):
    cloud_init = "#cloud-config"
    cloud_init += f"\nuser: {server_name}"

    if password is not None:
        cloud_init += f"\npassword: {password}"
        cloud_init += "\nchpasswd: {expire: False}"
        cloud_init += f"\nssh_pwauth: True"

    if user_data is not None:
        cloud_init += "\n" + user_data

    return cloud_init


def validate_ssh_key(**kwargs) -> bool:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    host_name = kwargs['host_name']
    user_name = kwargs['user_name']

    try:
        if kwargs['private_key'] != "":
            key = paramiko.RSAKey.from_private_key(kwargs['private_key'])
            client.connect(hostname=host_name, username=user_name, pkey=key)
        else:
            client.connect(hostname=host_name, username=user_name, password=kwargs['password'])
    except Exception as e:
        backend_logger.error(e)
        return False
    finally:
        client.close()

    return True


def gateway_extractor(cidr: str):
    # EX) 192.168.0.0/24 -> 192.168.0.1 반환
    return cidr[:-4] + '1'


def generator_len(generator: object):
    count = 0
    for _ in generator:
        count += 1

    return count


def create_env_dict(env: str) -> dict:
    if env is not None:
        result = {}
        dicts = env.split(',')
        for element in dicts:
            key, value = element.split('=')
            result[key] = value
    else:
        result = None

    return result


def create_cmd_list(cmds: str):
    if cmds is not None:
        cmd_list = []
        cmds = cmds.split(",")
        for cmd in cmds:
            cmd_list.append(cmd)

        return cmd_list

    else:
        return None


def alphabet_check(s: str):
    pattern = r'^[a-zA-Z0-9]+$'
    return bool(re.match(pattern, s))


def subnet_name_creator(network_name: str):
    return f'{network_name}_subnet'


def str_to_date(date_str: str):
    split_date = date_str.split(sep='-')
    return date(int(split_date[0]), int(split_date[1]), int(split_date[2]))


def extension_date_check(old_end_date: date, new_end_date: date):
    return old_end_date < new_end_date
