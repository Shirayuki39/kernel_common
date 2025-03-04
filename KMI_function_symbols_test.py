#!/usr/bin/env python3
# encoding: utf-8

import os
import sys
import re
import itertools
from typing import Final

from lxml import etree
from rich.console import Console
from rich.table import Table


__author__: Final = "Pzqqt"

LOCAL_DIR: Final = os.path.dirname(os.path.abspath(__file__))


def crc_to_int(crc: str) -> int:
    assert isinstance(crc, str)
    if re.match(r'0x[0-9a-fA-F]+', crc):
        return int(crc[2:], 16)
    raise ValueError(crc)

def int_to_crc(num: int) -> str:
    assert isinstance(num, int)
    return '0x' + hex(num)[2:].zfill(8)

def main(abi_gki_aarch64_xml_file: str, vmlinux_symvers_file: str) -> int:
    assert os.path.isfile(abi_gki_aarch64_xml_file)
    assert os.path.isfile(vmlinux_symvers_file)

    with open(abi_gki_aarch64_xml_file, 'r', encoding="utf-8") as f:
        xml_obj = etree.XML(f.read())
        abi_gki_aarch64_elf_symbols = {
            elf_symbol.get("name"): crc_to_int(elf_symbol.get("crc"))
            for elf_symbol in itertools.chain(
                xml_obj.findall('.//elf-function-symbols/elf-symbol'),
                xml_obj.findall('.//elf-variable-symbols/elf-symbol'),
            )
        }

    with open(vmlinux_symvers_file, 'r', encoding="utf-8") as f:
        vmlinux_symvers = {
            line.split()[1]: crc_to_int(line.split()[0]) for line in f.readlines()
        }

    if missing_symbols := abi_gki_aarch64_elf_symbols.keys() - vmlinux_symvers.keys():
        print("Warning: The kernel image is missing the following symbols:")
        for symbol in missing_symbols:
            print('-', symbol)

    diff_crc_items = [
        (key, abi_gki_aarch64_elf_symbols[key], vmlinux_symvers[key])
        for key in abi_gki_aarch64_elf_symbols.keys() & vmlinux_symvers.keys()
        if abi_gki_aarch64_elf_symbols[key] != vmlinux_symvers[key]
    ]

    if not diff_crc_items:
        print("No mismatching crc values found. Good job!")
        return 0

    rich_console = Console()

    rich_table = Table(show_header=True, header_style="bold magenta")
    rich_table.add_column("Function/variable symbol", style="dim")
    rich_table.add_column("Crc from abi_gki_aarch64.xml")
    rich_table.add_column("Crc from vmlinux.symvers")
    for item in diff_crc_items:
        rich_table.add_row(item[0], int_to_crc(item[1]), int_to_crc(item[2]))

    rich_console.print(rich_table)

    print("Found %d function/variable symbol(s) with mismatched crc values!" % len(diff_crc_items))
    return 1

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.exit(main(
            os.path.join(LOCAL_DIR, 'android', 'abi_gki_aarch64.xml'),
            os.path.join(LOCAL_DIR, 'out', 'vmlinux.symvers')
        ))
    if len(sys.argv) == 3:
        sys.exit(main(sys.argv[1], sys.argv[2]))
    print('Usage: %s <abi_gki_aarch64.xml file> <vmlinux.symvers file>' % sys.argv[0])
    sys.exit(2)
