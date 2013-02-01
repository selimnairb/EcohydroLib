#!/opt/local/bin/python2.7
#
# Query USDA soil datamart for SSURGO features and attributes
#
# Author(s): Brian Miles - brian_miles@unc.edu
#      Date: 20121105
#
# Revisions: 20121105: 1.0: First fully working version
#
# Example command line: PYTHONPATH=${PYTHONPATH}:../SSURGOLib:../SpatialDataLib:../NHDPlus2Lib ./GetSSURGOFeaturesForShapefile.py -i macosx2.cfg -f ../MapunitPolyExtended_bbox_-76.7669235994_39.2743914627_-76.7203809646_39.3054298527-attr.shp -t EPSG:26918 -s 3 3 -o scratch3
#
#
import os
import sys
import errno
import argparse
import ConfigParser

from spatialdatalib.utils import getBoundingBoxForShapefile
from spatialdatalib.utils import convertGMLToShapefile
from ssurgolib.featurequery import getMapunitFeaturesForBoundingBox
from ssurgolib.rasterize import rasterizeSSURGOFeatures
import ssurgolib.attributequery     

# Handle command line options
parser = argparse.ArgumentParser(description='Get SSURGO features for a bounding box')
parser.add_argument('-i', '--configfile', dest='configfile', required=True,
                    help='The configuration file')
parser.add_argument('-o', '--outdir', dest='outdir', required=False,
                    help='The directory to which intermediate and final files should be saved')
parser.add_argument('-f', '--shapefile', dest='shapefile', required=True,
                    help="Shapefile whose bounding box coordinates are to be used")
parser.add_argument('-s', '--soilrasterresolution', dest='soilrasterresolution', required=True, nargs=2, type=float,
                    help='Two floating point numbers representing the desired X and Y output resolution of soil property raster maps; unit: meters')
parser.add_argument('-t', '--t_srs', dest='t_srs', required=True, 
                    help='Target spatial reference system of output, in EPSG:num format')
args = parser.parse_args()

if not os.access(args.configfile, os.R_OK):
    raise IOError(errno.EACCES, "Unable to read configuration file %s" %
                  args.configfile)
config = ConfigParser.RawConfigParser()
config.read(args.configfile)

if not os.access(args.shapefile, os.R_OK):
    raise IOError(errno.EACCES, "Unable to read shapefile %s" %
                  args.shapefile)
shapefile = os.path.abspath(args.shapefile)

if not config.has_option('GDAL/OGR', 'PATH_OF_OGR2OGR'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_OGR2OGR'))
if not config.has_option('GDAL/OGR', 'PATH_OF_GDAL_RASTERIZE'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_GDAL_RASTERIZE'))

if args.outdir:
    outdir = args.outdir
else:
    outdir = os.getcwd()
if not os.path.isdir(outdir):
    raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outdir,))
if not os.access(outdir, os.W_OK):
    raise IOError(errno.EACCES, "Not allowed to write to output directory %s" %
                  outdir)
outdir = os.path.abspath(outdir)
os.chdir(outdir)

soilRasterResolutionX = args.soilrasterresolution[0]
soilRasterResolutionY = args.soilrasterresolution[1]

# Get bounding box
bbox = getBoundingBoxForShapefile(shapefile)
print "Bounding box: (%f, %f) (%f, %f)" % (bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY'])

# Get SSURGO data
gmlFilenames = getMapunitFeaturesForBoundingBox(outdir, bbox, mapunitExtended=True, tileBbox=False)
    
# Convert from gml to shp and then rasterize
for gmlFilename in gmlFilenames:
    gmlFilepath = os.path.join(outdir, gmlFilename)
    layerName = os.path.splitext(gmlFilename)[0]
    shpFilename = convertGMLToShapefile(config, outdir, gmlFilepath, layerName, args.t_srs)

    # Truncate attributes to 10 characters because shapefiles rely on ancient technology
    attrList = [elem[:10] for elem in ssurgolib.attributequery.attributeListNumeric] 
    rasterizeSSURGOFeatures(config=config, outputDir=outdir, featureFilename=shpFilename, featureLayername=layerName, \
                           featureAttrList=attrList, \
                           rasterResolutionX=soilRasterResolutionX, rasterResolutionY=soilRasterResolutionY)                     

