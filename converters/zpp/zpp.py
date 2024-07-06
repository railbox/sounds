# pylint: disable=C0114, C0116, R0903, C0115
import wave
import os
import sys
from enum import Enum
from typing import List, Dict, Optional
from pydub import AudioSegment

class RBType(str, Enum):
    LOOP = 'LOOP'
    START = 'START'
    STOP = 'STOP'
    ON = 'ON'
    OFF = 'OFF'
    LOOPA = 'LOOPA'
    LOOPD = 'LOOPD'
    DIR = 'DIR'

class ZppType:
    UNDEFINED = 0x7F
    str_map = {
        0x1:"short whistle",
        0x2:"long whistle",
        0x3:"bell",
        0x4:"coal shovels",
        0x5:"injector",
        0x6:"air pump",
        0x7:"oil burner",
        0x8:"conductor's whistle",
        0x9:"station announcement",
        0xA:"coupling",
        0xB:"generator",
        0xC:"horn",
        0xD:"false start",
        0x80:"idle",
        0x81:"change of direction",
        0x82:"brakes squealing",
        0x83:"thyristor sound",
        0x84:"starting whistle",
        0x85:"draining",
        0x86:"e-motor sound",
        0x88:"switchgear",
        0x89:"thyristor2",
        0x8A:"panto up",
        0x8B:"panto down air",
        0x8C:"panto down impact",
        0x8D:"turbocharger",
        0x8E:"electric brake",
        0x8F:"curve screech",
        UNDEFINED:"undefined",
        0xFE:"engine",
        0xFF:"engine"
    }

    function_map = {
        0x80: 1,
        0x81: 1,
        0x84: 1,
        0x8F: 13,
        0x86: 4,

    }

    rb_type_map = {
        0x80: RBType.LOOP,
        0x81: RBType.DIR,
        0x82: RBType.STOP,
        0x84: RBType.START,
        0x86: RBType.LOOP,
    }

    def __init__(self, value: int):
        self.value = value

    def get_function_id(self) -> Optional[int]:
        return self.function_map.get(self.value, None)

    def get_rb_type(self) -> Optional[RBType]:
        return self.rb_type_map.get(self.value, None)

    def __repr__(self) -> str:
        return self.str_map.get(self.value, 'ERR')

    def __int__(self) -> int:
        return self.value

class FunctionSound:
    LOOP = 0x8
    SHORT = 0x40
    def __init__(self, func: int, vol: int, flags: int):
        if vol == 0:
            vol = 0xFF
        vol = int(vol * 100 / 0xFF)
        self.func = func
        self.vol = vol
        self.flags = flags

    def __repr__(self):
        return f"FunctionSound(id={self.func}, volume={self.vol}, flags={self.flags})"

class SpecialSound:
    BASE_TYPE = 0x80
    # pylint: disable=W0622
    def __init__(self, type: int, vol: int):
        if vol == 0:
            vol = 0xFF
        vol = int(vol * 100 / 0xFF)
        self.type = type
        self.vol = vol

    def __repr__(self) -> str:
        return f"SpecialSound(id={self.type}, volume={self.vol})"

class TapChangeSound:
    def __init__(self, tap_id: int):
        self.tap_id = tap_id

    def __repr__(self) -> str:
        return f"TapChangeSound(id={self.tap_id})"

class PeriodicSound:
    STANDING = 0x08
    MOVING = 0x40
    ALL = STANDING|MOVING
    # pylint: disable=W0622, R0913
    def __init__(self, pos: int, vol: int, flags: int, min: int, max: int, duration: int):
        if vol == 0:
            vol = 0xFF
        vol = int(vol * 100 / 0xFF)
        self.pos = pos
        self.vol = vol
        if flags & self.ALL == self.ALL:
          flags &= ~self.ALL
        self.flags = flags
        self.min = min
        self.max = max
        self.duration = duration

    def __repr__(self):
        return f"PeriodicSound(pos={self.pos}, volume={self.vol}, flags={self.flags}, \
                 min={self.min}, max={self.max}, duration={self.duration})"

