# v.in.ogr input=C:\Users\Frank\Desktop\grid\Intersection_id_73.shp output=Intersection_id_73
# v.dissolve input=Intersection_id_73 output=dissolved_Intersection_id_73 column=dislv
# v.patch --o input=dissolved_Intersection_id_73,dissolved_Intersection_id_74 output=patched

# coding: utf-8

import fnmatch
import grass.script as grass
from grass.pygrass.modules import Module
from grass.script.utils import parse_key_val
from itertools import izip_longest
import os
import subprocess


def grouper(iterable, n, fillvalue=None):
    """Collect data into fixed-length chuncks or blocks
       https://docs.python.org/2.7/library/itertools.html#recipes"""
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

def clean():
    """Deletes all vector maps in Location"""
    for vector_map in grass.list_strings(type='vector'):
        remove_map(vector_map)


def map_exists(name):
    """check if a map already exists"""
    vector_maps = grass.list_strings(type='vector')

    for map_ in vector_maps:
        if map_ == '{}@Frank'.format(name):
            return True

    return False


def remove_map(name):
    grass.run_command('g.remove', type='vector', name=name, flags='f')

def read_shapefiles(args):
    """Get a list of all shapefiles in the args.path directory"""
    shapefiles = []
    for root, subdirs, files in os.walk(args.path):
        for filename in files:
            if fnmatch.fnmatch(filename, '*.shp'):
                shapefiles.append(filename)

    return shapefiles


def import_(args, shapefiles):
    """Import shapefiles into GRASS with v.in.ogr"""
    basemaps = []

    for shapefile in shapefiles:
        name = os.path.splitext(shapefile)[0]

        if name not in basemaps:
            basemaps.append(name)

        if map_exists(name):
            break

        # import map
        grass.run_command('v.in.ogr',
                          input=os.path.join(os.path.abspath(args.path),
                          shapefile), output=name, flags='o', snap=0.1)
        # add a dissolve column to the map
        grass.run_command('v.db.addcolumn', map=name, columns='dissolve varchar(15)')

    return basemaps


def dissolve(args):
    """Main routine for dissolving a list of shapefiles into one shapefile"""
    shapefiles = read_shapefiles(args)

    if args.clean:
        clean()

    basemaps = import_(args, shapefiles)
    dissolved_maps = []

    # dissolve each grid tile, clean it and generalize it
    for map_ in basemaps:
        dissolved_map = 'dissolved_{}'.format(map_)
        dissolved_maps.append(dissolved_map)

        if map_exists(dissolved_map):
            break

        grass.run_command('v.dissolve', input=map_,
                          output='dislv_tmp', column='dissolve')
        grass.run_command('v.clean', input='dislv_tmp', output='clean_tmp',
                          tool='snap,break,rmdupl', thres=0.1)
        grass.run_command('v.generalize', input='clean_tmp',
                          output=dissolved_map, method='douglas', threshold=1)
        remove_map('clean_tmp')
        remove_map('dislv_tmp')

    # dissolve only after patching
    do_dissolve = False
    for map_ in dissolved_maps:
        if map_exists('dissolved'):
            print "Patching {}".format(map_)
            grass.run_command('v.patch', input='dissolved,{}'.format(map_),
                              output='dislv_tmp', flags='e')
            grass.run_command('v.clean', input='dislv_tmp', output='clean_tmp',
                              tool='break,rmdupl,rmsa', thres=0.1)
            do_dissolve = True
        else:
            grass.run_command('g.copy', vector='{},dissolved'.format(map_))
            do_dissolve = False

        if do_dissolve:
            print "Dissolving {}".format(map_)
            grass.run_command('v.dissolve', input='clean_tmp', output='dislv_tmp',
                              column='dissolve', overwrite=True)
            grass.run_command('v.clean', input='dislv_tmp', output='dissolved',
                              tool='snap,break,rmdupl', thres=0.1, overwrite=True)
            remove_map('dislv_tmp')
            remove_map('clean_tmp')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clean', action='store_true')
    parser.add_argument('path')
    args = parser.parse_args()
    dissolve(args)
