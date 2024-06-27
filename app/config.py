import configparser
from dotenv import dotenv_values

def read_config(profile='DEFAULT'):
    config = configparser.ConfigParser()
    config.read('config.ini')

    return config[profile]

# Get the current profile from an environment variable or default to 'DEFAULT'
env = dotenv_values(".env")
config = read_config(env.get("PROFILE", "DEFAULT"))
