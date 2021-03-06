#!/usr/bin/env python
u"""
c_ampcor_iceye.py
Written by Enrico Ciraci' (03/2022)

Create the bat file to run AMPCOR between the considered pair of SLCs.

NOTE: Before Running this script, a preliminary constant offset between the
      two SLCs must be calculated by employing the relative orbital parameters
      must have been calculated.

COMMAND LINE OPTIONS:
  -h, --help            show this help message and exit
  --directory DIRECTORY, -D DIRECTORY :Project data directory.
  --pair PAIR, -P PAIR  SLC Pair passes as CSV - reference,secondary
  --np NP, -N NP        Number of Parallel Processes.
  --ampcor, -A {ampcor_large,ampcor_large2,ampcor_superlarge2}
         -> AMPCOR Implementation Selected.


PYTHON DEPENDENCIES:
    argparse: Parser for command-line options, arguments and sub-commands
           https://docs.python.org/3/library/argparse.html
    numpy: The fundamental package for scientific computing with Python
          https://numpy.org/

UPDATE HISTORY:
"""
# - Python dependencies
from __future__ import print_function
import os
import sys
import argparse
from datetime import datetime
import numpy as np
from utils.path_to_ampcor import path_to_ampcor
# - GAMMA's Python integration with the py_gamma module
import py_gamma as pg


