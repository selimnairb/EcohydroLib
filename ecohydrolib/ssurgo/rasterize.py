"""@package ecohydrolib.ssurgo.rasterize
    
@brief Rasterize SSURGO features

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
"""
import os.path, errno
import osr

from ecohydrolib.spatialdata.utils import deleteGeoTiff
from ecohydrolib.spatialdata.utils import getSpatialReferenceForRaster
from ecohydrolib.spatialdata.utils import getMeterConversionFactorForLinearUnitOfShapefile
from ecohydrolib.spatialdata.utils import getMeterConversionFactorForLinearUnitOfGMLfile

import attributequery

RASTER_ATTRIBUTES = attributequery.ATTRIBUTE_LIST_NUMERIC
# Depth to bed rock from MapunitPolyExtended
RASTER_ATTRIBUTES.append('brockdepmin')


def deleteSoilRasters(context, manifest):
    """ Delete soil raster maps stored in a project
    
        @param context Context object containing projectDir, the path of the project whose 
        metadata store is to be read from
        @param manifest Dict containing manifest entries.  Files associted with entries
        whose key begins with 'soil_raster_' will be deleted
    """
    for entry in manifest.keys():
        if entry.find('soil_raster_') == 0:
            filePath = os.path.join( context.projectDir, manifest[entry] )
            deleteGeoTiff(filePath)


