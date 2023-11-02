import json
import os
import re
from datetime import datetime

def slugify(text):
    return re.sub(r'\W+', '-', text).strip('-').lower()


def write_to_json(json_data, output_dir, filename, add_timestamp=True):
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    time_in_str = f'_{datetime.now().strftime("%Y-%m-%d-%H-%M-%S")}' if add_timestamp else ""
    file_path = os.path.join(
        output_dir, f"{slugify(filename)}{time_in_str}.json"
    )
    with open(file_path, "w") as json_file:
        json.dump(json_data, json_file, indent=4)
    return file_path
