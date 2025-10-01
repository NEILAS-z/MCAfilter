import argparse
import os.path
import sys
import json
import time
import zlib
import struct
from multiprocessing import Process, Value, Manager, Lock

def TAG_Byte_Array(d, skip):
    size = int.from_bytes(d[0:4], signed=True)
    if skip:
        return 4 + size
    arr = []
    for i in range(0, size, 1):
        arr.append(d[i + 4])
    return (arr, 4 + size)

def TAG_Int_Array(d, skip):
    size = int.from_bytes(d[0:4], signed=True)
    if skip:
        return 4 + size*4
    arr = []
    for i in range(0, size, 1):
        arr.append(int.from_bytes(d[(i*4 + 4) : (i*4 + 8)]))
    return (arr, 4 + size*4)

def TAG_Long_Array(d, skip):
    size = int.from_bytes(d[0:4], signed=True)
    if skip:
        return 4 + size*8
    arr = []
    for i in range(0, size, 1):
        arr.append(int.from_bytes(d[(i*8 + 4) : (i*8 + 4 + 8)]))
    return (arr, 4 + size*8)

def TAG_String(d, skip):
    size = int.from_bytes(d[0:2])
    if skip:
        return size + 2
    string = d[2:2+size].decode()
    return (string, size + 2)

def TAG_List(d, skip):
    TAG_ID = d[0]
    size = int.from_bytes(d[1:5])
    arr = []
    seek = 5
    if size == 0:
        if skip:
            return seek
        return ([], seek)
    if TAG_ID == 0:
        if skip:
            return seek + size
        return ([0]*size, seek + size)
    for i in range(0, size, 1):
        data, seekoff = read[TAG_ID](d[seek:], False)
        seek += seekoff
        arr.append(data)
    if skip:
        return seek
    return (arr, seek)

def TAG_Compound(d, skip):
    seek = 0
    compound_dict = {}
    while True:
        tag_id = d[seek]
        if tag_id == 0:
            seek += 1
            break
        seek += 1  # move past the id
        NameLength = int.from_bytes(d[seek:seek+2])
        seek += 2  # move past the name length
        if not skip:
            tagName = d[seek:seek+NameLength].decode()
        seek += NameLength
        if skip:
            seek += read[tag_id](d[seek:], True)
            continue
        if tagName in ("xPos","zPos","Y", "sections", "block_states", "palette", "data", "Name", "Properties", "Status"):
            data, offseek = read[tag_id](d[seek:], False)
            compound_dict[tagName] = data
            seek += offseek  # data
        else:
            seek += read[tag_id](d[seek:], True)
    if skip:
        return seek
    return (compound_dict, seek)

# functions to read specific tags and output
read = {
    1: lambda d, skip: 1 if skip else ( d[0] if d[0] < 128 else d[0] - 256,1),  # TAG_Byte
    2: lambda d, skip: 2 if skip else (int.from_bytes(d[0:2], signed=True), 2), # TAG_Short
    3: lambda d, skip: 4 if skip else (int.from_bytes(d[0:4], signed=True), 4), # TAG_Int
    4: lambda d, skip: 8 if skip else (int.from_bytes(d[0:8], signed=True), 8), # TAG_Long
    5: lambda d, skip: 4 if skip else (struct.unpack('f', d[0:4]), 4),          # TAG_Float
    6: lambda d, skip: 8 if skip else (struct.unpack('d', d[0:8]), 8),          # TAG_Double
    7: TAG_Byte_Array,
    8: TAG_String,
    9: TAG_List,
    10: TAG_Compound,
    11: TAG_Int_Array,
    12: TAG_Long_Array
}


# returns a dictionary
def ParseNBT(data) -> list:
    dictr = []
    seek = 0
    TagID = data[seek]
    seek += 1
    TagNameLength = int.from_bytes(data[seek:seek+2])
    seek += 2
    if not TagNameLength == 0:
        seek += TagNameLength
    (d, offseek) = read[TagID](data[seek:], False)
    seek += offseek
    dictr.append(d)
    return dictr