def rasterizeSSURGOFeatures(config, outputDir, featureFilename, featureLayername, featureAttrList, \
                            getResolutionFromRasterFileNamed=None, rasterResolutionX=None, rasterResolutionY=None):
    """ Create raster maps, in GeoTIFF format, for SSURGO attributes associated with SSURGO MapunitPoly/MapunitPolyExtended features
        
        @note Will silently exit if rasters already exist.
        @note If getResolutionFromRasterFileNamed as well as rasterResolutionX and rasterResolutionY are specified,
        output raster resolution will be determined from the file named by getResolutionFromRasterFileNamed. 
        
        @param config onfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_GDAL_RASTERIZE'
        @param outputDir String representing the absolute/relative path of the directory into which output rasters should be written
        @param featureFilename String representing the absolute/relative path of the input feature in ESRI shapefile or OGC GML format
        @param featureLayername String representing the name of feature layer whose features are to be rasterize
        @param featureAttrList List containing the SSURGO attributes for which raster maps are to be created
        @param getResolutionFromRasterFileNamed String representing the absolute path of an existing raster file from which the
            output raster resolution should be determined
        @param rasterResolutionX Float representing the X resolution of the output rasters
        @param rasterResolutionY Float representing the Y resolution of the output rasters
        
        @return Dictionary containing the keys for each soil attribute and values of the names of the raster files generated for that attribute
        
        @exception ConfigParser.NoSectionError
        @exception ConfigParser.NoOptionError
        @exception Exception if featureFilename is neither a SHP nor a GML file
        @exception IOError(errno.ENOTDIR) if outputDir is not a directory
        @exception IOError(errno.EACCESS) if outputDir is not writable
        @exception IOError(errno.EACCESS) if featureFilename is not readable
        @exception IOError(errno.ENOENT) if featureFilename is not a file
        @exception IOError(errno.EACCES) if getResolutionFromRasterFileNamed is not readable
        @exception ValueError if rasterResolutionX or rasterResolutionY are not floating point numbers greater than 0
        @exception Exception if a gdal_rasterize command fails
    """
    gdalCmdPath = config.get('GDAL/OGR', 'PATH_OF_GDAL_RASTERIZE')
    if not os.access(gdalCmdPath, os.X_OK):
        raise IOError(errno.EACCES, "The gdal_rasterize binary at %s is not executable" %
                      gdalCmdPath)
    gdalCmdPath = os.path.abspath(gdalCmdPath)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    featureFilepath = os.path.join(outputDir, featureFilename)
    if not os.access(featureFilepath, os.R_OK):
        raise IOError(errno.EACCES, "Not allowed to read feature file %s" % (featureFilepath,))
    if not os.path.isfile(featureFilepath):
        raise IOError(errno.ENOENT, "Feature file %s does not exist" % (featureFilepath,))
    
    if getResolutionFromRasterFileNamed is None:
        rasterResolutionX = float(rasterResolutionX)
        if rasterResolutionX <= 0.0:
            raise ValueError("rasterResolutionX must be > 0.0")
        rasterResolutionY = float(rasterResolutionY)
        if rasterResolutionY <= 0.0:
            raise ValueError("rasterResolutionY must be > 0.0")
    else:
        if not os.access(getResolutionFromRasterFileNamed, os.R_OK):
            raise IOError(errno.EACCES, "Not allowed to read existing raster file %s from which to get resolution" % \
                          (getResolutionFromRasterFileNamed))

    featureType = os.path.splitext(featureFilepath)[1].lstrip('.').upper()

    # Get conversion factor for converting soil feature linear unit into meters
    if featureType == "GML":
        soilMeterConvFactor = getMeterConversionFactorForLinearUnitOfGMLfile(featureFilepath)
    elif featureType == "SHP":
        soilMeterConvFactor = getMeterConversionFactorForLinearUnitOfShapefile(featureFilepath)
    else:
        raise Exception("Argument featureFilename must be either a GML or SHP file")
        
    # Determine soil property raster map resolution, in the same linear units as soil feature layer
    if getResolutionFromRasterFileNamed is not None:
        # Use DEM raster resolution as soil property raster resolution
        #sys.stderr.write("Using input raster resolution for soil property rasters ...\n")
        demPixelSizeAndUnits = getSpatialReferenceForRaster(getResolutionFromRasterFileNamed)
        # Default, DEM raster linear unit is the same as soil feature linear units
        rasterResolutionX = demPixelSizeAndUnits[0]
        rasterResolutionY = demPixelSizeAndUnits[1]
        # Get DEM raster linear units
        demSrs = osr.SpatialReference()
        if demSrs.ImportFromWkt(demPixelSizeAndUnits[4]) == 0: # OGRERR_NONE = 0
            #sys.stderr.write("Spatial reference found for DEM, converting DEM linear units to soil feature linear units\n")
            demMeterConvFactor = demSrs.GetLinearUnits()
            if soilMeterConvFactor != demMeterConvFactor:
                # Soil feature linear units differ from DEM linear units, convert to meters
                rasterResolutionX = (demPixelSizeAndUnits[0] * demMeterConvFactor)
                rasterResolutionY = (demPixelSizeAndUnits[1] * demMeterConvFactor)
        else:
            pass
            #sys.stderr.write("No spatial reference found for DEM, assuming DEM linear units are the same as soil feature linear units\n")
    else:
        # Use user-specified soil raster resolution, but convert from meters into soil feature linear units
        pass
        #sys.stderr.write("Using user-supplied resolution, %d meters x %d meters, for soil property rasters ...\n" % (rasterResolutionX, rasterResolutionY))
        
    # Convert output raster resolution from meters into the linear units of the soil feature shapefile 
    rasterResolutionX = rasterResolutionX / soilMeterConvFactor
    rasterResolutionY = rasterResolutionY / soilMeterConvFactor
    
    # Build base filename for all output raster maps
    rasterFilenameProto = os.path.splitext(featureFilename)[0]
    
    filesCreated = dict()
    
    # Rasterize soil feature attributes using gdal_rasterize
    for attr in featureAttrList:
        rasterFilename = "%s_%s.tif" % (rasterFilenameProto, attr)
        filesCreated[attr] = rasterFilename
        rasterFilepath = os.path.join(outputDir, rasterFilename)
        if not os.path.exists(rasterFilepath):
            gdalCommand = "%s -q -of GTiff -co 'COMPRESS=LZW' -tr %d %d -a_nodata -9999 -a %s -l %s %s %s" % (gdalCmdPath, rasterResolutionX, rasterResolutionY, attr, featureLayername, featureFilepath, rasterFilepath)
            #print gdalCommand
            returnCode = os.system(gdalCommand)
            if returnCode != 0:
                raise Exception("GDAL command %s failed.  Check spatial reference system of input vector dataset (geographic coordinate systems may not work)." % (gdalCommand,))
    return filesCreated  
        