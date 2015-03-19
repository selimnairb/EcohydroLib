"""@package ecohydrolib.spatialdata.utils
    
@brief Generic utilities for manipulating spatial data sets.
@brief Builds a task-oriented API, for select operations, on top of
GDAL/OGR utilities, GDAL/OGR API, Proj API.

This software is provided free of charge under the New BSD License. Please see
the following license information:

Copyright (c) 2013, University of North Carolina at Chapel Hill
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the University of North Carolina at Chapel Hill nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE UNIVERSITY OF NORTH CAROLINA AT CHAPEL HILL
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT 
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


@author Brian Miles <brian_miles@unc.edu>

@todo Refactor raster and vector functions into their own sub-packages
@toto Refactor bounding box as class
"""
import os, sys, errno
from math import sqrt
import math
import re
import ConfigParser
from subprocess import *

from osgeo.gdalconst import *
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from pyproj import Proj
from pyproj import transform
from pyproj import Geod

from shapely.geometry import shape

SHP_MINX = 0
SHP_MAXX = 1
SHP_MINY = 2
SHP_MAXY = 3

RASTER_RESAMPLE_METHOD = ['near', 'bilinear', 'cubic', 'cubicspline', 'lanczos', 'average', 'mode']
WGS84_EPSG = 4326
WGS84_EPSG_STR = 'EPSG:4326'

NORTH = 0.0
EAST = 90.0

BBOX_TILE_DIVISOR = 1.0

OGR_SHAPEFILE_DRIVER_NAME = 'ESRI Shapefile'
OGR_GEOJSON_DRIVER_NAME = 'GeoJSON'
OGR_DRIVERS = {OGR_SHAPEFILE_DRIVER_NAME: 'shp', 
               OGR_GEOJSON_DRIVER_NAME: 'geojson'}

EPSG_RE = re.compile('^epsg:\d+$')
GDAL_VERSION_RE = re.compile('^GDAL\s(\d{1,2})\.(\d{1,2})\.(\d{1,2}),\sreleased\s\d{4}/\d{2}/\d{2}\s*$')

def _readImageGDAL(filePath):
    ds = gdal.Open(filePath, GA_ReadOnly)
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    trans = ds.GetGeoTransform()
    proj = ds.GetProjection()
    ds=None
    return { 'rows': rows, 'cols': cols, 'trans': trans, 'srs': proj }


def bboxFromString(bboxStr):
    """ Get bbox dictionary from comma separated string of the form
        '-76.769782 39.273610 -76.717498 39.326008'
    
        @param bboxStr String representing bounding box in WGS84 coordinates
        @return Dict representing bounding box with keys: minX, minY, maxX, maxY, and srs
    """
    bbox = bboxStr.split()
    bbox = dict({'minX': float(bbox[0]), 'minY': float(bbox[1]), 'maxX': float(bbox[2]), 'maxY': float(bbox[3]), 'srs': 'EPSG:4326'})
    return bbox


def isValidSrs(srsString):
    """ Determine if spatial reference string is valid.  Currently,
        only strings of the form 'EPSG:X...X' are valid.
        
        @param srsString
        
        @return True if valid, False if invalid
    """   
    m = EPSG_RE.match(srsString.lower())
    return m != None
    

def getEPSGStringForUTMZone(zone, isNorth):
    """ Get EPSG string, e.g. "EPSG:32618" for UTM zone (WGS84)
    
        @param zone Integer representing UTM zone
        @param isNorth True if north
        
        @return String of the pattern "^EPSG:\d+$"
    """
    if isNorth:
        epsg = 32600 + zone
    else:
        epsg = 32700 + zone
    return "EPSG:%d" % (epsg,)


def getUTMZoneFromCoordinates(longitude, latitude):
    """ Determine the UTM zone for coordinate pair
    
        @param longitude Float representing WGS84 longitude
        @param latitude Float representing WGS84 latitude
        
        @return Tuple of the form (zone number, true if north)
    """
    zone = int((math.floor((longitude + 180)/6) + 1) % 60)
    isNorth = False
    if latitude > 0:
        isNorth = True
    return (zone, isNorth)


def transformCoordinates(sourceX, sourceY, t_srs, s_srs="EPSG:4326"):
    """ Transform a pair of X,Y coordinates from one reference system to another
    
        @param sourceX A float representing the X coordinate
        @param sourceY A float representing the Y coordinate
        @param t_srs A string representing the spatial reference system of the output coordinates
        @param s_srs A string representing the spatial reference system, in EPSG format, of the input
            coordinates
        
        @return A tuple of floats representing the transformed coordinates
    """
    p_in = Proj(init=s_srs)
    p_out = Proj(init=t_srs)
    return transform(p_in, p_out, sourceX, sourceY)


def getRasterExtentAsBbox(extentRasterFilepath):
    """ Determine raster extent and store it in a bbox along with the spatial 
        reference system of the raster
    
        @param extentRasterFilepath String representing the path of the raster
        whose extent we are interested in
        @return Dict representing bounding box with keys: minX, minY, maxX, maxY, and srs
        
        @raise IOError(errno.ENOENT) if extentRasterFilepath does not exist
        @raise IOError(errno.EACCESS) if extentRasterFilepath is not readable
    """
    extentRasterFilepath = os.path.abspath(extentRasterFilepath)
    if not os.path.exists(extentRasterFilepath):
        raise IOError(errno.ENOENT, "Raster %s does not exist" % (extentRasterFilepath,) )
    if not os.access(extentRasterFilepath, os.R_OK):
        raise IOError(errno.EACCES, "Raster %s is not readable" % (extentRasterFilepath,) )
    
    extentImg = _readImageGDAL(extentRasterFilepath)
    
    rows = extentImg['rows']
    cols = extentImg['cols']
    targetResX = abs(extentImg['trans'][1])
    targetResY = abs(extentImg['trans'][5])
    xmin = extentImg['trans'][0]
    ymax = extentImg['trans'][3]
    xmax = xmin + (targetResX * cols)
    ymin = ymax - (targetResY * rows)
    
    # TODO: Refactor: This is inefficient because we are reading raster twice
    # But _readImageGDAL gives us SRS in WKT, whereas getSpatialReferenceForRaster
    # give us SRS in EPSG, which is what we need.
    srs = getSpatialReferenceForRaster(extentRasterFilepath)[5]
    
    bbox = dict({'minX': float(xmin), 'minY': float(ymin), 'maxX': float(xmax), 'maxY': float(ymax), 'srs': srs})
    return bbox


