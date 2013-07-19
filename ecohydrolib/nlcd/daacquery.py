"""@package ecohydrolib.nlcd.daacquery
    
@brief Query NLCD data from ORNL Distributed Active Archive Center for 
Biogeochemical Dynamics

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
from ecohydrolib.wcslib import getRasterForBoundingBox

SUPPORTED_COVERAGE = { 'NLCD2001': '10009_1',
              'NLCD2006': '10009_14' }

SUPPORTED_FORMATS = ['GeoTIFF_BYTE']
MIME_TYPE = 'image/tiff'
INTERPOLATION = 'NEAREST'

# Example URL http://webmap.ornl.gov/ogcbroker/wcs?originator=SDAT&service=WCS&version=1.0.0&request=GetCoverage&coverage=10009_14&crs=EPSG:1020031&bbox=1220972.0103093,1646432.4742268,1250882.0103093,1671362.4742268&resx=30&resy=30&format=GeoTIFF_BYTE&interpolation=NEAREST
HOST = 'webmap.ornl.gov'
URL_PROTO = '/ogcbroker/wcs?originator=SDAT&service=WCS&version=1.0.0&request=GetCoverage&coverage={coverage}&crs={crs}&bbox={bbox}&response_crs={response_crs}&resx={resx}&resy={resy}&format={format}&interpolation={interpolation}'

def getNLCDForBoundingBox(config, outputDir, outNLCDFilename, bbox, resx, resy, coverage='NLCD2006', srs='EPSG:4326', format='GeoTIFF_BYTE', overwrite=True):
    """ Fetch a NLCD land cover data from ORNL Distributed Active Archive Center for 
        Biogeochemical Dynamics WCS-compliant web service.
        
        Will write any error returned by query to sys.stderr.
    
        @param config A Python ConfigParser (not currently used)
        @param outputDir String representing the absolute/relative path of the directory into which output DEM should be written
        @param outNLCDFilename String representing the name of the NLCD raster file to be written
        @param bbox Dict representing the lat/long coordinates and spatial reference of the bounding box area
            for which the NLCD data are to be extracted.  The following keys must be specified: minX, minY, maxX, maxY, srs.
        @param resx Float representing X resolution of NLCD data to be returned in units of srs
        @param resy Float representing Y resolution of NLCD data to be returned in units of srs
        @param coverage String representing the NLCD version to get.  Must be a value listed in SUPPORTED_COVERAGE
        @param srs String representing the spatial reference of the raster to be returned.
        @param format String representing the type of the raster format to be returned.  Must be a value listed in 
            SUPPORTED_FORMATS
        @param overwrite Boolean value indicating whether or not the file indicated by filename should be overwritten.
            If False and filename exists, IOError exception will be thrown with errno.EEXIST
    
        @raise IOError if outputDir is not a writable directory
        @raise IOError if outNLCDFilename already exists and overwrite is False (see above)
    
        @return Tuple(True if DEM data were fetched and False if not, URL of DEM fetched)
    """
    assert(format in SUPPORTED_FORMATS)
    assert(coverage in SUPPORTED_COVERAGE.keys())
    return getRasterForBoundingBox(config, outputDir, outNLCDFilename, HOST, URL_PROTO, MIME_TYPE, bbox, SUPPORTED_COVERAGE[coverage], srs, format,
                                   response_crs=srs, store=None, resx=resx, resy=resy, interpolation=INTERPOLATION, overwrite=overwrite)