"""@package ecohydrolib.hydro1k.demtile
    
@brief Extract tile for HYDRO1k digital elevation model (DEM) stored locally

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
import os, errno

from ecohydrolib.spatialdata.utils import extractTileFromRaster
from ecohydrolib.spatialdata.utils import deleteGeoTiff


DEFAULT_CRS = 'EPSG:2163' # spatial reference of HYDRO1k North America

def getDEMForBoundingBox(config, outputDir, outDEMFilename, bbox, srs='EPSG:4326', overwrite=True):
    """ Extract tile of HYDRO1k digital elevation model (DEM) for bounding box.
    
        @param config Python ConfigParser containing the following sections and options:
            'GDAL/OGR', 'PATH_OF_GDAL_TRANSLATE'
            'HYDRO1k', 'PATH_OF_HYDRO1k_DEM'
        @param outputDir String representing the absolute/relative path of the directory into which output DEM should be written
        @param outDEMFilename String representing the name of the DEM file to be written
        @param bbox Dict representing the lat/long coordinates and spatial reference of the bounding box area
            for which the DEM is to be extracted.  The following keys must be specified: minX, minY, maxX, maxY, srs.
        @param srs String representing the spatial reference of the raster to be returned.
        @param overwrite Boolean value indicating whether or not the file indicated by filename should be overwritten.
            If False and filename exists, IOError exception will be thrown with errno.EEXIST
    
        @return True if DEM tile was created and False if not.
    """
    tileCreated = False
    assert('minX' in bbox)
    assert('minY' in bbox)
    assert('maxX' in bbox)
    assert('maxY' in bbox)
    assert('srs' in bbox)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    outDEMFilepath = os.path.join(outputDir, outDEMFilename)
    
    if os.path.exists(outDEMFilepath):
        if overwrite: 
            deleteGeoTiff(outDEMFilepath)
        else:
            raise IOError(errno.EEXIST, "DEM file %s already exists" % outDEMFilepath)
    
    hydro1kDEMFilePath = config.get('HYDRO1k', 'PATH_OF_HYDRO1k_DEM')
    if not os.access(hydro1kDEMFilePath, os.R_OK):
        raise IOError(errno.EACCES, "Unable to read HYDRO1k DEM located at %s" % (hydro1kDEMFilePath,))
    
    extractTileFromRaster(config, outputDir, hydro1kDEMFilePath, outDEMFilepath, bbox)
    tileCreated = os.path.exists(outDEMFilepath)
    
    return tileCreated

    
    