class EngineSound:
    # pylint: disable=W0622, R0913
    def __init__(self, type: RBType, spd: int, period: int, idx: int = 0, vol: int = 0):
        if vol == 0:
            vol = 0xFF
        vol = int(vol * 100 / 0xFF)
        self.type = type
        self.vol = vol
        if spd > 0:
            self.spd = int(spd * 100 / 0xFF)
            if self.spd == 0:
                self.spd = 1
        else:
            self.spd = spd
        self.period = period
        self.idx = idx

class SpeedLevel:
    def __init__(self, on: int, loop: int, off: int, min_spd: int):
        self.on = on
        self.loop = loop
        self.off = off
        self.min_spd = min_spd

    def __repr__(self) -> str:
        return f"SpeedLevel({self.on},{self.loop},{self.off} from {self.min_spd})"

class SteamLevel:
    def __init__(self, high: int, mid: int, low: int, min_spd: int):
        self.high = high
        self.mid = mid
        self.low = low
        self.min_spd = min_spd

    def __repr__(self):
        return f"SteamLevel({self.high},{self.mid},{self.low} from {self.min_spd})"

class SteamMap:
    def __init__(self, chuffs: int, levels: List[SteamLevel]):
        self.chuffs = chuffs
        self.levels = levels

class WavFile:
    # pylint: disable=R0902, R0913
    def __init__(self, idx: int, levels: bytes, sample_rate: int, sample_width: int,
                 file_type: ZppType, name: str, loop_strt: int, loop_end: int):
        self.idx = idx
        self.data = levels
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.file_type = file_type
        self.name = name
        self.loop_strt = loop_strt
        self.loop_end = loop_end
        self.written = False

    def write_to_wav(self, folder_path: str, name: Optional[str] = None,
                         loop: bool = False, data: Optional[bytes] = None):
        if not name:
            name = self.name

        file_end = len(self.data) - self.sample_width
        if loop and (self.loop_strt != 0 or self.loop_end != file_end):
            #print(f"Splitting file {name} S={self.loop_strt} E={self.loop_end}<>{file_end}")
            name_split = name.split('_', 1)
            if len(name_split) == 1:
                name_split = name.rsplit('.', 1)
                name_split[1] = '.'+name_split[1]
            else:
                name_split[1] = '_'+name_split[1]
            self.write_to_wav(folder_path, f"{name_split[0]}_ON{name_split[1]}",
                                  loop=False, data=self.data[0:self.loop_strt])
            self.write_to_wav(folder_path, f"{name_split[0]}_LOOP{name_split[1]}",
                                  loop=False, data=self.data[self.loop_strt:self.loop_end])
            self.write_to_wav(folder_path, f"{name_split[0]}_OFF{name_split[1]}",
                                  loop=False, data=self.data[self.loop_end:])
            return

        file_path = os.path.join(folder_path, name)
        with wave.open(file_path, 'wb') as wav_file:
            # pylint: disable=E1101
            wav_file.setnchannels(1)
            wav_file.setsampwidth(self.sample_width)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(self.data if not data else data)
        output_path = file_path
        input_audio = AudioSegment.from_file(file_path)
        os.remove(file_path)
        output_audio = input_audio.set_channels(1).set_sample_width(2)
        if "_LOOP" in output_path:
            duration_ms = int(input_audio.duration_seconds * 1000)
            output_path = output_path.replace(".wav", f"_T{duration_ms}.wav")
        output_audio.export(output_path, format="wav", codec="adpcm_ima_wav",
                            parameters=["-ar", str(16000)])
        #print(f"{name} Created.")
        self.written = True