def extractTileFromRasterByRasterExtent(config, outputDir, extentRasterFilepath, inRasterFilepath, outRasterFilename, resampleMethod='near'):
    """ Extract a tile from a raster using the extent of another raster as the tile bounds.
        
        @note Output raster will be in LZW-compressed GeoTIFF file.
        @note Will delete existing output raster if it already exists, then perform the extraction
        
        @param config Python ConfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_GDAL_WARP'
        @param outputDir String representing the absolute/relative path of the directory into which output raster
         should be written
        @param extentRasterFilepath String representing the path of the extent raster
        @param inRasterFilepath String representing the path of the raster from which a tile will be extracted
        @param outRasterFilename String representing the name of the output raster
        @param resampleMethod String representing method to use to resample; one of: RASTER_RESAMPLE_METHOD
    """
    assert(resampleMethod in RASTER_RESAMPLE_METHOD)
    gdalCmdPath = config.get('GDAL/OGR', 'PATH_OF_GDAL_WARP')
    if not os.access(gdalCmdPath, os.X_OK):
        raise IOError(errno.EACCES, "The gdalwarp binary at %s is not executable" %
                      gdalCmdPath)
    gdalCmdPath = os.path.abspath(gdalCmdPath)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    extentRasterFilepath = os.path.abspath(extentRasterFilepath)
    inRasterFilepath = os.path.abspath(inRasterFilepath)
    
    outRasterFilepath = os.path.join(outputDir, outRasterFilename)
    outRasterFilepath = os.path.abspath(outRasterFilepath)

    if os.path.exists(outRasterFilepath):
        os.unlink(outRasterFilepath)
    
    extentImg = _readImageGDAL(extentRasterFilepath)
    t_srs = extentImg['srs']
    inImg = _readImageGDAL(inRasterFilepath)
    s_srs = inImg['srs']
    
    rows = extentImg['rows']
    cols = extentImg['cols']
    targetResX = abs(extentImg['trans'][1])
    targetResY = abs(extentImg['trans'][5])
    xmin = extentImg['trans'][0]
    ymax = extentImg['trans'][3]
    xmax = xmin + (targetResX * cols)
    ymin = ymax - (targetResY * rows)
    
    targetExtent = [xmin, ymin, xmax, ymax]
    targetExtent = [str(x) for x in targetExtent]
    targetExtent = ' '.join(targetExtent)
    
    targetRes = "%f %f" % (targetResX, targetResY)
    
    gdalCommand = "%s -s_srs %s -t_srs %s -te %s -tr %s -r %s %s %s" \
        % (gdalCmdPath, s_srs, t_srs, targetExtent, targetRes, resampleMethod, inRasterFilepath, outRasterFilepath)
    #print gdalCommand
    returnCode = os.system(gdalCommand)
    if returnCode != 0:
        raise Exception("GDAL command %s failed." % (gdalCommand,)) 
            

def extractTileFromRaster(config, outputDir, inRasterFilename, outRasterFilename, bbox):
    """ Extract a tile from a raster. Tile extent is defined by supplied bounding box 
        with coordinates defined in WGS84 (EPSG:4326).
        
        @note Output raster will be in LZW-compressed GeoTIFF file.
        @note Will silently return if output raster already exists.
        
        @param config Python ConfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_GDAL_TRANSLATE'
        @param outputDir String representing the absolute/relative path of the directory into which output raster
         should be written
        @param inRasterFilename String representing the name of the input raster
        @param outRasterFilename String representing the name of the output raster
        @param bbox A dict containing keys: minX, minY, maxX, maxY, srs, where srs='EPSG:4326' (WGS84)
    """
    gdalCmdPath = config.get('GDAL/OGR', 'PATH_OF_GDAL_TRANSLATE')
    if not os.access(gdalCmdPath, os.X_OK):
        raise IOError(errno.EACCES, "The gdal_translate binary at %s is not executable" %
                      gdalCmdPath)
    gdalCmdPath = os.path.abspath(gdalCmdPath)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    inRasterFilepath = os.path.join(outputDir, inRasterFilename)
    outRasterFilepath = os.path.join(outputDir, outRasterFilename)
    
    if not os.path.exists(outRasterFilepath):
        # Convert into coordinate system of inRaster
        inRasterSrs = getSpatialReferenceForRaster(inRasterFilepath)
        inSrs = osr.SpatialReference()
        assert(inSrs.ImportFromWkt(inRasterSrs[4]) == 0)
        p_in = Proj(init="EPSG:4326")
        p_out = Proj(inSrs.ExportToProj4())
        (ulX, ulY) = transform(p_in, p_out, bbox['minX'], bbox['maxY'])
        (lrX, lrY) = transform(p_in, p_out, bbox['maxX'], bbox['minY'])
        
        gdalCommand = "%s -q -stats -of GTiff -co 'COMPRESS=LZW' -projwin %f %f %f %f %s %s" \
                        % (gdalCmdPath, ulX, ulY, lrX, lrY, \
                           inRasterFilepath, outRasterFilepath)
        #print gdalCommand
        returnCode = os.system(gdalCommand)
        if returnCode != 0:
            raise Exception("GDAL command %s failed." % (gdalCommand,)) 


def resampleRaster(config, outputDir, inRasterFilepath, outRasterFilename, \
                s_srs, t_srs, trX, trY, resampleMethod='bilinear'):
    """ Resample raster from one spatial reference system and resolution to another.
        
        @note Output raster will be in LZW-compressed GeoTIFF file.
        @note Will silently return if output raster already exists.
    
        @param config Python ConfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_GDAL_WARP'
        @param outputDir String representing the absolute/relative path of the directory into which output raster
            should be written
        @param inRasterFilepath String representing the path of the input raster
        @param outRasterFilename String representing the name of the output raster
        @param s_srs String representing the spatial reference of the input raster, if s_srs is None, 
            the input raster's spatial reference
        @param t_srs String representing the spatial reference of the output raster
        @param trX Float representing the X resolution of the output raster (in target spatial reference units)
        @param trY Float representing the Y resolution of the output raster (in target spatial reference units) 
        @param resampleMethod String representing resampling method to use. Must be one of spatialdatalib.utils.RASTER_RESAMPLE_METHOD.
        
        @exception ConfigParser.NoSectionError
        @exception ConfigParser.NoOptionError
        @exception IOError(errno.ENOTDIR) if outputDir is not a directory
        @exception IOError(errno.EACCESS) if outputDir is not writable
        @exception ValueError if trX or trY are not floating point numbers greater than 0
        @exception Exception if a gdal_warp command fails
    """
    gdalCmdPath = config.get('GDAL/OGR', 'PATH_OF_GDAL_WARP')
    if not os.access(gdalCmdPath, os.X_OK):
        raise IOError(errno.EACCES, "The gdalwarp binary at %s is not executable" %
                      gdalCmdPath)
    gdalCmdPath = os.path.abspath(gdalCmdPath)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    trX = float(trX)
    if trX <= 0.0:
        raise ValueError("trX must be > 0.0")
    trY = float(trY)
    if trY <= 0.0:
        raise ValueError("trY must be > 0.0")
    
    assert(resampleMethod in RASTER_RESAMPLE_METHOD)
    
    nodata = getNodataValuesForRaster(inRasterFilepath)
    nodataStr = ' '.join(map(str, nodata))
    
    outRasterFilepath = os.path.join(outputDir, outRasterFilename)
    
    if not os.path.exists(outRasterFilepath):
        if s_srs is None:
            gdalCommand = "%s -q -t_srs %s -dstnodata '%s' -tr %f %f -r %s -of GTiff -co 'COMPRESS=LZW' %s %s" \
                            % (gdalCmdPath, t_srs, nodataStr, trX, trY, resampleMethod, \
                               inRasterFilepath, outRasterFilepath)
        else:
            gdalCommand = "%s -q -s_srs %s -t_srs %s -dstnodata '%s' -tr %f %f -r %s -of GTiff -co 'COMPRESS=LZW' %s %s" \
                            % (gdalCmdPath, s_srs, t_srs, nodataStr, trX, trY, resampleMethod, \
                               inRasterFilepath, outRasterFilepath)
        #print gdalCommand
        returnCode = os.system(gdalCommand)
        if returnCode != 0:
            raise Exception("GDAL command %s failed." % (gdalCommand,)) 


