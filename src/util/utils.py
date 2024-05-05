import paramiko


def cloud_init_creator(server_name: str,
                       password: str):
    cloud_init = "#cloud-config"
    cloud_init += f"\nuser: {server_name}"

    if password != "":
        cloud_init += f"\npassword: {password}"
        cloud_init += "\nchpasswd: {expire: False}"
        cloud_init += f"\nssh_pwauth: True"

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
    except (paramiko.SSHException, FileNotFoundError):
        return False
    finally:
        client.close()

    return True