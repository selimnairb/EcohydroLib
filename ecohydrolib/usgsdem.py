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
import shutil
from math import floor, ceil
import xml.sax
import urlparse
import socket
import httplib
import tempfile
import textwrap

from pyproj import Proj
from pyproj import transform

import requests

from ecohydrolib.spatialdata.utils import resampleRaster
from ecohydrolib.spatialdata.utils import rescaleRaster
from ecohydrolib.spatialdata.utils import deleteGeoTiff


_BUFF_LEN = 4096 * 100

HOST = 'cida-test.er.usgs.gov'
URL_PROTO = "/nhdplus/geoserver/ows?service=WCS&version=1.1.1&request=GetCoverage&identifier={coverage}&boundingBox={x1},{y1},{x2},{y2},urn:ogc:def:crs:{bbox_srs}&gridBaseCRS=urn:ogc:def:crs:EPSG::5070&gridOffsets={xoffset},{yoffset}&format=image/tiff&store=true"

DEFAULT_SRS = 'EPSG:5070'
DEFAULT_RASTER_RESAMPLE_METHOD = 'cubic'
RASTER_RESAMPLE_METHOD = ['bilinear', 'cubic', 'cubicspline']
DEFAULT_COVERAGE = 'NED'
COVERAGES = {   'NHDPlus_hydroDEM':
                {'srs': DEFAULT_SRS,
                 'grid_origin': [-2356109.9999999995, 3506249.9999999967],
                 'grid_offset': [30.000000000000245, -30.00000000000047],
                 'grid_extent': [2419274.9999999995, 186285.00000000186]},
                'NED':
                {'srs': DEFAULT_SRS,
                 'grid_origin': [-2470950.0000000005, 3621360.000000002],
                 'grid_offset': [30.0, -30.0],
                 'grid_extent': [2258235.0000000377, 209654.99999994505]}
             }

CONTENT_TYPE_ERRORS = ['text/html']


class USGSDEMCoverageHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.in_coverage = False
        self.coverage_url = None
    def startElement(self, name, attrs):
        if not self.in_coverage:
            if name.lower() == 'wcs:coverage':
                self.in_coverage = True
                return
        else:
            if name.lower() == 'ows:reference':
                if not 'xlink:href' in attrs:
                    raise xml.sax.SAXParseException('xlink:href attribute not found in ows:reference element')
                self.coverage_url = attrs['xlink:href']
                return

