import yaml
from pathlib import Path
from ..utils.exceptions import ConfigurationError


class ConfigLoader:
    @staticmethod
    def load(config_path: Path) -> dict:
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Error parsing YAML file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration file: {e}")
