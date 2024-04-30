import yaml

with open("config/server_config.yaml") as yml:
    server_config = yaml.full_load(yml)

with open("config/openstack_config.yaml") as yml:
    openstack_config = yaml.full_load(yml)

with open("config/db_config.yaml") as yml:
    db_config = yaml.full_load(yml)