def rescaleRaster(config, outputDir, inRasterFilepath, outRasterFilename, \
                  scalar):
    """ Rescale DN values of raster.
        
        @note Output raster will be in LZW-compressed GeoTIFF file.
        @note Will silently return if output raster already exists.
    
        @param config Python ConfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_GDAL_WARP'
        @param outputDir String representing the absolute/relative path of the directory into which output raster
            should be written
        @param inRasterFilepath String representing the path of the input raster
        @param outRasterFilename String representing the name of the output raster
        @param scalar Float representing scalar.  Values can run from (-Inf, Inf).

        @exception ConfigParser.NoSectionError
        @exception ConfigParser.NoOptionError
        @exception IOError(errno.ENOTDIR) if outputDir is not a directory
        @exception IOError(errno.EACCESS) if outputDir is not writable
        @exception ValueError if scalar is not a floating point number
        @exception Exception if a gdal_calc.py command fails
    """
    gdalBase = None
    try:
        gdalBase = config.get('GDAL/OGR', 'GDAL_BASE')
    except ConfigParser.NoOptionError:
        gdalBase = os.path.dirname(config.get('GDAL/OGR', 'PATH_OF_GDAL_WARP'))
    
    # Get GDAL version
    gdalVersionCommand = config.get('GDAL/OGR', 'PATH_OF_GDAL_WARP') + ' --version'
    process = Popen(gdalVersionCommand, shell=True,
                    stdout=PIPE, stderr=PIPE)
    (process_stdout, process_stderr) = process.communicate()
    if process.returncode != 0:
        raise Exception("Unable to get GDAL version using {0} which, returned {1}\nstdout:\n{2}\nstderr:\n{3}\n.".format(gdalVersionCommand, 
                                                                                                                         process.returncode,
                                                                                                                         process_stdout,
                                                                                                                         process_stderr))
    m = GDAL_VERSION_RE.match(process_stdout)
    if not m:
        raise Exception("Unable to determine GDAL version, command returned: {0}".format(process_stdout))
    major_version = int(m.group(1))
    minor_version = int(m.group(2))
    gdalCalcCOSupported = True
    if major_version < 2:
        if minor_version < 10:
            # gdal_calc.py didn't support --co options until GDAL 1.10
            gdalCalcCOSupported = False
    
    gdalCmdPath = os.path.join(gdalBase, 'gdal_calc.py')
    if not os.access(gdalCmdPath, os.X_OK):
        raise IOError(errno.EACCES, "The gdalwarp binary at %s is not executable" %
                      gdalCmdPath)
    gdalCmdPath = os.path.abspath(gdalCmdPath)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    scalar = float(scalar)
    
    outRasterFilepath = os.path.join(outputDir, outRasterFilename)
    
    if not os.path.exists(outRasterFilepath):
        gdalCommand = "%s -A %s --outfile=%s --type='Float32' --calc='A*%s' --format=GTiff" \
                            % (gdalCmdPath, inRasterFilepath, outRasterFilepath, scalar)
        if gdalCalcCOSupported:
            gdalCommand += " --co='COMPRESS=LZW'"
        #print gdalCommand
        returnCode = os.system(gdalCommand)
        if returnCode != 0:
            raise Exception("GDAL command %s failed." % (gdalCommand,)) 

def convertGMLToShapefile(config, outputDir, gmlFilepath, layerName, t_srs):
    """ Convert a GML file to a shapefile.  Will silently exit if shapefile already exists
    
        @param config A Python ConfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_OGR2OGR'
        @param outputDir String representing the absolute/relative path of the directory into which shapefile should be written
        @param gmlFilepath String representing the absolute path of the GML file to convert
        @param layerName String representing the name of the layer contained in the GML file to write to a shapefile
        @param t_srs String representing the spatial reference system of the output shapefile, of the form 'EPSG:XXXX'
        
        @return String representing the name of the shapefile written
    
        @exception Exception if the conversion failed.
    """
    pathToOgrCmd = config.get('GDAL/OGR', 'PATH_OF_OGR2OGR')
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    shpFilename = "%s.shp" % (layerName,)
    shpFilepath = os.path.join(outputDir, shpFilename)
    if not os.path.exists(shpFilepath):
        ogrCommand = "%s -f 'ESRI Shapefile' -nln %s -t_srs %s %s %s" % (pathToOgrCmd, "MapunitPolyExtended", t_srs, shpFilepath, gmlFilepath)
        returnCode = os.system(ogrCommand)
        if returnCode != 0:
            raise Exception("GML to shapefile command %s returned %d" % (ogrCommand, returnCode))
    
    return shpFilename


def convertGMLToGeoJSON(config, outputDir, gmlFilepath, layerName, t_srs='EPSG:4326'):
    """ Convert a GML file to a shapefile.  Will silently exit if GeoJSON already exists
    
        @param config A Python ConfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_OGR2OGR'
        @param outputDir String representing the absolute/relative path of the directory into which GeoJSON should be written
        @param gmlFilepath String representing the absolute path of the GML file to convert
        @param layerName String representing the name of the layer contained in the GML file to write to a GeoJSON
        @param t_srs String representing the spatial reference system of the output GeoJSON, of the form 'EPSG:XXXX'
        
        @return String representing the name of the GeoJSON written
    
        @exception Exception if the conversion failed.
    """
    pathToOgrCmd = config.get('GDAL/OGR', 'PATH_OF_OGR2OGR')
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    geojsonFilename = "%s.geojson" % (layerName,)
    geojsonFilepath = os.path.join(outputDir, geojsonFilename)
    if not os.path.exists(geojsonFilepath):
        ogrCommand = "%s -f 'GeoJSON' -nln %s -t_srs %s %s %s" % (pathToOgrCmd, layerName, t_srs, geojsonFilepath, gmlFilepath)
        returnCode = os.system(ogrCommand)
        if returnCode != 0:
            raise Exception("GML to GeoJSON command %s returned %d" % (ogrCommand, returnCode))
    
    return geojsonFilename


