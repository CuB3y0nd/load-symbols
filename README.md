# :spider_web: load-symbols

*A tiny GDB plugin that bravely ventures into the filesystem to bring you debug symbols from the depths of your `.debug` directories.*

## :thinking: What is this?

`load-symbols` is a lightweight, no-nonsense GDB Python command that iterative loads symbol files from a directory and its subdirectories.

Got a pile of `.debug`, `.so`, or `.sym` files scattered like socks after laundry day? Let `load-symbols` pick them up and hand them to GDB like a loyal assistant with obsessive-compulsive tendencies.

## :thought_balloon: Inspired by

Your overflowing `/glibc` folder and the eternal struggle of:

> "Why is GDB not showing any function names again?!"

Also, `gdb` can only load symbol file one by one through `add-symbol-file`, which is super low-efficiency.

## :dart: Features

- Load single debug symbol
- Iterative walks directories like a bloodhound
- Loads `.debug`, `.so`, `.sym` etc. symbol files into GDB
- Gives you colorful, pwndbg-style, comforting output (debugging is painful enough already)
- Gracefully handles bad paths and unreadable files
- Won't judge your folder structure

## :bookmark: Installation

```bash
git clone https://github.com/CuB3y0nd/load-symbols.git ~/load-symbols
echo "source ~/load-symbols/load-symbols.py" >> ~/.gdbinit
```

## :boom: Disclaimer

Do whatever you want with it. Just don't blame me if it loads the wrong symbols and your debugger starts quoting Nietzsche.

*Have phun!*
