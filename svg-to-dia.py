#!/usr/bin/env python3
# This is free and unencumbered software released into the public domain.

from argparse import ArgumentParser
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
import getpass
import subprocess

# Control the verbosity of the output
verbose_print = None

@dataclass
class Sheet:
    name: str
    author: str
    description: str
    objects: dict


def build_sheet(sheet):
    xsheet = ET.Element(
        'sheet',
        attrib={'xmlns': 'http://www.lysator.liu.se/~alla/dia/dia-sheet-ns'}
    )
    if sheet.name:
        ET.SubElement(xsheet, 'name').text = sheet.name
    if sheet.author:
        ET.SubElement(xsheet, 'created_by').text = sheet.author
    if sheet.description:
        ET.SubElement(xsheet, 'description').text = sheet.description

    xcontents = ET.SubElement(xsheet, 'contents')
    for oname, odescription in sheet.objects.items():
        xobj = ET.SubElement(xcontents, 'object')
        xobj.attrib['name'] = oname
        ET.SubElement(xobj, 'description').text = odescription
    return xsheet


def build_shape(svg_path, width, height):
    attrib = {
        'xmlns:svg': "http://www.w3.org/2000/svg",
        'xmlns:xlink': "http://www.w3.org/1999/xlink",
        'xmlns': 'http://www.daa.com.au/~james/dia-shape-ns',
    }
    xshape = ET.Element('shape', attrib=attrib)
    ET.SubElement(xshape, 'name').text = svg_path.stem
    ET.SubElement(xshape, 'icon').text = f"{svg_path.stem}.png"

    xconns = ET.SubElement(xshape, 'connections')
    points = [
        (0, 0),
        (0, width // 2),
        (0, width),
        (height // 2, 0),
        (height, 0),
        (width // 2, height),
        (width // 2, height // 2),
        (width, height // 2),
        (width, height),
    ]
    for x, y in points:
        ET.SubElement(xconns, 'point', attrib={'x': str(x), 'y': str(y)})

    ET.SubElement(xshape, 'aspectratio', attrib={'type': 'fixed'})

    xsvg = ET.SubElement(xshape, 'svg:svg')
    ET.SubElement(xsvg, 'svg:image', attrib={'xlink:href': f"{svg_path.stem}.svg", 'x': '0', 'y': '0', 'width': str(width), 'height': str(height)})

    return xshape


def main():
    aparser = ArgumentParser()
    aparser.add_argument('--name', default='TODO')
    aparser.add_argument('svg_file', nargs='+')
    aparser.add_argument('-v', '--verbosity', action="count",
                         help="increase output verbosity (e.g., -vv is more than -v)")
    args = aparser.parse_args()

    # Check and define verbosity print output function
    # source: stackoverflow.com/questions/5980042/how-to-implement-the-verbose-or-v-option-into-a-script
    if args.verbosity:
        def _verbose_print(*verbose_args):
            if verbose_args[0] > (1 - args.verbosity):
                print(verbose_args[1])
    else:
        _verbose_print = lambda *a: None # do-nothing function

    global verbose_print
    verbose_print = _verbose_print

    # Set paths for sheets and shapes using name to hold all the shapes
    psheets = Path('sheets')
    psheets.mkdir(exist_ok=True)
    pshapes = Path(f'shapes/{args.name}')
    pshapes.mkdir(parents=True, exist_ok=True)

    sheet = Sheet(
        name=args.name,
        author=getpass.getuser(),
        description=f"{args.name} description",
        objects={}
    )

    seen = set()
    for svg_file in args.svg_file:
        svg_file = Path(svg_file)
        if svg_file.stem in seen:
            verbose_print(2, f"WARN: ignoring duplicate {svg_file.stem}")
            continue
        seen.add(svg_file.stem)

        png_file = f'{pshapes}/{svg_file.stem}.png'
        subprocess.check_call([
            'convert',
            str(svg_file),
            '-resize',
            '22x22',
            png_file,
        ])
        verbose_print(1, f"INFO: wrote {png_file}")

        width, height = map(int, subprocess.check_output([
            'identify',
            '-format',
            '%w %h',
            png_file,
        ]).decode().split())

        new_path = pshapes.joinpath(f"{svg_file.stem}.svg")
        new_path.write_bytes(svg_file.read_bytes())
        verbose_print(1, f"INFO: wrote {new_path}")

        xshape = build_shape(svg_file, width, height)
        # ET.indent(xshape)
        tshape = ET.tostring(xshape, encoding='unicode')
        shape_path = pshapes.joinpath(f"{svg_file.stem}.shape")
        shape_path.write_text(tshape)
        verbose_print(1, f"INFO: wrote {shape_path}")

        sheet.objects[svg_file.stem] = f"description {svg_file.stem}"

    xsheet = build_sheet(sheet)
    # ET.indent(xsheet)
    tsheet = ET.tostring(xsheet, encoding="unicode")
    sheet_path = psheets.joinpath(f"{args.name}.sheet")
    sheet_path.write_text(tsheet)
    verbose_print(1, f"INFO: wrote {sheet_path}")


if __name__ == '__main__':
    main()