def convertGeoJSONToShapefile(config, outputDir, geoJSONFilepath, shapefileName, layerName='OGRGeoJSON', t_srs='EPSG:4326'):
    """ Convert a GeoJSON file to a shapefile.  Will silently exit if shapefile already exists
    
        @param config A Python ConfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_OGR2OGR'
        @param outputDir String representing the absolute/relative path of the directory into which shapefile should be written
        @param geoJSONFilepath String representing the absolute path of the GeoJSON file to convert
        @param layerName String representing the name of the layer contained in the GeoJSON file to write to a shapefile
        @param t_srs String representing the spatial reference system of the output shapefile, of the form 'EPSG:XXXX'
        
        @return String representing the name of the shapefile written
    
        @exception Exception if the conversion failed.
    """
    pathToOgrCmd = config.get('GDAL/OGR', 'PATH_OF_OGR2OGR')
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    shpFilename = "%s.shp" % (shapefileName,)
    shpFilepath = os.path.join(outputDir, shpFilename)
    if not os.path.exists(shpFilepath):
        ogrCommand = "%s -f 'ESRI Shapefile' -nln %s -t_srs %s %s %s" % (pathToOgrCmd, layerName, t_srs, shpFilepath, geoJSONFilepath)
        returnCode = os.system(ogrCommand)
        if returnCode != 0:
            raise Exception("GeoJSON to shapefile command %s returned %d" % (ogrCommand, returnCode))
    
    return shpFilename


def mergeFeatureLayers(config, outputDir, featureFilepaths, outLayerName,
                       outFormat='GeoJSON',
                       keepOriginals=False, 
                       t_srs='EPSG:4326',
                       overwrite=False):
    """ Combine vector feature files readable by OGR into a single feature layer.
    
        @param config A Python ConfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_OGR2OGR'
        @param outputDir String representing the absolute/relative path of the directory into which shapefile should be written
        @param featureFilepaths Array of strings representing the absolute path of the feature files to convert
        @param outLayerName String representing the name of the merged GeoJSON feature.  Extension '.geojson' will be added.
        @param outFormat String representing output format supported by OGR listed in OGR_DRIVERS
        @param keepOriginals Boolean, if True, original feature layers will be retained (otherwise they will be deleted)
        @param t_srs String representing the spatial reference system of the output feature, of the form 'EPSG:XXXX'
        @param overwrite Boolean, if True any existing files will be overwritten
        
        @return String representing the absolute path of the single feature file written
        
        @exception Exception if OGR returned an error.
    """
    pathToOgrCmd = config.get('GDAL/OGR', 'PATH_OF_OGR2OGR')
    
    assert(outFormat in OGR_DRIVERS.keys())
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    # Write virtual feature layer (requires GDAL 1.10)
    vFeatureFilename = 'mergeFeatureLayersToGeoJSON.vrt'
    vFeatureFilepath = os.path.join(outputDir, vFeatureFilename)
    
    f = open(vFeatureFilepath, 'w')
    f.write('<OGRVRTDataSource>\n\t<OGRVRTUnionLayer name="unionLayer">\n')
    for feature in featureFilepaths:
        if not os.access(feature, os.R_OK):
            raise IOError(errno.EACCES, "Not allowed to read feature %s" % (feature,))
        f.write('\t\t<OGRVRTLayer name="OGRGeoJSON">\n')
        f.write('\t\t\t<SrcDataSource>{0}</SrcDataSource>\n\t\t</OGRVRTLayer>\n'.format(feature))
    f.write('\t</OGRVRTUnionLayer>\n</OGRVRTDataSource>\n')
    f.close()
        
    # Merge to a single output feature
    outExt = OGR_DRIVERS[outFormat]
    outName = "%s.%s" % (outLayerName, outExt)
    outPath = os.path.join(outputDir, outName)
    if overwrite:
        if os.path.exists(outPath):
            os.unlink(outPath)
    ogrCommand = "%s -f '%s' -t_srs %s %s %s -dialect sqlite -sql \"SELECT DISTINCT geometry, * FROM unionLayer\"" % (pathToOgrCmd, outFormat, t_srs, outPath, vFeatureFilepath)
    returnCode = os.system(ogrCommand)
    if returnCode != 0:
        raise Exception("Merge feature layers to single layer command %s returned %d" % (ogrCommand, returnCode))
    
    # Remove originals (if requested)
    if not keepOriginals:
        os.unlink(vFeatureFilepath)
        for feature in featureFilepaths:
            os.unlink(feature)
            
    return outPath


def convertFeatureLayerToShapefile(config, outputDir, featureFilepath, shapefileName, layerName=None, t_srs='EPSG:4326', overwrite=False):
    """ Convert a vector feature file readible by OGR to a shapefile.  
        Will silently exit if output shapefile already exists
    
        @param config A Python ConfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_OGR2OGR'
        @param outputDir String representing the absolute/relative path of the directory into which shapefile should be written
        @param featureFilepath String representing the absolute path of the feature file to convert
        @param layerName String representing the name of the layer contained in the feature file to write to a shapefile.
                         If none, the base name of featureFilepath will be used
        @param t_srs String representing the spatial reference system of the output shapefile, of the form 'EPSG:XXXX'
        
        @return String representing the name of the shapefile written
    
        @exception Exception if the conversion failed.
    """
    pathToOgrCmd = config.get('GDAL/OGR', 'PATH_OF_OGR2OGR')
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    if not os.access(featureFilepath, os.R_OK):
        raise IOError(errno.EACCES, "Not allowed to read feature path %s" % (featureFilepath,))
    
    if layerName == None:
        layerName = os.path.splitext(os.path.basename(featureFilepath))[0]
    
    shpFilename = "%s.shp" % (shapefileName,)
    shpFilepath = os.path.join(outputDir, shpFilename)
    
    if os.path.exists(shpFilepath):
        if overwrite:
            deleteShapefile(shpFilepath)
        else:
            raise Exception("Output shapefile %s already exists, but the overwrite option was not specified." % (shpFilepath,) )
        
    # Import the feature layer using ogr2ogr...
    ogrCommand = "%s -f 'ESRI Shapefile' -nln %s -t_srs %s %s %s" % (pathToOgrCmd, layerName, t_srs, shpFilepath, featureFilepath)
    returnCode = os.system(ogrCommand)
    if returnCode != 0:
        raise Exception("Feature layer to shapefile command %s returned %d" % (ogrCommand, returnCode))
    
    return shpFilename