def main():
    # - Read the system arguments listed after the program
    parser = argparse.ArgumentParser(
        description="""Create the bat file to run AMPCOR.
            """
    )
    # - Working Directory directory.
    default_dir = os.path.join(os.path.expanduser('~'), 'Desktop',
                               'iceye_gamma_test', 'output')
    parser.add_argument('--directory', '-D',
                        type=lambda p: os.path.abspath(os.path.expanduser(p)),
                        default=default_dir,
                        help='Project data directory.')

    parser.add_argument('--pair', '-P',
                        type=str,
                        default=None,
                        help='SLC Pair Codes separated by "_" '
                             'reference-secondary')

    parser.add_argument('--np', '-N',
                        type=int, default=14,
                        help='Number of Parallel Processes.')

    parser.add_argument('--ampcor', '-A',
                        type=str, default='ampcor_large',
                        choices=['ampcor_large', 'ampcor_large2',
                                 'ampcor_superlarge2'],
                        help='AMPCOR Implementation Selected.')

    parser.add_argument('--init_offset', '-I', action='store_true',
                        help='Determine initial offset between SLC'
                             'images using correlation of image intensity')

    args = parser.parse_args()

    if args.pair is None:
        print('# - Provide selected SLC names as: --pair=Ref_Code_Sec_Code')
        sys.exit()

    # - Reference and Secondary SLCs
    slc_list = args.pair.split('-')
    ref_slc = slc_list[0]
    sec_slc = slc_list[1]
    # -
    ref_slc_path = os.path.join(args.directory, 'slc+par', ref_slc + '.slc')
    ref_par_path = os.path.join(args.directory, 'slc+par', ref_slc + '.par')
    sec_slc_path = os.path.join(args.directory, 'slc+par', sec_slc + '.slc')
    sec_par_path = os.path.join(args.directory, 'slc+par', sec_slc + '.par')
    # - output directory
    if args.init_offset:
        out_dir = os.path.join(args.directory, 'pair_diff_io',
                               ref_slc + '-' + sec_slc)
    else:
        out_dir = os.path.join(args.directory, 'pair_diff',
                               ref_slc + '-' + sec_slc)
    off_par_path = os.path.join(out_dir, ref_slc + '-' + sec_slc + '.par')

    if not os.path.isfile(ref_slc_path):
        print(f'# - {ref_slc}.slc - Not Found.')
        sys.exit()
    if not os.path.isfile(ref_par_path):
        print(f'# - {ref_slc}.par - Not Found.')
        sys.exit()
    if not os.path.isfile(sec_slc_path):
        print(f'# - {sec_slc}.slc - Not Found.')
        sys.exit()
    if not os.path.isfile(sec_par_path):
        print(f'# - {sec_slc}.par - Not Found.')
        sys.exit()
    if not os.path.isfile(off_par_path):
        print(f'# - {ref_slc}' + '-' + f'{sec_slc}.par - Not Found.')
        sys.exit()

    # - other parameters - ampcor skip
    range_spacing = 30
    line_spacing = 30

    # - bat file name
    bat_id = os.path.join(out_dir, f'bat_{ref_slc}-{sec_slc}')

    # - read offset parameter file
    off_param_dict = pg.ParFile(off_par_path).par_dict

    # - initial range and azimuth offsets
    xoff = int(off_param_dict['initial_range_offset'][0])
    yoff = int(off_param_dict['initial_azimuth_offset'][0])
    print(f'# - initial_range_offset: {xoff}')
    print(f'# - initial_azimuth_offset: {yoff}')

    # - read reference slc parameters
    ref_param = pg.ParFile(ref_par_path).par_dict
    n_rec_ref = int(ref_param['azimuth_lines'][0])
    n_pix_ref = int(ref_param['range_samples'][0])

    # - read secondary slc parameters
    sec_param = pg.ParFile(sec_par_path).par_dict
    nrec_sec = int(sec_param['azimuth_lines'][0])
    n_pix_sec = int(sec_param['range_samples'][0])

    # - X-Axis - Range
    # - set first and last index to be considered
    # - in the case of the x-axis (range direction)
    x_start = 1
    x_end = n_pix_ref

    # - Y-Axis - Azimuth
    # - set total number of records equal to the
    # - maximum above the number of azimuth_lines of the
    # - two SLCs.
    y_end = max([n_rec_ref, nrec_sec])
    # - set first and last index to be considered
    # - in the case of the y-axis (azimuth direction)
    # - equal to the maximum value found between
    # - 0 and the initial_azimuth_offset estimated by
    # - "init_offset_orbit" multiplied by -1 and normalized
    # - for 30 (line_spacing ???)
    px0 = int(off_param_dict['initial_azimuth_offset'][0])
    y_start = int(max([0, np.fix((-px0 / line_spacing) + 1.5) * 30]))

    # - Total Number of Records to consider
    n_rec = int(y_end - y_start)

    # - Azimuth Pixel spacing
    ref_pixel_sp = float(ref_param['azimuth_pixel_spacing'][0].split(' ')[0])
    sec_pixel_sp = float(sec_param['azimuth_pixel_spacing'][0].split(' ')[0])

    # - y-slope
    y_slope = (ref_pixel_sp - sec_pixel_sp) / ref_pixel_sp
    print(f'# - Reference Azimuth Res: {ref_pixel_sp}')
    print(f'# - Secondary Azimuth Res: {sec_pixel_sp}')
    print(f'# - Computed y_slope: {y_slope}\n')
    print(f'# - Number of record of ref. SLC : {n_rec}')
    print(f'# - Divide offsets into {args.np} chunks')

    # - Number of offset lines per chunk
    nn = int(n_rec / line_spacing / args.np)
    print(f'# - Number of number of lines per chunk : {int(n_rec / args.np)}')
    print(f'# - Number of offset lines per chunk : {nn}')

    # - write input parameters files for each chunk
    # - considered by AMPCOR
    y_curr = int(y_start)       # - chunk specific y_start

    # - open bat_id file
    with open(bat_id, 'w', encoding='utf8') as fid_1:
        for i in range(args.np):
            # - Open specific chunk parameter file
            s_file = os.path.join(out_dir,
                                  f'{ref_slc}-{sec_slc}.offmap_{i + 1}.in')
            with open(s_file, 'w', encoding='utf8') as fid_2:
                # - Add Reference and Secondary SLC o=to the parameter file
                print(f'{ref_slc}.slc', file=fid_2)
                print(f'{sec_slc}.slc', file=fid_2)

                # - Output offset map file name
                print(f'{ref_slc}-{sec_slc}.offmap_{i + 1}', file=fid_2)

                print(os.path.join(path_to_ampcor(), args.ampcor)
                      + f' {ref_slc}-{sec_slc}.offmap_{i + 1}' + '.in old &',
                      file=fid_1)

                # - range_samples of the 2 slc
                print('{:5} {:5}'.format(n_pix_ref, n_pix_sec), file=fid_2)
                # - azimuth-direction processing spacing [see -> line_spacing]
                if (y_curr - 2 * line_spacing) > 0:
                    print('{:6} {:8} {:3}'
                          .format((y_curr - 2 * line_spacing),
                                  y_curr + line_spacing * (nn - 1),
                                  line_spacing), file=fid_2)
                else:
                    print('{:6} {:8} {:3}'
                          .format(0, y_curr + line_spacing * (nn - 1),
                                  line_spacing), file=fid_2)

                # - range-direction processing spacing [see -> range_spacing]
                print('{:4} {:5} {:5}'.format(x_start, x_end,
                                              range_spacing), file=fid_2)
                # - Define "Search Window" and "Chip" size
                print('64 64', file=fid_2)
                print('32 32', file=fid_2)
                print('1 1', file=fid_2)

                # - i-th chunk initial offset
                xoff_c = xoff
                yoff_c = int(np.fix(yoff + y_slope
                                    * (2. * y_curr
                                       + line_spacing * (nn - 1)) / 2. + 0.5))

                print('{:5} {:6}'.format(xoff_c, yoff_c), file=fid_2)

                # - Other Input parameters for AMPCOR
                # - threshold SNR = 0
                # - threshold covariance matrix = 1.e10
                # - > With this threshold values, all the offset are
                # -   calculated.
                print('0. 1.e10', file=fid_2)
                # - Offsets expressed as floating point real numbers
                print('f f', file=fid_2)

                # - print on std-output
                print(f'# - {ref_slc}-{sec_slc}.offmap_{i + 1}.in '
                      f'- y-boundaries ->' + str(y_curr).rjust(10)
                      + str(y_curr + line_spacing * (nn - 1)).rjust(10))
                print(f'# - Chunk {i + 1} offsets :'
                      f' yoff={yoff_c}, xoff={xoff_c}\n')

                # - update y_curr value
                y_curr += int(line_spacing * nn)
            # - Change Output file permissions
            os.chmod(s_file, 0o0755)
    os.chmod(bat_id, 0o0755)

    print('# - AMPCOR Calculation Parameters set.')


# - run main program
if __name__ == '__main__':
    start_time = datetime.now()
    main()
    end_time = datetime.now()
    print(f"# - Computation Time: {end_time - start_time}")
