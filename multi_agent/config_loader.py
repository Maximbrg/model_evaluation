import yaml

def load_config(file_path="config.yaml"):
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: {file_path} not found. Please create it using config.yaml as an example.")
        return {}
