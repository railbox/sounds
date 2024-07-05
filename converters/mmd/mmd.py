# pylint: disable=C0103, C0114, C0115, C0116, C0301

import re
import os
import sys
import shutil
from pydub import AudioSegment

sound_pattern = r'sound(\d+|begin|end|main):\s*([^\s]+)'
block_pattern = r'([\w-]+):\s*\{([^}]+)\}'
old_pattern = r'([\w-]+): ([^:|]+?) ([^:|]+?) ([^:|]+?) '
soundset_pattern = r'soundset:\s*\[ (.*?) \]'
include_pattern = r'include\s*\[ (.*?) \]'
include_pattern2 = r'include ([^\[\]]*?) end'
comment_pattern = re.compile(r'//.*')

function_ids = {
    "tractionmotor": 1,
    "engine": 4,
    "ventilator": 4,

    "ignition": 1,
    "brake": 1,
    "unbrake": 1,

    "horn1": 2,
    "horn2": 3,
    "horn3": 5,
    "curve": 13,
    "compressor": 17,
    "small-compressor": 19,
    "oilpump": 19,
    #"converter": -1, ???
    "pantographup": 24,
    "pantographdown": 24,
    "sand": 21,
    "releaser": 9, #???
}
max_values = {
    "tractionmotor": 1000,
    "engine": 1000,
    "ventilator": 1000,
    "curve": 100,
    "brake": 200,
}

block_type = {
    "ignition": "ON",
    "brake": "STOP",
    "unbrake": "START",
    "pantographup": "ON",
    "pantographdown": "OFF"
}

class Item:
    # pylint: disable=R0903
    def __init__(self, start_speed, file_name, on_file_name="", off_file_name=""):
        self.file_name = file_name
        self.on_file_name = on_file_name
        self.off_file_name = off_file_name
        self.start_speed = start_speed
        self.end_speed = None

database = {}
crossfades = {}
placements = {}

def replace_extension(filename):
    if not filename:
        return ""
    root, ext = os.path.splitext(filename)
    if ext.lower() == ".ogg":
        return filename
    return root + ".ogg"

def parse_item(block_name, type_value, file_name, on_file_name="", off_file_name=""):
    block_db = database.get(block_name)
    if block_db is None:
        block_db = []
    max_value = max_values.get(block_name, 100)

    file_name = replace_extension(file_name)
    on_file_name = replace_extension(on_file_name)
    off_file_name = replace_extension(off_file_name)

    if type_value == "main":
        if "silence" in file_name:
            return
        block_db.append(Item(None, file_name, on_file_name, off_file_name))
    else:
        orig_value = int(type_value)
        value = int((orig_value * 100 + max_value / 2) / max_value)
        if orig_value != 0 and value == 0:
            value = 1
        if "silence" in file_name:
            if orig_value != 0 and len(block_db) and value != 100:
                # pylint: disable=W0511
                #TODO
                last_item = block_db[-1]
                last_item.end_speed = value
            return
        block_db.append(Item(value, file_name))

    database[block_name] = block_db

def process_file(original_path, output_path, otype):
    if not os.path.exists(original_path):
        print(f"    ERROR: File {original_path} is not exists")
        return
    input_audio = AudioSegment.from_ogg(original_path)
    output_audio = input_audio.set_channels(1).set_sample_width(2)
    if "adpcm" in otype:
        if "_LOOP" in output_path:
            duration_ms = int(input_audio.duration_seconds * 1000)
            output_path = output_path.replace(".ogg", f"_T{duration_ms}.wav")
        else:
            output_path = output_path.replace(".ogg", ".wav")
    print(f"    '{os.path.basename(original_path)}' -> {os.path.basename(output_path)}")
    if "adpcm" in otype:
        output_audio.export(output_path, format="wav", codec="adpcm_ima_wav", parameters=["-ar", str(16000)])
    else:
        output_audio.export(output_path, format="ogg", parameters=["-ar", str(32000)])

def load_include(file_name, data):
    try:
        with open(file_name, 'r', encoding="utf-8", errors='ignore') as file:
            if isinstance(data, list):
                for line in file:
                    data.append(line.rstrip())
            else:
                for line in file:
                    data += line
    except FileNotFoundError:
        pass
    except UnicodeDecodeError as e:
        print(f"Error decoding file {file_name}: {e}")
    except PermissionError as e:
        print(f"Permission error accessing file {file_name}: {e}")

    return data