def deleteShapefile(shpfilePath):
    """ Delete shapefile and its related files (.dbf, .prj, .shx)
        
        @param shpfilePath -- Path, including filename, of the shapefile to be deleted
    """
    SHP_EXT = ['dbf', 'prj', 'shx']
    fileName = os.path.splitext(shpfilePath)[0]
    if os.path.exists(shpfilePath):
        os.remove(shpfilePath)
    for ext in SHP_EXT:
        tmpFilepath = fileName + "." + ext
        if os.path.exists(tmpFilepath):
            os.remove(tmpFilepath)


def getCoordinatesOfPointsFromShapefile(shpFilepath, layerName, pointIDAttr, pointIDs):
    """ Get WGS84 coordinates of point features in shapefile
    
        @param shpFilepath String representing the path of the shapefile
        @param layerName String representing the name of the layer within the shapefile from 
        to read points
        @param pointIDAttr String representing name of the attribute used to identify points
        @param pointIDs List of strings representing IDs of coordinate pairs
        
        @raise Exception if unable to read layer of shapefile, or if no feature(s) with given
        attribute value(s) were found in the shapefile
        
        @return Tuple of floats of the form (longitude, latitude)
    """
    coordinates = []
    
    if not os.access(shpFilepath, os.R_OK):
        raise IOError(errno.EACCES, "Unable to read shapefile %s" % (shpFilepath,))
    
    poDS = ogr.Open(shpFilepath, True)
    assert(poDS.GetLayerCount() > 0)
    poLayer = poDS.GetLayerByName(layerName)
    if not poLayer:
        raise Exception( "Layer named '%s' not found in shapefile %s" % (layerName, shpFilepath) )
    
    # Determine type of ID field
    poFeatureDef = poLayer.GetLayerDefn()
    assert(poFeatureDef)
    idAttrType = ogr.OFTString
    numFields = poFeatureDef.GetFieldCount()
    i = 0
    while i < numFields:
        poFieldDef = poFeatureDef.GetFieldDefn(i)
        if pointIDAttr == poFieldDef.GetNameRef():
            idAttrType = poFieldDef.GetType()
            break
        i = i + 1
    
    # Build query string to select points of interest
    assert(len(pointIDs) > 0)
    if ogr.OFTString == idAttrType:
        whereFilter = "%s='%s'" % (pointIDAttr, pointIDs[0])
        for point in pointIDs[1:]:
            whereFilter = "%s and %s=%s" % (whereFilter, pointIDAttr, point)
    else:
        whereFilter = "%s=%s" % (pointIDAttr, pointIDs[0])
        for point in pointIDs[1:]:
            whereFilter = "%s and %s=%s" % (whereFilter, pointIDAttr, point)
    
    # Determine spatial reference, and if we need to convert coordinates
    isWGS84 = True
    inSRS = poLayer.GetSpatialRef()
    epsgStr = "%s:%s" % ( inSRS.GetAttrValue("AUTHORITY", 0), inSRS.GetAttrValue("AUTHORITY", 1) )
    if WGS84_EPSG_STR != epsgStr:
        p_in = Proj(inSRS.ExportToProj4())
        p_out = Proj(init="EPSG:4326")
        isWGS84 = False
    
    # Iterate over features matching query string
    if poLayer.SetAttributeFilter(whereFilter) != 0:
        raise Exception( "Feature identified by \"%s\" not found in layer '%s' of shapefile %s" % \
                         (whereFilter, layerName, shpFilepath) )
    poFeature = poLayer.GetNextFeature()
    while poFeature:
        poGeometry = poFeature.GetGeometryRef()
        
        # Get coordinates
        x = poGeometry.GetX()
        y = poGeometry.GetY()
        
        # Convert coorinate pair to WGS84, if need be
        if not isWGS84:
            (x, y) = transform(p_in, p_out, x, y)
        
        coordinates.append( (x, y) )
        poFeature = poLayer.GetNextFeature()
        
    if len(coordinates) == 0:
        raise Exception( "No features identified by \"%s\" not found in layer '%s' of shapefile %s" % \
                         (whereFilter, layerName, shpFilepath) )
    return coordinates


def deleteGeoTiff(geoTiffPath):
    """ Delete GeoTIFF and its related files (.aux.xml)
        
        @param geoTiffPath -- Path, including filename, of the GeoTIFF to be deleted
    """
    GTIFF_EXT = ['tif.aux.xml']
    fileName = os.path.splitext(geoTiffPath)[0]
    if os.path.exists(geoTiffPath):
        os.remove(geoTiffPath)
    for ext in GTIFF_EXT:
        tmpFilepath = fileName + "." + ext
        if os.path.exists(tmpFilepath):
            os.remove(tmpFilepath)


def isCoordinatePairInBoundingBox(bbox, coordinates):
    """ Determine whether coordinate pair lies within bounding box
    
        @param bbox A dict containing keys: minX, minY, maxX, maxY, srs, where srs='EPSG:4326'
        @param coordinates List of tuples of floats of the form (longitude, latitude), in WGS84
    
        @return True if coordinates pair is within bounding box
    """
    assert(bbox['srs'] == 'EPSG:4326')
    
    lon = coordinates[0]
    lat = coordinates[1]
    
    if (lon < bbox['minX']) or (lon > bbox['maxX']):
        return False 
    if (lat < bbox['minY']) or (lat > bbox['maxY']):
        return False
    
    return True


def calculateBoundingBoxCenter(bbox):
    """ Calculate the central point of the bounding box
    
        @param bbox A dict containing keys: minX, minY, maxX, maxY, srs, where srs='EPSG:4326'
        
        @return Tuple of floats of the form (longitude, latitude)
    """
    x_diff = ( bbox['maxX'] - bbox['minX'] ) / 2
    y_diff = ( bbox['maxY'] - bbox['minY'] ) / 2
    longitude = bbox['minX'] + x_diff
    latitude = bbox['minY'] + y_diff
    return (longitude, latitude)


