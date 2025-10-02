# MCAfilter
Filters MCA (Minecraft Anvil Format) for blocks using multithreading and outputs it to a json file

No need for any libraries, everything is written without any dependencies being needed besides
from the standard python libraries (but they are already pre-installed)

Takes ~1.1 seconds to parse one, fully loaded MCA file with 4 threads (Ryzen 5 5600G, SSD) and filtering for `minecraft:deepslate_diamond_ore`

1 MCA file = 32x32 chunks

# `Usage`:

```bash
python main.py [-h] -f FILE -b BLOCK [-t THREADS] [-d] [-v]
```

Options:

-h, --help | show this help message and exit

-f, --file FILE | Path to region file or folder full of region files

-b, --block BLOCK | Block to filter for. example: minecraft:deepslate_diamond_ore

-t, --threads THREADS | How many threads to read in parallel? (default: 4)

-d, --bDetail | Should the block Name/Properties be shown in the output.json? (default: False)

-v, --verbose | Logs more info when filtering blocks.

**Example**:
```bash
python main.py -f r.0.0.mca -b minecraft:barrel -t 8 -d -v
```

------
**Warning**: expect the json file to be >6 MB for a single region file and an ore,
if your importing a large world, have patience.
The code is designed to always show logs and be very verbose.

**Known Issues**:
- The code doesn’t output working JSON for multiple MCA files.
- The threads aren't split along multiple MCA files. but rather split in one MCA file.
- Some sort of optimization can be done with reading chunks. but im confused, please post a `pull request` if you know the issue, thanks!
