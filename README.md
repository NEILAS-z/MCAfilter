# MCAfilter
Filters MCA (Minecraft Anvil Format) for blocks using multithreading and outputs it to a json file

No need for any libraries, everything is written without any dependances being needed besides
from the standard python librarys (but they are already pre-installed)

Takes ~1.4 seconds to parse one MCA file with 4 threads and filtering for `minecraft:deepslate_diamond_ore`
on a `Ryzen 5 5600G`

# `Usage:`

python main.py [-h] -f FILE -b BLOCK [-t THREADS] [-d]

options:

-h, --help | show this help message and exit

-f, --file FILE | Path to region file or folder full of region files

-b, --block BLOCK | Block to filter for. example: minecraft:deepslate_diamond_ore

-t, --threads THREADS | How many threads to read in parallel? (default: 4)

-d, --bDetail | Should the block Name/Properties be shown in the output.json? (default: False)

------
**Warning**: expect the json file to be >6 MB for a single region file and a ore, if your importing a large world, have patience.
the code is designed to always show logs and be very verbose.

**Known Issues**:
- The code doesnt output working JSON for multiple MCA files.
- The threads arent split along multiple MCA files. but rather split in one MCA file.
- Some sort of optimization can be done with reading chunks. but im confused, please post a `Pull request` if you know the issue, thanks!
