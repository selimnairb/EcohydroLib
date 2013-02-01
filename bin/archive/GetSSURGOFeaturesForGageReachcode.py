#!/opt/local/bin/python2.7
#
# Query USDA soil datamart for SSURGO features and attributes
#
# Author(s): Brian Miles - brian_miles@unc.edu
#      Date: 20121016 
#
# Revisions: 20121016: 1.0: First fully working version
#
# TODO: Make work for catchments larger than USDA datamart web service limit
#
# Example command line: PYTHONPATH=${PYTHONPATH}:../SSURGOLib:../SpatialDataLib:../NHDPlus2Lib:../WCS4DEMLib:../SOLIMLib ./GetSSURGOFeaturesForGageReachcode.py -i macosx2.cfg -o scratch2 -r 02060003000740 -m 84.03533 -t EPSG:26918
# Example command line: PYTHONPATH=${PYTHONPATH}:../SSURGOLib:../SpatialDataLib:../NHDPlus2Lib:../WCS4DEMLib:../SOLIMLib /usr/bin/python2.7 ./GetSSURGOFeaturesForGageReachcode.py -i ubuntu.cfg -o scratch-linux -r 02060003000740 -m 84.03533 -t EPSG:26918
#
import os
import sys
import errno
import argparse
import ConfigParser

from wcs4demlib.demquery import getDEMForBoundingBox
from nhdplus2lib.networkanalysis import getBoundingBoxForCatchmentsForGage
from ssurgolib.featurequery import getMapunitFeaturesForBoundingBox
from ssurgolib.rasterize import rasterizeSSURGOFeatures
from spatialdatalib.utils import convertGMLToShapefile
import ssurgolib.attributequery
from solimlib.inference import inferSoilPropertiesForSSURGOAndTerrainData

# Handle command line options
parser = argparse.ArgumentParser(description='Get SSURGO features for the drainage area of an NHDPlus2 gage')
parser.add_argument('-i', '--configfile', dest='configfile', required=True,
                  help='The configuration file')
parser.add_argument('-o', '--outdir', dest='outdir', required=False,
                  help='The directory to which intermediate and final files should be saved')
parser.add_argument('-r', '--reachcode', dest='reachcode', required=True,
                  help='A string representing the Reachcode of a stream reach whose catchment ComIDs are to be determined from NHDPlus2 topology')
parser.add_argument('-m', '--measure',  dest='measure', required=True, type=float,
                  help='A float representing the measure along reach where Stream Gage is located in percent from downstream end of the one or more NHDFlowline features that are assigned to the ReachCode')
parser.add_argument('-s', '--soilrasterresolution', dest='soilrasterresolution', required=False, type=float,
                  help='A floating point number representing of desired output resolution of soil property raster maps; unit: meters')
parser.add_argument('-t', '--t_srs', dest='t_srs', required=True, 
                    help='Target spatial reference system of output, in EPSG:num format')
args = parser.parse_args()

soilRasterResolution = -1
if args.soilrasterresolution:
    soilRasterResolution = args.soilrasterresolution
    if soilRasterResolution <= 0:
        raise ValueError("soilrasterresolution must be a positive real number")

if not os.access(args.configfile, os.R_OK):
    raise IOError(errno.EACCES, "Unable to read configuration file %s" %
                  args.configfile)

config = ConfigParser.RawConfigParser()
config.read(args.configfile)

if not config.has_option('GDAL/OGR', 'PATH_OF_OGR2OGR'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_OGR2OGR'))
if not config.has_option('GDAL/OGR', 'PATH_OF_GDAL_RASTERIZE'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_GDAL_RASTERIZE'))
if not config.has_option('SOLIM', 'PATH_OF_SOLIM'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'SOLIM', 'PATH_OF_SOLIM'))
if not config.has_option('NHDPLUS2', 'PATH_OF_NHDPLUS2_DB'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'NHDPLUS2', 'PATH_OF_NHDPLUS2_DB'))
if not config.has_option('NHDPLUS2', 'PATH_OF_NHDPLUS2_CATCHMENT'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'NHDPLUS2', 'PATH_OF_NHDPLUS2_CATCHMENT'))  

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

solimCmdPath = config.get('SOLIM', 'PATH_OF_SOLIM')
if not os.access(solimCmdPath, os.X_OK):
    raise IOError(errno.EACCES, "SOLIM command %s is not executable" % (solimCmdPath,))

# Get bounding box
bbox = getBoundingBoxForCatchmentsForGage(config, outdir, args.reachcode, args.measure)
print "Bounding box for gage %s measure %f: %f,%f,%f,%f" % (args.reachcode, args.measure, bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY'])

# Get DEM from DEMExplorer
demFilename = "DEM_%s.tif" % (args.reachcode)
returnCode = getDEMForBoundingBox(outdir, demFilename, bbox=bbox, srs=args.t_srs)
assert(returnCode)

# Get SSURGO data
gmlFilenames = getMapunitFeaturesForBoundingBox(outdir, bbox, mapunitExtended=True, tileBbox=False)

# Convert from gml to shp and then rasterize
for gmlFilename in gmlFilenames:
    gmlFilepath = os.path.join(outdir, gmlFilename)
    layerName = os.path.splitext(gmlFilename)[0]
    shpFilename = convertGMLToShapefile(config, outdir, gmlFilepath, layerName, args.t_srs)

    # Truncate attributes to 10 characters because shapefiles rely on ancient technology
    attrList = [elem[:10] for elem in ssurgolib.attributequery.attributeListNumeric] 
    if soilRasterResolution == -1:
        # Use DEM raster resolution as soil property raster resolution
        sys.stderr.write("Using DEM resolution for soil property rasters ...\n")
        rasterizeSSURGOFeatures(config=config, outputDir=outdir, featureFilename=shpFilename, featureLayername=layerName, \
                                featureAttrList=attrList, \
                                getResolutionFromRasterFileNamed=demFilename)
    else:
        # Use user-specified soil raster resolution, but convert from meters into soil feature linear units
        sys.stderr.write("Using user-supplied resolution, %d meters x %d meters, for soil property rasters ...\n" % (soilRasterResolution, soilRasterResolution))
        rasterizeSSURGOFeatures(config=config, outputDir=outdir, featureFilename=shpFilename, featureLayername=layerName, \
                               featureAttrList=attrList, \
                               rasterResolutionX=soilRasterResolution, rasterResolutionY=soilRasterResolution)                     

    #solimCommand = "%s %s MUKEY %s %s avgSand,avgSilt,avgClay,avgKsat,avgPorosity" % \
    #    (solimCmdPath, shpFilename, demFilename, outdir)
    #print solimCommand
    #returnCode = os.system(solimCommand)
    returnCode = inferSoilPropertiesForSSURGOAndTerrainData(config, outdir, shpFilename, demFilename)
    assert(returnCode == 0)
    
    
