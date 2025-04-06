import json


def write_json(json_data, file_path):
    with open(file_path, "w") as f:
        json.dump(json_data, f, indent=4)


def read_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)
