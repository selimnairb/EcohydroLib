#!/opt/local/bin/python2.7
#
# Get bounding box for ESRI Shapefile projected in WGS84 (EPSG:4326)
#
# Author(s): Brian Miles - brian_miles@unc.edu
#      Date: 20130122
#
# Revisions: 20130122: 1.0: First fully working version
#
# Example command line: PYTHONPATH=${PYTHONPATH}:../../SpatialDataLib ./GetBoundingboxForShapefile.py -f ../../../scratchspace/scratch3/catchment.shp
#
#
import os
import errno
import argparse

from spatialdatalib.utils import getBoundingBoxForShapefile
   

# Handle command line options
parser = argparse.ArgumentParser(description='Get SSURGO features for a bounding box')
parser.add_argument('-f', '--shapefile', dest='shapefile', required=True,
                    help="Shapefile whose bounding box coordinates are to be used")
args = parser.parse_args()

if not os.access(args.shapefile, os.R_OK):
    raise IOError(errno.EACCES, "Unable to read shapefile %s" %
                  args.shapefile)
shapefile = os.path.abspath(args.shapefile)

# Get bounding box
bbox = getBoundingBoxForShapefile(shapefile)
print "%f %f %f %f" % (bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY'])

