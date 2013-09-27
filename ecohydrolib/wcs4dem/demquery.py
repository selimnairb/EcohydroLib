"""@package ecohydrolib.wcs4dem.demquery
    
@brief Query NASA EOS Education Alliance (NEHEA) GeoBrain for DEM data

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

COVERAGE_NED_30m_USA = 'NED_30m_USA'
COVERAGE_SRTM_30m_USA = 'SRTM_30m_USA'
COVERAGE_SRTM_90m_USA = 'SRTM_90m_Global'
COVERAGE_GTOPO_30arc_GLOBAL = 'GTOPO_30arc_Global'
SUPPORTED_COVERAGE = [COVERAGE_NED_30m_USA, COVERAGE_SRTM_30m_USA, COVERAGE_SRTM_90m_USA, COVERAGE_GTOPO_30arc_GLOBAL]

FORMAT_GEOTIFF = 'image/geotiff'
FORMAT_NETCDF = 'image/netcdf'
FORMAT_PNG = 'image/PNG'
FORMAT_JPEG = 'image/JPEG'
FORMAT_JP2000 = 'image/JPEG2000'
FORMAT_HDF4 = 'image/HDF4IMAGE'
SUPPORTED_FORMATS = [FORMAT_GEOTIFF, FORMAT_NETCDF, FORMAT_PNG, FORMAT_JPEG, FORMAT_JP2000, FORMAT_HDF4]

MIME_TYPE = 'application/image'

# Example URL /cgi-bin/gbwcs-dem?service=wcs&version=1.0.0&request=getcoverage&coverage=SRTM_90m_Global&bbox=-90,38,-89,39&crs=epsg:4326&format=image/geotiff&store=true
HOST = 'geobrain.laits.gmu.edu'
URL_PROTO = '/cgi-bin/gbwcs-dem?service=wcs&version=1.0.0&request=getcoverage&coverage={coverage}&crs={crs}&bbox={bbox}&response_crs={response_crs}&format={format}&store={store}'

def getDEMForBoundingBox(config, outputDir, outDEMFilename, bbox, coverage=COVERAGE_NED_30m_USA, srs='EPSG:4326', format=FORMAT_GEOTIFF, overwrite=True):
    """ Fetch a digital elevation model (DEM) from the GeoBrain WCS4DEM WCS-compliant web service.
        Will write any error returned by query to sys.stderr.
    
        @param config A Python ConfigParser (not currently used)
        @param outputDir String representing the absolute/relative path of the directory into which output DEM should be written
        @param outDEMFilename String representing the name of the DEM file to be written
        @param bbox Dict representing the lat/long coordinates and spatial reference of the bounding box area
            for which the DEM is to be extracted.  The following keys must be specified: minX, minY, maxX, maxY, srs.
        @param coverage String representing the DEM source from which to get the DEM coverage.  Must be a value listed in SUPPORTED_COVERAGE
        @param srs String representing the spatial reference of the raster to be returned.
        @param format String representing the MIME type of the raster format to be returned.  Must be a value listed in 
            SUPPORTED_FORMATS
        @param overwrite Boolean value indicating whether or not the file indicated by filename should be overwritten.
            If False and filename exists, IOError exception will be thrown with errno.EEXIST
    
        @raise IOError if outputDir is not a writable directory
        @raise IOError if outDEMFilename already exists and overwrite is False (see above)
    
        @return Tuple(True if DEM data were fetched and False if not, URL of DEM fetched)
    """
    assert(format in SUPPORTED_FORMATS)
    assert(coverage in SUPPORTED_COVERAGE)
    return getRasterForBoundingBox(config, outputDir, outDEMFilename, HOST, URL_PROTO, MIME_TYPE, bbox, coverage, srs, format,
                                   response_crs=srs, store=False, overwrite=overwrite)
    