def calculateBoundingBoxArea(bbox, srs=WGS84_EPSG_STR):
    """ Calculate bbox area in squared units of srs
    
        @param bbox A dict containing keys: minX, minY, maxX, maxY, srs, where srs='EPSG:4326'
        @param srs String representing spatial reference system, in EPSG format, in which
        area should be calculated.
        
        @return Float representing the bounding box area in square meters
    """
    assert(bbox['srs'] == WGS84_EPSG_STR)
    coords = [(bbox['minX'], bbox['minY']), 
              (bbox['maxX'], bbox['minY']),
              (bbox['maxX'], bbox['maxY']), 
              (bbox['minX'], bbox['maxY'])]
    (lon, lat) = zip(*coords)
    if bbox['srs'] != srs:
        p_in = Proj(init=bbox['srs'])
        p_out = Proj(init=srs)
        (lon, lat) = transform(p_in, p_out, lon, lat)
        
    geojson = {'type': 'Polygon', 'coordinates': [zip(lon, lat)]}
    poly = shape(geojson)
    
    return poly.area


def tileBoundingBox(bbox, threshold, t_srs=WGS84_EPSG_STR, divisor=BBOX_TILE_DIVISOR):
    """ Break up bounding box into tiles if bounding box is larger than threshold. 
        Bounding box must be defined by WGS84 lat,lon coordinates
        
        @param bbox Dict containing keys: minX, minY, maxX, maxY, srs, where srs='EPSG:4326'
        @param threshold Float representing threshold area above which bounding box will be tiled. Units: sq. meters
        @param t_srs String representing spatial reference system, in EPSG format, in which
        area should be calculated.
        @param divisor Float representing amount by which to divide tile sides, such that tile side = sqrt(threshold) / divisor
        
        @return A list containing tiles defined as a dict containing keys: minX, minY, maxX, maxY, srs, where srs='EPSG:4326'
    """
    assert(bbox['srs'] == WGS84_EPSG_STR)
    
    threshold = float(threshold)
    divisor = float(divisor)
    
    assert(threshold > 0.0)
    assert(divisor > 0.0)
    
    geod = Geod(ellps='WGS84')
    area = calculateBoundingBoxArea(bbox, t_srs)
    
    bboxes = []
    if area <= threshold:
        sys.stderr.write("Area of bounding box <= threshold, no tiling\n")
        bboxes.append(bbox)
    else:
        # Tile it
        sys.stderr.write("Area of bounding box > threshold, tiling ...\n")
        # Calculate the length of a "side" of a square tile
        tileSide = sqrt(threshold) / divisor
        # Start at the southwestern-most corner of the bounding box
        minLat = bbox['minY']
        minLon = bbox['minX']
        #maxLat = None; maxLon = None
        while minLat < bbox['maxY']: 
            (lon, maxLat, backAz) = geod.fwd(lons=minLon, lats=minLat, az=NORTH, dist=tileSide)
            while minLon < bbox['maxX']:
                (maxLon, lat, backAz) = geod.fwd(lons=minLon, lats=maxLat, az=EAST, dist=tileSide)
                bboxes.append(dict({'minX': minLon, 'minY': minLat, 'maxX': maxLon, 'maxY': maxLat, 'srs': WGS84_EPSG_STR}))
                minLon = maxLon
            minLat = maxLat
            minLon = bbox['minX']
                                                
    return bboxes


def getBoundingBoxForShapefile(shapefileName, buffer=0.0):
    """ Return the bounding box, in WGS84 (EPSG:4326) coordinates, for the ESRI shapefile.  
        Assumes shapefile exists and is readable.
        Based on http://svn.osgeo.org/gdal/trunk/gdal/swig/python/samples/ogrinfo.py
   
        @param shapefileName String representing the path of the shapefile whose bounding box should be determined.
        @param buffer Float >= 0.0 representing number of degrees by which to buffer the bounding box; 0.0 = no buffer, 
        0.01 = 0.01 degree buffer
        
        @return A dict containing keys: minX, minY, maxX, maxY, srs, where srs='EPSG:4326'
    """
    assert(buffer >= 0.0)
    
    # Get spatial reference system for shapefile
    poDS = ogr.Open(shapefileName, True)
    assert(poDS.GetLayerCount() > 0)
    poLayer = poDS.GetLayer(0)
    assert(poLayer)
    srs_proj4 = poLayer.GetSpatialRef().ExportToProj4()
    
    # Setup Proj to convert to EPSG:4326 (WGS84)
    p_in = Proj(srs_proj4)
    p_out = Proj(init="EPSG:4326")
    
    # Get bounding box for shapefile
    (minX, maxX, minY, maxY) = poLayer.GetExtent()
    # Convert coordinates to EPSG:4326 (WGS84)
    (minX, minY) = transform(p_in, p_out, minX, minY)
    (maxX, maxY) = transform(p_in, p_out, maxX, maxY)
    
    bbox = dict({'minX': minX, 'minY': minY, 'maxX': maxX, 'maxY': maxY, 'srs': 'EPSG:4326'})
    bufferBoundingBox(bbox, buffer)
    
    return bbox


def bufferBoundingBox(bbox, buffer):
    """ Buffer the bounding by a given percentage
    
        @param bbox A dict containing keys: minX, minY, maxX, maxY, srs, where srs='EPSG:4326'
        @param buffer Float >= 0.0 representing number of degrees by which to buffer the bounding box; 0.0 = no buffer, 
        0.01 = 0.01 degree buffer
    """
    if buffer > 0.0:
        # Apply buffer
        minX = bbox['minX']
        minY = bbox['minY']
        maxX = bbox['maxX']
        maxY = bbox['maxY']
        minX = minX - buffer
        minY = minY - buffer
        maxX = maxX + buffer
        maxY = maxY + buffer
        # Correct any wrapping that occurred
        if minX < -180.0: minX = 360.0 + minX
        if minY < -90.0: minY = -90.0
        if maxX > 180.0: maxX = -360.0 + maxX
        if minY > 90.0: maxY = 90.0
        bbox['minX'] = minX
        bbox['minY'] = minY
        bbox['maxX'] = maxX
        bbox['maxY'] = maxY


def getMeterConversionFactorForLinearUnitOfGMLfile(gmlFilename):
    """ Get conversion factor for converting a GML file's linear unit into meters
    
        @param gmlFilename String representing the GML file
        
        @return Float representing the conversion factor
    
        @exception IOError(errno.EACCES) if the GML file cannot be opened
    """
    driver = ogr.GetDriverByName('GML')
    inDS = driver.Open(gmlFilename, 0)
    if inDS is None:
        raise IOError(errno.EACCES, "Unable to open GML file %s" %
                      gmlFilename)
    inLayer = inDS.GetLayer()
    soilSrs = inLayer.GetSpatialRef()
    if soilSrs == None:
        # Assume EPSG:4326 (WGS84 GCS)
        soilSrs = osr.SpatialReference()
        soilSrs.ImportFromEPSG(4326)
    return soilSrs.GetLinearUnits()


