#!/opt/local/bin/python2.7
#
# Get lat/lon, in WGS84 (EPSG:4326), from gage point layer (Gage_Loc) for
# gage identified by a source_fea (e.g. USGS Site Number) 
#
# Returns "<x>, <y>" or "Gage not found"
#
# Author(s): Brian Miles - brian_miles@unc.edu
#      Date: 20130124
#
# Revisions: 20130124: 1.0: First fully working version
#
# Example command line: PYTHONPATH=${PYTHONPATH}:../../NHDPlus2Lib:../../SpatialDataLib ./GetLocationForNHDStreamflowGage.py -i macosx2.cfg -g 01589330
#
import os
import sys
import errno
import argparse
import ConfigParser

from nhdplus2lib.networkanalysis import getLocationForStreamGageByGageSourceFea

# Handle command line options
parser = argparse.ArgumentParser(description='Get NHDPlus2 streamflow gage identifiers for a USGS gage. Outputs a string (reachcode) and a float (measure)')
parser.add_argument('-i', '--configfile', dest='configfile', required=True,
                    help='The configuration file')
parser.add_argument('-g', '--gageid', dest='gageid', required=True,
                    help='An integer representing the USGS site identifier')
args = parser.parse_args()

if not os.access(args.configfile, os.R_OK):
    raise IOError(errno.EACCES, "Unable to read configuration file %s" %
                  args.configfile)
config = ConfigParser.RawConfigParser()
config.read(args.configfile)

if not config.has_option('NHDPLUS2', 'PATH_OF_NHDPLUS2_GAGELOC'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'NHDPLUS2', 'PATH_OF_NHDPLUS2_GAGELOC'))

result = getLocationForStreamGageByGageSourceFea(config, args.gageid)
if result:
    print "%s %s" % (result[0], result[1])
else:
    print "Gage not found"