def create_folder_for_file(file_path: str) -> str:
    file_name = os.path.splitext(os.path.basename(file_path))[0]

    folder_path = os.path.join(os.path.dirname(file_path), file_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Folder '{file_name}' created successfully.")
    else:
        print(f"Folder '{file_name}' already exists.")
    return folder_path

def bytes2int(data: bytes, offset: int, length: int) -> int:
    return int.from_bytes(data[offset:offset+length], "little")

# pylint: disable=E1101, R0914
def parse_wav_file(data: bytes, offset: int, idx: int, file_type: ZppType) -> 'WavFile':
    flags = data[offset]
    offset += 1
    header_offset = offset
    data_end = bytes2int(data, header_offset+0, 3)
    loop_strt = bytes2int(data, header_offset+3, 3)
    loop_end = bytes2int(data, header_offset+6, 3)
    data_offset = offset + 9

    sample_rate = 11025  # in Hz ZIMO: 11, 22, 44 kHz
    sample_width = 1
    if flags & 0x80 != 0:
        sample_width = 2
    if flags & 0x04 != 0:
        sample_rate = 22050
    if flags & 0x20 != 0:
        sample_rate = 44100

    name_offset = data_end + sample_width + 2
    name_len = data[name_offset]
    name = f"{idx}"
    if name_len > 0:
        name += "-"+data[name_offset+1:name_offset+1+name_len].decode("latin-1").rstrip('\0')
    if int(file_type) != ZppType.UNDEFINED:
        name += '_'+str(file_type)
    name += ".wav"
    file_data = data[data_offset:data_end + sample_width]
    return WavFile(idx, file_data, sample_rate, sample_width,
                   file_type, name, loop_strt - data_offset, loop_end - data_offset)

def get_map_item(func_map, idx: int):
    item = func_map.get(idx, None)
    if item is None:
        item = []
        func_map[idx] = item
    return item

def parse_func_map(data: bytes, func_map: Dict[int, List['FunctionSound']],
                   offset: int, base_func: int, length: int):
    for i in range(0, length):
        addr = offset + 3*i
        if data[addr] == 0:
            continue
        func_id = base_func + i
        item = get_map_item(func_map, data[addr])
        item.append(FunctionSound(func_id, data[addr+1], data[addr+2]))

def parse_special_map(data: bytes, special_map: Dict[int, 'SpecialSound'],
                      offset: int, lenght: int):
    for i in range(0, lenght):
        addr = offset + 2*i
        idx = SpecialSound.BASE_TYPE + i
        if data[addr] != 0:
            special_map[data[addr]] = SpecialSound(ZppType(idx), data[addr+1])

def parse_periodic_map(data: bytes, periodic_map: Dict[int, 'PeriodicSound'],
                       offset: int, offset2: int, lenght: int):
    for i in range(0, lenght):
        addr = offset + 3*i
        addr2 = offset2 + 3*i
        if data[addr] != 0:
            periodic_map[data[addr]] = PeriodicSound(i, data[addr+1], data[addr+2],
                                                     data[addr2], data[addr2+1], data[addr2+2])

def parse_diesel_map(data: bytes, offset: int) -> List['SpeedLevel']:
    levels = []
    steps = data[offset]
    offset += 1

    # 0 - Hydralics(Based on target speed), 1 - Electric(Based on current speed)
    # 2 - Mechanical
    #steps_type = data[offset]

    # 0x08 - Limit CV55, 0x10 - Limit CV53 - 0x18 - Limit CV51
    #limit_type = data[offset+1]

    offset += 4
    for i in range(0, steps+1):
        addr = offset + 3*i
        if i >= 2:
            min_spd = data[offset + 0x22 + 2*(i-2)]
        else:
            min_spd = i-1
        lev = SpeedLevel(data[addr], data[addr+1], data[addr+2], min_spd)
        levels.append(lev)
    return levels

def parse_steam_map(data: bytes, offset: int) -> 'SteamMap':
    levels = []
    chuffs = data[offset]
    offset += 1

    threshold_offset = offset
    length = 0
    for i in range(1, 10):
        if data[offset] == 0xFF:
            length = i
            break
        offset += 1
    offset += 1

    for i in range(0, length):
        addr = offset+3*i
        if i != 0:
            min_spd = data[threshold_offset+i-1]
        else:
            min_spd = 1
        lev = SteamLevel(data[addr], data[addr+1], data[addr+2], min_spd)
        levels.append(lev)
    return SteamMap(chuffs, levels)

def parse_tap_charger(data: bytes, tap_change_map: Dict[int, 'TapChangeSound'], offset: int):
    length = data[offset]
    offset += 1
    #End file data[offset+4]

    offset += 5
    for i in range(0, length):
        addr = offset + i
        tap_change_map[data[addr]] = TapChangeSound(i)

def get_full_name(name: str, vol: int = 0) -> str:
    if vol not in (100, 0):
        name += "_V"+str(vol)
    name += '.wav'
    return name

def main(argv):
    # pylint: disable=R0914, R0912, R0915, R1702
    input_file_name = argv[0]

    if getattr(sys, 'frozen', False):
        # If the script is running as a bundled executable (e.g., PyInstaller)
        script_dir = os.path.dirname(sys.executable)
        os.environ['PATH'] += os.pathsep + f"{script_dir}\\_internal"

    print(input_file_name)
    folder_path = create_folder_for_file(input_file_name)
    unused_folder_path = os.path.join(folder_path, "unused")
    if not os.path.exists(unused_folder_path):
        os.makedirs(unused_folder_path)

    # Read raw data from the file ########################################
    with open(input_file_name, 'rb') as raw_file:
        data = raw_file.read()
    # Remove 0x80 of file header
    data = data[0x80:]

    prj_name_len = data[0xA00]
    data_base = 0xA00 + prj_name_len + 1

    # CV Table
    # data_base -> data_base + 0x3FF

    # Steam scheme parsing ############################################
    offset = 0x800
    engine_scheme = None
    for i in range(0, 3):
        address = offset + 2*i
        steam_table_offset = int.from_bytes(data[offset:offset+2], "big")
        if steam_table_offset != 0:
            if i != 0:
                print(f"Got steam map {i}")
            else:
                engine_scheme = parse_steam_map(data, steam_table_offset)

    # Diesel scheme parsing ###########################################
    offset = 0x840
    for i in range(0, 3):
        address = offset + 2*i
        diesel_table_offset = int.from_bytes(data[address:address+2], "big")
        if diesel_table_offset != 0:
            if i != 0:
                print(f"Got diesel map {i}")
            else:
                engine_scheme = parse_diesel_map(data, diesel_table_offset)

    #offset = 0x8E0

    # Tap changer parsing ################################################
    offset = 0x920
    tap_changer_map = {}
    for i in range(0, 3):
        address = offset + 2*i
        tap_changer_offset = int.from_bytes(data[address:address+2], "big")
        if tap_changer_offset != 0:
            if i != 0:
                print(f"Got tap changer map {i}")
            else:
                parse_tap_charger(data, tap_changer_map, tap_changer_offset)

    engine_map = {}
    if isinstance(engine_scheme, SteamMap):
        print(f"Steam map: Chuffs={engine_scheme.chuffs} Levels={len(engine_scheme.levels)}")
        for lev in engine_scheme.levels:
            if lev.high != 0:
                for idx in range(0, engine_scheme.chuffs):
                    item = get_map_item(engine_map, lev.high+idx)
                    item.append(EngineSound(RBType.LOOPA, lev.min_spd, 1000 if idx==0 else -1, idx))
            if lev.mid != 0:
                for idx in range(0, engine_scheme.chuffs):
                    item = get_map_item(engine_map, lev.mid+idx)
                    item.append(EngineSound(RBType.LOOP, lev.min_spd, 1000 if idx==0 else -1, idx))
            if lev.low != 0:
                for idx in range(0, engine_scheme.chuffs):
                    item = get_map_item(engine_map, lev.low+idx)
                    item.append(EngineSound(RBType.LOOPD, lev.min_spd, 1000 if idx==0 else -1, idx))
            print(lev)
    elif engine_scheme:
        print(f"Diesel map: Levels={len(engine_scheme)}")
        for lev in engine_scheme:
            if lev.on != 0:
                item = get_map_item(engine_map, lev.on)
                item.append(EngineSound(RBType.ON, lev.min_spd, 0))
            if lev.loop != 0:
                item = get_map_item(engine_map, lev.loop)
                item.append(EngineSound(RBType.LOOP, lev.min_spd, 0))
            if lev.off != 0:
                item = get_map_item(engine_map, lev.off)
                item.append(EngineSound(RBType.OFF, lev.min_spd, 0))
            print(lev)

    # Function mapping parsing ###########################################
    func_map = {}
    parse_func_map(data, func_map, 0x239+data_base, 0, 1)  #F0
    parse_func_map(data, func_map, 0x200+data_base, 1, 19) #F1 - F19
    parse_func_map(data, func_map, 0x2A0+data_base, 20, 9) #F20 - F28

    # Periodic parsing ###################################################
    periodic_map = {}
    parse_periodic_map(data, periodic_map, 0x2E7+data_base, 0x13A+data_base, 8)

    # Special sounds parsing #############################################
    special_map = {}
    parse_special_map(data, special_map, 0x23C+data_base, 16)

    # File table parsing #################################################
    virtual_function_pos = 63
    logic_lines = []
    file_map = {}
    # 256 - 512 built it files
    for idx in range(1, 256):
        off = (idx - 1) * 4
        file_type = ZppType(data[off])
        offset = int.from_bytes(data[off+1:off+4], "big")
        if offset == 0:
            continue
        dublicate = file_map.get(offset, None)
        if dublicate:
            file_map[idx] = dublicate
            continue
        file_map[idx] = parse_wav_file(data, offset, idx, file_type)

    for idx, wav_file in file_map.items():
        func_list = func_map.get(idx, None)
        if func_list:
            for item in func_list:
                loop = item.flags & FunctionSound.LOOP != 0
                if int(wav_file.file_type) != ZppType.UNDEFINED:
                    file_name = get_full_name(f"F{item.func}_{wav_file.file_type}", item.vol)
                else:
                    file_name = get_full_name(f"F{item.func}", item.vol)
                wav_file.write_to_wav(folder_path, file_name, loop=loop)

        special_type = special_map.get(idx, None)
        if special_type:
            file_type = str(wav_file.file_type)
            rb_type = special_type.type.get_rb_type()
            if rb_type:
                wav_file.file_type = rb_type
            func_id = special_type.type.get_function_id()
            if rb_type and not func_id:
                func_id = 1
            if func_id:
                file_name = get_full_name(f"F{func_id}_{rb_type}", special_type.vol)
                wav_file.write_to_wav(folder_path, file_name)

            if not wav_file.written:
                print(f"  Special type={special_type.type}, vol={special_type.vol}")

        periodic_type = periodic_map.get(idx, None)
        if periodic_type:
            virtual = False
            periodic_func = None
            if func_list:
                periodic_func = func_list[0].func
            if not periodic_func:
                virtual = True
                periodic_func = virtual_function_pos
                virtual_function_pos -= 1
            duration_ms = periodic_type.duration * 1000
            logic_line = f"F{periodic_func}_RAND_S{periodic_type.min}_E{periodic_type.max}\
                _L{duration_ms}"
            if periodic_type.flags & PeriodicSound.MOVING != 0:
              logic_line += "_INMOVE"
            if periodic_type.flags & PeriodicSound.STANDING != 0:
              logic_line += "_INSTOP"
            logic_lines.append(logic_line)
            if virtual:
                wav_file.write_to_wav(folder_path, get_full_name(f"F{periodic_func}"))

        tap_changer_type = tap_changer_map.get(idx, None)
        if tap_changer_type:
            wav_file.write_to_wav(unused_folder_path)

        engine_type_list = engine_map.get(idx, None)
        if engine_type_list:
            for engine_type in engine_type_list:
                if engine_type.spd >= 0 or engine_type.period != 0:
                    if engine_type.period == 0:
                        if engine_type.spd > 0 and engine_type.spd < 3:
                            print(f"Skip speed {engine_type.spd}")
                            continue
                        if engine_type.spd == 0:
                            engine_type.spd = 1
                        file_name = get_full_name(f"F1_{engine_type.type}_S{engine_type.spd}",
                                                  engine_type.vol)
                        wav_file.write_to_wav(folder_path, file_name)
                    else:
                        period_str = str(engine_type.period) if engine_type.period > 0 else 'x'
                        file_name = get_full_name(f"F1_{engine_type.type}{engine_type.idx+1}"+
                                                  f"_S{engine_type.spd}_P{period_str}",
                                                  engine_type.vol)
                        wav_file.write_to_wav(folder_path, file_name)
                else:
                    file_name = get_full_name(f"F1_{engine_type.type}_S0", engine_type.vol)
                    wav_file.write_to_wav(folder_path, file_name)

        if not wav_file.written:
            wav_file.write_to_wav(unused_folder_path)
            print(f"Name={wav_file.name} Bits={wav_file.sample_width*8}"+
                  f" Rate={wav_file.sample_rate}Hz Type={wav_file.file_type}")

        with open(os.path.join(folder_path, 'logic.txt'), 'w', encoding='utf-8') as file:
            for line in logic_lines:
                file.write(line + '\n')

if __name__ == "__main__":
    main(sys.argv[1:])
