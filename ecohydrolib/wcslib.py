"""@package ecohydrolib.wcslib
    
@brief Make WCS query for a raster data set

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
import sys

import socket
import httplib
import textwrap

from ecohydrolib.spatialdata.utils import deleteGeoTiff

CONTENT_TYPE_ERRORS = ['text/xml', 'application/vnd.ogc.se_xml;charset=ISO-8859-1']

_DEFAULT_CRS = 'EPSG:4326'
_BUFF_LEN = 4096 * 10

def getRasterForBoundingBox(config, outputDir, outFilename, host, urlProto, mimeType, bbox, coverage, srs, format, 
                            response_crs=None, store=None, resx=None, resy=None, interpolation=None, overwrite=True):
    """ Fetch a rater from WCS-compliant web service.
        Will write any error returned by query to sys.stderr.
    
        @param config A Python ConfigParser (not currently used)
        @param outputDir String representing the absolute/relative path of the directory into which output raster should be written
        @param outFilename String representing the name of the raster file to be written
        @param host String representing the host (e.g. 'webmap.ornl.gov', 'geobrain.laits.gmu.edu')
        @param urlProto String representing WCS service URL, must contain the following replacement fields:
            coverage, crs, bbox, format. May have the following fields: response_srs, store, resx, resy, interpolation
        @param mimeType String representing the MIME type expected for the response data
        @param bbox Dict representing the lat/long coordinates and spatial reference of the bounding box area
            for which the raster is to be extracted.  The following keys must be specified: minX, minY, maxX, maxY, srs.
        @param coverage String representing the raster source from which to get the raster coverage.  Must be a value listed in SUPPORTED_COVERAGE
        @param srs String representing the spatial reference of the raster to be returned.
        @param format String representing the MIME type of the raster format to be returned.  Must be a value listed in 
            SUPPORTED_FORMATS
        @param response_srs String representing the spatial reference of the raster to be returned.  
            Present for compatibility purposes and is ignored; only srs is used.
        @param store String present for compatibility with WCS4DEM.
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
    assert(format)
    assert(coverage)
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
    
    crs = bbox['srs']
    bboxStr = "%f,%f,%f,%f" % (bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY'])
 
    # coverage, crs, bbox, format. May have the following fields: response_srs, store, resx, resy, interpolation
    url = urlProto.format(coverage=coverage, crs=crs, bbox=bboxStr, format=format, 
                          response_crs=srs, store=store, resx=resx, resy=resy, interpolation=interpolation)
    urlFetched = "http://%s%s" % (host, url)

    conn = httplib.HTTPConnection(host)
    try:
        conn.request('GET', url)
        res = conn.getresponse(buffering=True)
    except socket.error as e:
        msg = "Encountered the following error when trying to read raster from %s. Error: %s.  Please try again later or contact the developer." % \
            (urlFetched, str(e) )
        sys.stderr.write( textwrap.fill(msg) )
        return ( dataFetched, urlFetched )
  
    if 200 != res.status:
        msg = "HTTP response %d %s encountered when querying %s.  Please try again later or contact the developer." % \
            (res.status, res.reason, urlFetched)
        sys.stderr.write( textwrap.fill(msg) ) 
        return ( dataFetched, urlFetched )
     
    contentType = res.getheader('Content-Type')
    
    if contentType == mimeType:
        # The data returned were of the type expected, read the data
        data = res.read(_BUFF_LEN)
        if data: 
            demOut = open(outFilepath, 'wb')
            dataFetched = True
            while data:
                demOut.write(data)
                data = res.read(_BUFF_LEN)
            demOut.close()
    elif contentType in CONTENT_TYPE_ERRORS:
        # Read the error and print to stderr
        msg = "The following error was encountered reading URL %s\n" %\
            (urlFetched, )
        sys.stderr.write( textwrap.fill(msg) )
        data = res.read(_BUFF_LEN)
        while data: 
            sys.stderr.write(data)
            sys.stderr.flush()
            data = res.read(_BUFF_LEN)
        sys.stderr.write('\n')
    else:
        msg = "Query for raster from URL %s returned content type %s, was expecting type %s.  Operation failed." % \
            (urlFetched, contentType, mimeType)
        sys.stderr.write( textwrap.fill(msg) )
        
    return ( dataFetched, urlFetched )