def getDEMForBoundingBox(config, outputDir, outFilename, bbox, srs, coverage=DEFAULT_COVERAGE, 
                         resx=None, resy=None, interpolation=DEFAULT_RASTER_RESAMPLE_METHOD, scale=1.0, overwrite=True,
                         verbose=False, outfp=sys.stdout):
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
        @param interpolation String representing interpolation method.  Must be one of RASTER_RESAMPLE_METHOD.  Defaults to DEFAULT_RASTER_RESAMPLE_METHOD.
        @param scale Float representing factor by which to scale elevation data.  Defaults to 1.0.
        @param overwrite Boolean value indicating whether or not the file indicated by filename should be overwritten.
            If False and filename exists, IOError exception will be thrown with errno.EEXIST
        @param verbose Boolean True if detailed output information should be printed to outfp
        @param outfp File-like object to which verbose output should be printed
    
        @raise IOError if outputDir is not a writable directory
        @raise IOError if outFilename already exists and overwrite is False (see above)
        @raise Exception if there was an error making the WCS request
    
        @return Tuple(True if raster data were fetched and False if not, URL of raster fetched)
    """
    dataFetched = False
    assert(coverage in COVERAGES.keys())
    assert('minX' in bbox)
    assert('minY' in bbox)
    assert('maxX' in bbox)
    assert('maxY' in bbox)
    assert('srs' in bbox)
    assert(scale > 0.0)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    outFilepath = os.path.join(outputDir, outFilename)
    
    deleteOldfile = False
    if os.path.exists(outFilepath):
        if overwrite: 
            deleteOldfile = True
        else:
            raise IOError(errno.EEXIST, "Raster file %s already exists" % outFilepath)
     
    cov = COVERAGES[coverage]
    grid_origin = cov['grid_origin']
    grid_offset = cov['grid_offset']
    grid_extent = cov['grid_extent']
    s_srs = cov['srs']
    
    if resx is None:
        resx = abs(grid_offset[0])
    if resy is None:
        resy = abs(grid_offset[1])
    t_srs = srs

    # For requests, grid cell centers are used. Need to add half the grid_offset to the grid_origin
    grid_origin_0 = grid_origin[0] + grid_offset[0] / 2.0
    grid_origin_1 = grid_origin[1] + grid_offset[1] / 2.0
    
    p = Proj(init=DEFAULT_SRS)
    (x1, y1) = p(bbox['minX'], bbox['minY'])
    (x2, y2) = p(bbox['maxX'], bbox['maxY'])
    # Pad the width of the bounding box as the Albers transform results in regions of interest
    # that are a bit narrower than I would like, which risks watershed boundaries lying beyond
    # the DEM boundary.
    len_x = x2 - x1
    del_x = len_x * 0.30
    x1 = x1 - del_x
    x2 = x2 + del_x
    bbox_srs = DEFAULT_SRS
 
    # Find the number of grid cells from the grid origin to each edge of the request.
    # Multiply by the grid_offset and add the grid origin to get to the request location.
    xi1 = floor((x1 - grid_origin_0) / grid_offset[0]) * grid_offset[0] + grid_origin_0
    xi2 = ceil((x2 - grid_origin_0) / grid_offset[0]) * grid_offset[0] + grid_origin_0
    yi1 = floor((y1 - grid_origin_1) / grid_offset[1]) * grid_offset[1] + grid_origin_1
    yi2 = ceil((y2 - grid_origin_1) / grid_offset[1]) * grid_offset[1] + grid_origin_1
 
    # coverage, crs, bbox, format. May have the following fields: response_srs, store, resx, resy, interpolation
    url = URL_PROTO.format(coverage=coverage, x1=xi1, y1=yi1, x2=xi2, y2=yi2, bbox_srs=bbox_srs,
                           xoffset=grid_offset[0], yoffset=grid_offset[1])
    urlFetched = "http://%s%s" % (HOST, url)

    if verbose:
        outfp.write("Acquiring DEM data from {0} ...\n".format(urlFetched))

    # Make initial request, which will return the URL of our clipped coverage
    r = requests.get(urlFetched)
    if r.status_code != 200:
        raise Exception("Error fetching {url}, HTTP status code was {code} {reason}".format(urlFetched,
                                                                                            r.status_code,
                                                                                            r.reason))
    usgs_dem_coverage_handler = USGSDEMCoverageHandler()
    xml.sax.parseString(r.text, usgs_dem_coverage_handler)
    coverage_url = usgs_dem_coverage_handler.coverage_url
    if coverage_url is None:
        raise Exception("Unable to deteremine coverage URL from WCS server response.  Response text was: {0}".format(r.text))
    parsed_coverage_url = urlparse.urlparse(coverage_url)
    
    if verbose:
        outfp.write("Downloading DEM coverage from {0} ...\n".format(coverage_url))
    
    # Download coverage to tempfile
    tmp_dir = tempfile.mkdtemp()
    tmp_cov_name = os.path.join(tmp_dir, 'usgswcsdemtmp')
    tmp_out = open(tmp_cov_name, mode='w+b')
    
    conn = httplib.HTTPConnection(parsed_coverage_url.netloc)
    try:
        conn.request('GET', parsed_coverage_url.path)
        res = conn.getresponse(buffering=True)
    except socket.error as e:
        msg = "Encountered the following error when trying to read raster from %s. Error: %s.  Please try again later or contact the developer." % \
            (urlFetched, str(e) )
        raise Exception(msg)
  
    if 200 != res.status:
        msg = "HTTP response %d %s encountered when querying %s.  Please try again later or contact the developer." % \
            (res.status, res.reason, urlFetched)
        raise Exception(msg) 
     
    contentType = res.getheader('Content-Type')
    
    mimeType = 'image/tiff'
    if contentType.startswith(mimeType):
        # The data returned were of the type expected, read the data
        data = res.read(_BUFF_LEN)
        if data: 
            dataFetched = True
            while data:
                tmp_out.write(data)
                data = res.read(_BUFF_LEN)
            tmp_out.close()
    elif contentType.startswith(CONTENT_TYPE_ERRORS):
        # Read the error and print to stderr
        msg = "The following error was encountered reading WCS coverage URL %s\n\n" %\
            (coverage_url, )
        data = res.read(_BUFF_LEN)
        while data:
            msg += data 
        raise Exception(msg)
    else:
        msg = "Query for raster from URL %s returned content type %s, was expecting type %s. " + \
              " Operation failed." % \
            (coverage_url, contentType, mimeType)
        raise Exception(msg)

    # Rescale raster values if requested        
    if scale != 1.0:
        # Rescale values in raster
        if verbose:
            outfp.write("Rescaling raster values by factor {0}".format(scale))
        rescale_out = os.path.basename("{0}_rescale".format(tmp_cov_name))
        rescaleRaster(config, tmp_dir, tmp_cov_name, rescale_out, scale)
        tmp_cov_name = os.path.join(tmp_dir, rescale_out)
    
    if deleteOldfile:
        deleteGeoTiff(outFilepath)
    
    if verbose:
        msg = "Resampling raster from {s_srs} to {t_srs} " + \
              "with X resolution {resx} and Y resolution {resy}\n"
        outfp.write(msg.format(s_srs=s_srs,
                               t_srs=t_srs,
                               resx=resx,
                               resy=resy))
    
    # Re-sample to target spatial reference and resolution
    resampleRaster(config, outputDir, tmp_cov_name,  outFilename,
                   s_srs, t_srs, resx, resy, interpolation)
    
    # Delete temp directory
    shutil.rmtree(tmp_dir)
        
    return ( dataFetched, urlFetched )