def getMeterConversionFactorForLinearUnitOfShapefile(shpFilename):
    """ Get conversion factor for converting a shapefile's linear unit into meters
    
        @param shpFilename String representing the name of the shapefile
        
        @return Float representing the conversion factor
    
        @exception IOError(errno.EACCES) if the shapefile cannot be opened
    """
    driver = ogr.GetDriverByName('ESRI Shapefile')
    inDS = driver.Open(shpFilename, 0)
    if inDS is None:
        raise IOError(errno.EACCES, "Unable to open shapefile %s" %
                      shpFilename)
    inLayer = inDS.GetLayer()
    soilSrs = inLayer.GetSpatialRef()
    if soilSrs == None:
        # Assume EPSG:4326 (WGS84 GCS)
        soilSrs = osr.SpatialReference()
        soilSrs.ImportFromEPSG(4326)
    return soilSrs.GetLinearUnits()


def getNodataValuesForRaster(filename):
    """ Get nodata value for each band in a raster.  Uses GDAL library
        Code adapted from: http://svn.osgeo.org/gdal/trunk/gdal/swig/python/samples/gdalinfo.py
        
        @param filename String representing the DEM file path
        
        @return List containing nodata values for each band
        
        @exception IOError if filename is not readable
    """
    nodata = []
    
    if not os.access(filename, os.R_OK):
        raise IOError(errno.EACCES, "Not allowed to read DEM %s to nodata value" %
                      filename)
        
    hDataset = gdal.Open(filename, gdal.GA_ReadOnly)
    if hDataset is not None:
        for iBand in range(hDataset.RasterCount):
            hBand = hDataset.GetRasterBand(iBand+1 )
            nodata.append( hBand.GetNoDataValue() )
    
    return nodata


def getSpatialReferenceForRaster(filename):
    """ Get pixel size and unit for DEM.  Uses GDAL library
        Code adapted from: http://svn.osgeo.org/gdal/trunk/gdal/swig/python/samples/gdalinfo.py
        
        @param filename String representing the DEM file path
        
        @return A tuple of the form: 
        (pixelWidth, pixelHeight, linearUnitsName, linearUnitsConversionFactor, WKT SRS string, EPSG SRS string)
        
        @exception IOError if filename is not readable
    """
    pixelWidth = None
    pixelHeight = None
    linearUnitsName = None
    linearUnitsConversionFactor = None
    pszProjection = None
    
    if not os.access(filename, os.R_OK):
        raise IOError(errno.EACCES, "Not allowed to read DEM %s to read spatial reference" %
                      filename)
    
    hDataset = gdal.Open(filename, gdal.GA_ReadOnly)

    if hDataset is not None:
        adfGeoTransform = hDataset.GetGeoTransform()
        if adfGeoTransform is not None:
            pixelWidth = abs(adfGeoTransform[1])
            pixelHeight = abs(adfGeoTransform[5])
        
        pszProjection = hDataset.GetProjectionRef()
        if pszProjection is not None:
            hSRS = osr.SpatialReference()
            if hSRS.ImportFromWkt(pszProjection) == gdal.CE_None:
                linearUnitsName = hSRS.GetLinearUnitsName()
                linearUnitsConversionFactor = hSRS.GetLinearUnits()
        
        if hSRS.GetAttrValue("AUTHORITY", 0) != None and hSRS.GetAttrValue("AUTHORITY", 1):
            epsgStr = "%s:%s" % ( hSRS.GetAttrValue("AUTHORITY", 0), hSRS.GetAttrValue("AUTHORITY", 1) )
        else:
            epsgStr = None
    return (pixelWidth, pixelHeight, linearUnitsName, linearUnitsConversionFactor, pszProjection, epsgStr)


def getDimensionsForRaster(filename):
    """ Get number of columns and rows for raster.  Uses GDAL library
        Code adapted from: http://svn.osgeo.org/gdal/trunk/gdal/swig/python/samples/gdalinfo.py
        
        @param filename String representing the DEM file to read pixel size and units
        
        @return A tuple of the form: 
        (columns, rows) or None if raster could not be opened
        
        @exception IOError if filename is not readable
    """
    columns = None
    rows = None
    
    if not os.access(filename, os.R_OK):
        raise IOError(errno.EACCES, "Not allowed to read DEM %s to read number of columns and rows" %
                      filename)
    
    hDataset = gdal.Open(filename, gdal.GA_ReadOnly)

    if hDataset is not None:
        columns = hDataset.RasterXSize
        rows = hDataset.RasterYSize
            
    return (columns, rows)


def getBoundingBoxForRaster(filename):
    """ Return the bounding box, in WGS84 (EPSG:4326) coordinates, for the raster dateset.  
        Assumes raster exists and is readable.
        Code adapted from: http://svn.osgeo.org/gdal/trunk/gdal/swig/python/samples/gdalinfo.py
        
        @param filename String representing the DEM file to read pixel size and units
        
        @return A tuple of the form: 
        (columns, rows) or None if raster could not be opened
        
        @exception IOError if filename is not readable
        @exception Exception if raster dataset failed to open
    """
    
    if not os.access(filename, os.R_OK):
        raise IOError(errno.EACCES, "Not allowed to read DEM %s to determine bounding box" %
                      filename)
    
    hDataset = gdal.Open(filename, gdal.GA_ReadOnly)

    if hDataset is None:
        raise Exception("Unable to open raster dataset")
    
    # Setup for translating from pixels to coordinates
    pszProjection = hDataset.GetProjectionRef()
    assert(pszProjection is not None)
    hProj = osr.SpatialReference(pszProjection)
    assert(hProj is not None)
    hLatLong = osr.SpatialReference()
    hLatLong.ImportFromEPSG(WGS84_EPSG)
    hTransform = osr.CoordinateTransformation( hProj, hLatLong )
    adfGeoTransform = hDataset.GetGeoTransform(can_return_null = True)
    assert(adfGeoTransform is not None)

    (minX, maxY) = _transformPixelsToCoordinates(hDataset, hTransform, adfGeoTransform,
                                                 0, 0)
    (maxX, minY) = _transformPixelsToCoordinates(hDataset, hTransform, adfGeoTransform,
                                                 hDataset.RasterXSize, hDataset.RasterYSize)

    return dict({'minX': float(minX), 'minY': float(minY), 'maxX': float(maxX), 'maxY': float(maxY), 'srs': 'EPSG:4326'})