def parse_mmd(path, otype, sounds_path, output_path):
    # pylint: disable=R0912, R0914, R0915
    full_data = []
    data = ""

    shutil.rmtree(output_path)
    os.makedirs(output_path)

    #Capture sounds: section
    inside_sounds_section = False
    inside_include = False
    with open(path, 'r', encoding="utf-8") as file:
        for line in file:
            # Remove any comments
            line = comment_pattern.sub('', line).strip()
            if "include " in line:
                inside_include = True
            if inside_include and "end" in line:
                inside_include = False
                if not "include " in line:
                    continue
            if inside_include:
                inc_split = line.split()
                for inc in inc_split:
                    if not "include" in inc:
                        full_data = load_include(inc, full_data)
            else:
                full_data.append(line+"\n")

    for line in full_data:
        if "sounds:" in line:
            inside_sounds_section = True
            continue

        if "endsounds" in line:
            inside_sounds_section = False

        if inside_sounds_section:
            data += line
        #Add additional blocks outside of sounds
        if "ignition:" in line:
            data += line

    #Load includes #############################################################
    for match in re.finditer(include_pattern, data, re.DOTALL):
        include_list = match.group(1).split(' ')
        for item in include_list:
            data = load_include(item, data)
    for match in re.finditer(include_pattern2, data, re.DOTALL):
        inc_file = match.group(1)
        data = load_include(inc_file, data)

    #Parse data ################################################################
    for match in re.finditer(block_pattern, data):
        block_name = match.group(1)
        function_id = function_ids.get(block_name)
        if function_id is None:
            continue
        block_content = match.group(2)

        # Extract the crossfade value
        crossfade_match = re.search(r'crossfade:\s*(\d+)', block_content)
        crossfade = crossfade_match.group(1) if crossfade_match else "0"
        crossfades[block_name] = int(crossfade)

        # Extract the placement value
        placement_match = re.search(r'placement:\s*(\w+)', block_content)
        placement = placement_match.group(1) if placement_match else ""
        placements[block_name] = placement

        # Extract sound information
        sound_matches = re.findall(sound_pattern, block_content)
        sound_on = ""
        sound_loop = ""
        sound_off = ""
        for file_type, file_name in sound_matches:
            if "begin" in file_type:
                sound_on = file_name
            elif "end" in file_type:
                sound_off = file_name
            elif "main" in file_type:
                sound_loop = file_name
            else:
                parse_item(block_name, file_type, file_name)
        if sound_loop:
            parse_item(block_name, 'main', sound_loop, sound_on, sound_off)

        set_matches = re.search(soundset_pattern, block_content, re.DOTALL)
        if set_matches:
            set_list = set_matches.group(1).split(',')
            for items in set_list:
                item_list = items.replace(' ', '').split('|')
                if len(item_list) >= 3:
                    parse_item(block_name, 'main', item_list[1], item_list[0], item_list[2])
                else:
                    print(set_matches.group(1))

    for match in re.finditer(old_pattern, data):
        block_name = match.group(1)
        function_id = function_ids.get(block_name)
        if function_id is None:
            continue
        file1 = match.group(2)
        file2 = match.group(3)
        file3 = match.group(4)
        if "ogg" in file2:
            parse_item(block_name, 'main', file2, file1, file3)
        else:
            parse_item(block_name, 'main', file1)

    for block_name in database:
        block = database.get(block_name)
        function_id = function_ids.get(block_name)
        print(f"Block name: {block_name}({function_id})")

        new_name = None
        if block_name == "brake":
            for idx, item in enumerate(block):
                new_name = f"F{function_id}_STOP_{block_name}_spd{item.start_speed}.ogg"
                process_file(os.path.join(sounds_path, item.file_name), os.path.join(output_path, new_name), otype)
        else:
            idx = 0
            for idx, item in enumerate(block):
                if idx != 0:
                    idx_str = f"_#{idx}"
                else:
                    idx_str = ""
                if item.start_speed is None:
                    if item.on_file_name:
                        new_name = f"F{function_id}{idx_str}_ON_{block_name}.ogg"
                        process_file(os.path.join(sounds_path, item.on_file_name), os.path.join(output_path, new_name), otype)
                    if item.off_file_name:
                        new_name = f"F{function_id}{idx_str}_OFF_{block_name}.ogg"
                        process_file(os.path.join(sounds_path, item.off_file_name), os.path.join(output_path, new_name), otype)
                    new_name = f"F{function_id}{idx_str}_LOOP_{block_name}.ogg"
                elif item.end_speed is None:
                    new_name = f"F{function_id}_LOOP_S{item.start_speed}_{block_name}.ogg"
                else:
                    new_name = f"F{function_id}_LOOP_S{item.start_speed}_E{item.end_speed}_{block_name}.ogg"
                if block_name in placements:
                    placement = placements[block_name]
                    if "engine" in placement:
                        new_name = new_name.replace(".ogg", "_ENG.ogg")
                    if "internal" in placement:
                        print(f"    Skipping file {item.file_name} as in have INTERNAL placecement")
                        continue
                if not item.file_name:
                    print(f"    ERROR: file {item.file_name}")
                    continue
                process_file(os.path.join(sounds_path, item.file_name), os.path.join(output_path, new_name), otype)


def main(argv):
    if len(argv) < 3:
        print("ERROR: File path is not profided usage:\nmmd.py <Path to simulator sound files> <output_type> <mmd file path>")
        sys.exit(1)

    sounds_path = argv[0]
    otype = argv[1]
    mmd_path = argv[2]

    mmd_name = os.path.splitext(os.path.basename(mmd_path))[0]
    if getattr(sys, 'frozen', False):
        # If the script is running as a bundled executable (e.g., PyInstaller)
        script_dir = os.path.dirname(sys.executable)
        os.environ['PATH'] += os.pathsep + f"{script_dir}\\_internal"
    else:
        # If the script is running as a normal Python script
        script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, mmd_name)
    os.makedirs(output_path, exist_ok=True)

    parse_mmd(mmd_path, otype, sounds_path, output_path)


if __name__ == "__main__":
    main(sys.argv[1:])
