import pathlib
import yaml

BASE_DIR = pathlib.Path(__file__).parent.parent
config_path = BASE_DIR / 'conf' / 'main.yaml'

def get_conf(path):
    with open(path) as f:
        config = yaml.safe_load(f)
    return config

conf = get_conf(config_path)
