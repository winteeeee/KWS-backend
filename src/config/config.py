import yaml

with open("config/server_config.yaml", encoding='UTF-8') as yml:
    server_config = yaml.full_load(yml)

with open("config/openstack_config.yaml", encoding='UTF-8') as yml:
    openstack_config = yaml.full_load(yml)

with open("config/db_config.yaml", encoding='UTF-8') as yml:
    db_config = yaml.full_load(yml)

with open("config/node_config.yaml", encoding='UTF-8') as yml:
    node_config = yaml.full_load(yml)