def ReadChunk(uncomressed_ch_data, block, showBlock):
    chk_data = ParseNBT(zlib.decompress(uncomressed_ch_data))[0]

    chkX = chk_data["xPos"]
    chkZ = chk_data["zPos"]
    if chk_data["Status"] != "minecraft:full":
        return ([], 0)

    chkblocks = []

    blocks_found = 0

    for section in chk_data["sections"]:
        if not 'block_states' in section:
            continue
        sectionY = section["Y"] * 16
        block_states = section["block_states"]
        blocks = block_states["palette"]

        # filter for the block we want
        filterIdx = 0
        found = False
        for blx in blocks:
            if blx["Name"] == block:
                found = True
                break
            filterIdx += 1

        if not found:
            # its not in the section palette, skip
            continue

        if len(blocks) == 1:
            if 0 != filterIdx:
                continue
            arr = [[blocks[0], i%16, (i//16)%16, i//256] for i in range(16**3)]
            blocks_found += 16**3
            chkblocks.extend(arr)
            continue
        bits = max(4, (len(blocks)-1).bit_length())
        idx = 0
        for data in block_states["data"]:
            packedData = int(data)
            for i in range(64//bits):
                blockIdx = (packedData >> (i * bits)) & ((1 << bits) - 1)
                if blockIdx != filterIdx:
                    continue
                blocks_found += 1
                sblock = blocks[blockIdx]
                x = i
                y = idx//16
                z = idx%16

                x += chkX * 16
                y += sectionY
                z += chkZ * 16
                if showBlock:
                    chkblocks.append([sblock, x, y, z])
                else:
                    chkblocks.append([x, y, z])
            idx += 1
    return (chkblocks, blocks_found)

def ReadChunks(seekPositions, file, output, i, block, lock, done_chunks, showblock, total_chunks, verbose):
    chunks = []
    amount = 0
    with open(file, "rb") as f:
        for ch_offset in seekPositions:
            f.seek(ch_offset * 4096)
            length = int.from_bytes(f.read(4))
            f.seek((ch_offset * 4096) + 4)

            compress_type = int.from_bytes(f.read(1))
            f.seek((ch_offset * 4096) + 5)
            if compress_type == 1:
                if verbose:
                    print("Unsupported Compression type: GZip")
                continue
            if compress_type == 3:
                if verbose:
                    print("Unsupported Compression type: Uncompressed, are you loading a <1.15.1 region file?")
                continue
            if not compress_type == 2:
                if verbose:
                    print("Unsupported Compression type: Unknown, is your region file corrupted? Compression Type:", compress_type)
                continue
            
            chkblocks, blocks = ReadChunk(f.read(length-1), block, showblock)
            chunks.append(chkblocks)
            amount += blocks
            if verbose:
                with lock:
                    done_chunks.value += 1
                    print(f"Thread {i} done, {done_chunks.value} / {total_chunks} | found {blocks} in chunk")

    output[i * 2] = chunks
    output[(i * 2) + 1] = amount

if __name__ == "__main__":
    done_chunks = Value("i", 0)
    lock = Lock()
    def chunks(lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
    
    total_chunks = 1024

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, required=True, help="Path to region file or folder full of region files")
    parser.add_argument("-b","--block", type=str, required=True, help="Block to filter for. example: minecraft:deepslate_diamond_ore")
    parser.add_argument("-t","--threads", type=int, required=False, default=4, help="How many threads to read in parallel? (default: 4)")
    parser.add_argument("-d","--bDetail", required=False, action="store_true", default=False, help="Should the block Name/Properties be shown in the output.json? (default: False)")
    parser.add_argument("-v", "--verbose", required=False, action="store_true", default=False, help="Logs more info when filtering blocks.")
    args = parser.parse_args()

    threads = args.threads

    with open("output.json", "w") as js:
        js.write("")  # remove data

    def readmca(path):
        with open(path, "rb") as f:
            locations = f.read(4096)
            f.seek(4096)
            timestamps = f.read(4096)

            ch_offsets = []
            ch_timestamps = []

            for i in range(1024):
                ch_offsets.append(int.from_bytes(locations[i * 4:(i * 4)+3]))
            for i in range(1024):
                ch_timestamps.append(int.from_bytes(timestamps[i * 4:(i * 4)+4]))

            blocks_found = 0
            chk_read = 0

            workflow = list(chunks(ch_offsets, 1024 // threads))

            manager = Manager()
            output = manager.list([manager.list() for _ in range(len(workflow * 2))])

            processes = []
            for i, chunk_offsets in enumerate(workflow):
                p = Process(target=ReadChunks, args=(chunk_offsets, path, output, i, args.block, lock, done_chunks, args.bDetail, total_chunks, args.verbose))
                processes.append(p)
                if args.verbose:
                    print(f"Dispatched thread {i}")
                p.start()
            
            for p in processes:
                p.join()

            total_blocks = 0
            blocks = []
            for i in range(len(workflow)):
                total_blocks += output[(i * 2) + 1]
                blocks.append(output[i*2])
            print("total blocks:", total_blocks)
            with open("output.json", "a") as js:
                js.write(json.dumps(blocks, indent=2))

    folder = False

    if not os.path.isfile(args.file):
        if not os.path.isdir(args.file):
            print(sys.argv[0] + ": error: the file / folder doesnt exist")
            quit(1)
        else:
            folder = True
    
    path = args.file

    mca_files = []
    if folder:
        for fname in os.listdir(path):
            if fname.endswith(".mca"):
                mca_files.append(os.path.join(path, fname))
    else:
        mca_files.append(path)

    total_chunks = len(mca_files * 1024)

    print(f"Found {len(mca_files)} region file(s)")
    start = time.perf_counter()
    for f in mca_files:
        print("Reading", f + "...")
        readmca(f)
    print("Took", time.perf_counter() - start, "seconds")
    
