import yaml

with open("Config/server_config.yaml") as yml:
    server_config = yaml.full_load(yml)

with open("Config/openstack_config.yaml") as yml:
    openstack_config = yaml.full_load(yml)