def writeBboxPolygonToShapefile(bbox, outputDir, layerName, overwrite=True):
    """ Write bbox to a shapfile
    
        @param bbox A dict containing keys: minX, minY, maxX, maxY, srs, where srs='EPSG:4326'
        @param outputDir String representing the absolute/relative path of the directory into which shapefile should be written
        @param layerName String representing the name of the layer. Will be used as root of filename of output shapefile
        @param overwrite True if existing shapefile should be overwritten.
        
        @return String representing the name of shapefile created (not the absolute path)
        
        @raise IOError is output directory is not a writable directory
        @raise Exception if shapefile already exists
        @raise Exception is failed to create shapefile
    """
    pszDriverName = "ESRI Shapefile"
    shpFilename = "%s%sshp" % (layerName, os.extsep)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    shpFilepath = os.path.join(outputDir, shpFilename)
    if os.path.exists(shpFilepath):
        if not overwrite:
            raise Exception("Shapefile %s already exists in directory %s" % \
                            (shpFilename,outputDir) )
        else:
            deleteShapefile(shpFilepath)
    
    ogr.UseExceptions()
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(WGS84_EPSG)
    hDriver = ogr.GetDriverByName(pszDriverName)
    assert(hDriver is not None)
    hDS = hDriver.CreateDataSource(shpFilepath)
    assert(hDS is not None)
    hLayer = hDS.CreateLayer(layerName, srs, ogr.wkbPolygon)
    assert(hLayer is not None)
    hFeature = ogr.Feature(hLayer.GetLayerDefn())
    ring = ogr.Geometry(type=ogr.wkbLinearRing)
    ring.AddPoint(bbox['minX'], bbox['minY'])
    ring.AddPoint(bbox['minX'], bbox['maxY'])
    ring.AddPoint(bbox['maxX'], bbox['maxY'])
    ring.AddPoint(bbox['maxX'], bbox['minY'])
    poly = ogr.Geometry(type=ogr.wkbPolygon)
    poly.AssignSpatialReference(srs)
    poly.AddGeometry(ring)
    hFeature.SetGeometry(poly)
    if hLayer.CreateFeature(hFeature) != 0:
        raise Exception("Failed to create shapefile for bounding box")
    # Clean-up
    hFeature.Destroy()
    hDS.Destroy()
    
    return shpFilename


def writeCoordinatePairsToPointShapefile(outputDir, layerName, pointIDAttr, pointIDs, coordinates, overwrite=True):
    """ Write coordinates as a point shapefile
    
        @param outputDir String representing the absolute/relative path of the directory into which shapefile should be written
        @param layerName String representing the name of the layer. Will be used as root of filename of output shapefile
        @param pointIDAttr String representing name of the attribute used to identify points
        @param pointIDs List of strings representing IDs of coordinate pairs 
        @param coordinates List of tuples of floats of the form (longitude, latitude), in WGS84
        @param overwrite True if existing shapefile should be overwritten.
        
        @return String representing the name of shapefile created (not the absolute path)
        
        @raise IOError is output directory is not a writable directory
        @raise Exception if shapefile already exists
        @raise Exception is failed to create shapefile
    """
    pszDriverName = "ESRI Shapefile"
    shpFilename = "%s%sshp" % (layerName, os.extsep)
    
    numCoord = len(coordinates)
    assert(len(pointIDs) == numCoord)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    shpFilepath = os.path.join(outputDir, shpFilename)
    if os.path.exists(shpFilepath):
        if not overwrite:
            raise Exception("Shapefile %s already exists in directory %s" % \
                            (shpFilename,outputDir) )
        else:
            deleteShapefile(shpFilepath)
    
    ogr.UseExceptions()
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(WGS84_EPSG)
    hDriver = ogr.GetDriverByName(pszDriverName)
    assert(hDriver is not None)
    hDS = hDriver.CreateDataSource(shpFilepath)
    assert(hDS is not None)
    hLayer = hDS.CreateLayer(layerName, srs, ogr.wkbPoint)
    assert(hLayer is not None)
    
    # Create ID field
    hField = ogr.FieldDefn(pointIDAttr, ogr.OFTString)
    hField.SetWidth(32)
    assert(hLayer.CreateField(hField) == 0)
    
    i = 0
    while i < numCoord:
        x = coordinates[i][0]
        y = coordinates[i][1]
        hFeature = ogr.Feature(hLayer.GetLayerDefn())
        hFeature.SetField(pointIDAttr, pointIDs[i])
        hPoint = ogr.Geometry(ogr.wkbPoint)
        hPoint.AssignSpatialReference(srs)
        hPoint.SetPoint_2D(0, x, y)
        hFeature.SetGeometry(hPoint)
        assert(hLayer.CreateFeature(hFeature) == 0)
        hFeature.Destroy()
        i = i + 1
    
    hDS.Destroy()
    
    return shpFilename


def copyRasterToGeoTIFF(config, outputDir, inRasterPath, outRasterName):
    """ Copy input raster from a location outside of outputDir to a GeoTIFF format raster stored in outputDir
    
        @param config A Python ConfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_GDAL_TRANSLATE'
        @param outputDir String representing the absolute/relative path of the directory into which shapefile should be written
        @param inRasterPath String representing path of input raster
        @param outRasterName String representing name of output raster to be stored in outputDir
        
        @raise IOError if gdal_translate binary is not found/executable
        @raise IOError if output directory does not exist or not writable
        @raise IOError if input raster is not readable
    """
    gdalCmdPath = config.get('GDAL/OGR', 'PATH_OF_GDAL_TRANSLATE')
    if not os.access(gdalCmdPath, os.X_OK):
        raise IOError(errno.EACCES, "The gdal_translate binary at %s is not executable" %
                      gdalCmdPath)
    gdalCmdPath = os.path.abspath(gdalCmdPath)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    if not os.access(inRasterPath, os.R_OK):
        raise IOError(errno.EACCES, "Not allowed to read input raster %s" (inRasterPath,))
    
    outRasterPath = os.path.join(outputDir, outRasterName)
    
    gdalCommand = "%s -q -of GTiff -co 'COMPRESS=LZW' %s %s" % \
                  (gdalCmdPath, inRasterPath, outRasterPath)
    returnCode = os.system(gdalCommand)
    if returnCode != 0:
        raise Exception("GDAL command %s failed." % (gdalCommand,)) 
    
    

def _transformPixelsToCoordinates(hDataset, hTransform, adfGeoTransform, x, y):
    """ Adapted from http://svn.osgeo.org/gdal/trunk/gdal/swig/python/samples/gdalinfo.py
    
        @param hDataset A GDAL raster dataset object
        @param hTransform A GDAL transform object
        @param adfGeoTransform A GDAL geographic transform object
        @param x The X coordinate
        @param y The Y coordinate
        @return Tuple of floats representing longitude and latitude coordiates.
    """
    # Transform point into georeferenced coordiates
    dfGeoX = adfGeoTransform[0] + adfGeoTransform[1] * x \
            + adfGeoTransform[2] * y
    dfGeoY = adfGeoTransform[3] + adfGeoTransform[4] * x \
            + adfGeoTransform[5] * y
    # Transform georeferenced coordinates into lat/long
    coords = hTransform.TransformPoint(dfGeoX, dfGeoY, 0)
    return (coords[0], coords[1])
        
    
    