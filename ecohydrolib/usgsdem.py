"""@package ecohydrolib.wcslib
    
@brief Make WCS 1.1.1 query for DEM data hosted by U.S. Geological Survey

This software is provided free of charge under the New BSD License. Please see
the following license information:

Copyright (c) 2015, University of North Carolina at Chapel Hill
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
#from __future__ import division
import os, errno
import sys
from math import floor, ceil
import socket
import httplib
import textwrap

from pyproj import Proj

from ecohydrolib.spatialdata.utils import deleteGeoTiff


_BUFF_LEN = 4096 * 10

HOST = 'cida-test.er.usgs.gov'
URL_PROTO = "/nhdplus/geoserver/ows?service=WCS&version=1.1.1&request=GetCoverage&identifier={coverage}&boundingBox={x1},{y1},{x2},{y2},urn:ogc:def:crs:EPSG::5070&gridBaseCRS=urn:ogc:def:crs:EPSG::5070&gridOffsets={xoffset},{yoffset}&format=image/tiff&store=true"

COVERAGES = {   'NHDPlus_hydroDEM':
                {'grid_origin': [-2356109.9999999995, 3506249.9999999967],
                 'grid_offset': [30.000000000000245, -30.00000000000047],
                 'grid_extent': [2419274.9999999995, 186285.00000000186]},
                'NED':
                {'grid_origin': [-2470950.0000000005, 3621360.000000002],
                 'grid_offset': [30.0, -30.0],
                 'grid_extent': [2258235.0000000377, 209654.99999994505]}
             }

CONTENT_TYPE_ERRORS = ['application/xml']

def getDEMForBoundingBox(config, outputDir, outFilename, bbox, srs, coverage='NHDPlus_hydroDEM', 
                         resx=None, resy=None, interpolation=None, overwrite=True):
    """ Fetch U.S. 1/3 arcsecond DEM data hosted by U.S. Geological Survey using OGC WCS 1.1.1 query.
    
        @note Adapted from code provided by dblodgett@usgs.gov.
    
        @param config A Python ConfigParser (not currently used)
        @param outputDir String representing the absolute/relative path of the directory into which output raster should be written
        @param outFilename String representing the name of the raster file to be written
        @param bbox Dict representing the lat/long coordinates and spatial reference of the bounding box area
            for which the raster is to be extracted.  The following keys must be specified: minX, minY, maxX, maxY, srs.
        @param srs String representing the spatial reference of the raster to be returned.
        @param coverage String representing the raster source from which to get the raster coverage.  Must be one of: NHDPlus_hydroDEM, NED
        @param resx Float representing the X resolution of the raster(s) to be returned
        @param resy Float representing the Y resolution of the raster(s) to be returned
        @param interpolation String representing interpolation method.
        @param overwrite Boolean value indicating whether or not the file indicated by filename should be overwritten.
            If False and filename exists, IOError exception will be thrown with errno.EEXIST
    
        @raise IOError if outputDir is not a writable directory
        @raise IOError if outFilename already exists and overwrite is False (see above)
    
        @return Tuple(True if raster data were fetched and False if not, URL of raster fetched)
    """
    dataFetched = False
    assert(coverage in COVERAGES.keys())
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
    
    outFilepath = os.path.join(outputDir, outFilename)
    
    if os.path.exists(outFilepath):
        if overwrite: 
            deleteGeoTiff(outFilepath)
        else:
            raise IOError(errno.EEXIST, "Raster file %s already exists" % outFilepath)
    
    #crs = bbox['srs']
    #bboxStr = "%f,%f,%f,%f" % (bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY'])
    
    cov = COVERAGES[coverage]
    grid_origin = cov['grid_origin']
    grid_offset = cov['grid_offset']
    grid_extent = cov['grid_extent']

    # For requests, grid cell centers are used. Need to add half the grid_offset to the grid_origin
    grid_origin_0 = grid_origin[0] + grid_offset[0] / 2.0
    grid_origin_1 = grid_origin[1] + grid_offset[1] / 2.0
    
    x_len = (grid_extent[0] - grid_origin_0) / grid_offset[0]
    y_len = (grid_extent[1] - grid_origin_1) / grid_offset[1]
    
    # Fix the grid extent
    grid_extent_0 = grid_origin_0 + grid_offset[0] * x_len
    grid_extent_1 = grid_origin_1 + grid_offset[1] * y_len
    
    p=Proj(init="EPSG:5070")
    (x1, y1) = p(bbox['minX'], bbox['minY'])
    (x2, y2) = p(bbox['maxX'], bbox['maxY'])
 
    # Find the number of grid cells from the grid origin to each edge of the request.
    # Multiply by the grid_offset and add the grid origin to get to the request location.
    xi1 = floor((x1 - grid_origin_0) / grid_offset[0]) * grid_offset[0] + grid_origin_0
    xi2 = ceil((x2 - grid_origin_0) / grid_offset[0]) * grid_offset[0] + grid_origin_0
    yi1 = floor((y1 - grid_origin_1) / grid_offset[1]) * grid_offset[1] + grid_origin_1
    yi2 = ceil((y2 - grid_origin_1) / grid_offset[1]) * grid_offset[1] + grid_origin_1
 
    # coverage, crs, bbox, format. May have the following fields: response_srs, store, resx, resy, interpolation
    url = URL_PROTO.format(coverage=coverage, x1=xi1, y1=yi1, x2=xi2, y2=yi2, 
                           xoffset=grid_offset[0], yoffset=grid_offset[1])
    urlFetched = "http://%s%s" % (HOST, url)

    print urlFetched
    
        
    return ( dataFetched, urlFetched )