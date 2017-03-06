#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import argparse
import binascii
import glob
import itertools
import os
import re

home_dir = os.path.expanduser('~')
acv_dir = os.path.join(home_dir, 'Library/Application Support/Adobe/Adobe Photoshop CC 2017/Presets/Curves')
lrtemplate_dirs = os.path.join(home_dir, 'Library/Application Support/Adobe/Lightroom/Develop Presets')


def handle_commandline():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', dest='source')
    parser.add_argument('-o', dest='target', default = acv_dir)
    args = parser.parse_args()
    source = os.path.abspath(args.source)

    return source, args.target


def parse_template(filename, exit_flag = False):
    """
    """
    hexstr = ''
    with open(filename, 'rb') as f:
        data = f.read()

    pattern1 = re.compile(r'(ToneCurvePV2012(?:Blue|Green|Red)?)\[\d{1,2}\] = (\d{1,3})', re.DOTALL)
    found = pattern1.findall(data)
    if len(found) > 0:
        d = dict()
        for k,v in itertools.groupby(found, key = lambda x: x[0]):
            d[k] = list([vi[1] for vi in v])
    else:
        pattern2 = re.compile(r'(ToneCurvePV2012.*?) = \{(.*?)\}', re.DOTALL)
        curves_data = pattern2.findall(data)

        if len(curves_data) == 0:
            exit_flag = True
        else:
            d = dict((x, re.findall(r'\d{1,3}', y)) for x, y in curves_data)

    if not exit_flag:
        hexd = dict()
        # http://www.adobe.com/devnet-apps/photoshop/fileformatashtml/#50577411_32675
        # A NULL curve (no change to image data) is represented by the following five-number,
        # ten-byte sequence in a file:
        null_curve = '00020000000000FF00FF'  # 2 0 0 255 255
        hexd.get('ToneCurvePV2012', null_curve)
        hexd.get('ToneCurvePV2012Red', null_curve)
        hexd.get('ToneCurvePV2012Green', null_curve)
        hexd.get('ToneCurvePV2012Blue', null_curve)

        for key, values in d.items():
            # Swap input and output for each point
            # Lightroom preset writes input, output
            # Photoshop curve hex data write in the opposite order
            print(key, values)
            for i in range(0, len(values), 2):
                values[i], values[i+1] = values[i+1], values[i]

            point_data = [len(values)/2] + [int(v) for v in values]

            # 0x0 is 00 00 in .acv file
            hexstr = ['{:04X}'.format(p) for p in point_data]
            hexd[key] = ''.join(hexstr)

        curve_header = '00040005'

        # Effect on Photoshop RGB curve is much harsher on the shadow
        # so replace the RGB curve by the null curve
        # Make adjustment in Photoshop to your taste
        # TODO: add a commandline argument to include RGB curve
        hexstr = curve_header + '{}{}{}{}'.format(*[null_curve,
                    hexd['ToneCurvePV2012Red'],
                    hexd['ToneCurvePV2012Green'],
                    hexd['ToneCurvePV2012Blue']]) + null_curve  # HEX data end with null fifth curve

    return exit_flag, hexstr


def main():
    source, target = handle_commandline()
    # templates = [t.decode('utf8') for t in glob.glob(os.path.join(source, '*.lrtemplate'))]
    templates = [t for t in os.listdir(source) if t.endswith('lrtemplate')]
    set_name  = os.path.split(source)[1]

    for t in templates:
        curve_name = os.path.split(t)[1].split('.lrtemplate')[0]
        exit_flag, hexstr = parse_template(os.path.join(source, t))

        if not exit_flag:
            outfile  = os.path.join(target, '{} - {}.acv'.format(re.sub(r'\+\s+', '', set_name), curve_name))
            with open(outfile, 'wb') as f:
                f.write(binascii.unhexlify(hexstr))


if __name__ == '__main__':
    main()
