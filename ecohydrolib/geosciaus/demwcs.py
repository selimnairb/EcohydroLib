"""@package ecohydrolib.geosciaus.demwcs
    
@brief Query DEM data from WCS service provided by Geoscience Australia

This software is provided free of charge under the New BSD License. Please see
the following license information:

Copyright (c) 2014, University of North Carolina at Chapel Hill
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

COVERAGE_SRTM_1DEG_AUS = 'dem_1s'
COVERAGE_SRTM_1DEG_AUS_HYDRO = 'dem_h_1s'
COVERAGE_SRTM_1DEG_AUS_SMOOTH = 'dem_s_1s'
SUPPORTED_COVERAGE = [COVERAGE_SRTM_1DEG_AUS, COVERAGE_SRTM_1DEG_AUS_HYDRO, COVERAGE_SRTM_1DEG_AUS_SMOOTH]
COVERAGE_DESC = {COVERAGE_SRTM_1DEG_AUS: '1 second SRTM Digital Elevation Model of Australia', 
                 COVERAGE_SRTM_1DEG_AUS_HYDRO: '1 second SRTM Digital Elevation Model - Hydrologically Enforced', 
                 COVERAGE_SRTM_1DEG_AUS_SMOOTH: '1 second SRTM Digital Elevation Model - Smoothed'}

FORMAT_GEOTIFF = 'GeoTIFF'
FORMAT_NITF = 'NITF'
FORMAT_HDF = 'HDF'
SUPPORTED_FORMATS = [FORMAT_GEOTIFF, FORMAT_NITF, FORMAT_HDF]

MIME_TYPE = {FORMAT_GEOTIFF: 'image/tiff',
             FORMAT_NITF: 'application/x-nitf',
             FORMAT_HDF: 'application/x-hdf'
             }

# Example URL http://www.ga.gov.au/gisimg/services/topography/dem_h_1s/ImageServer/WCSServer?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage&COVERAGE=1&FORMAT=GeoTIFF&BBOX=147.539,-37.024,147.786,-36.830&RESX=0.000277777777778&RESY=0.000277777777778&CRS=EPSG:4283&RESPONSE_CRS=EPSG:4326&INTERPOLATION=bilinear&Band=1
HOST = 'www.ga.gov.au'
#URL_PROTO = '/cgi-bin/gbwcs-dem?service=wcs&version=1.0.0&request=getcoverage&coverage={coverage}&crs={crs}&bbox={bbox}&response_crs={response_crs}&format={format}&store={store}'
URL_PROTO = '/gisimg/services/topography/{coverage}/ImageServer/WCSServer?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage&COVERAGE=1&FORMAT={format}&BBOX={bbox}&RESX=0.000277777777778&RESY=0.000277777777778&CRS={crs}&RESPONSE_CRS={response_crs}&INTERPOLATION=bilinear&Band=1'

def getDEMForBoundingBox(config, outputDir, outDEMFilename, bbox, coverage=COVERAGE_SRTM_1DEG_AUS, srs='EPSG:4326', fmt=FORMAT_GEOTIFF, overwrite=True):
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
    assert(fmt in SUPPORTED_FORMATS)
    assert(coverage in SUPPORTED_COVERAGE)
    return getRasterForBoundingBox(config, outputDir, outDEMFilename, HOST, URL_PROTO, MIME_TYPE[fmt], bbox, coverage, srs, fmt,
                                   response_crs=srs, store=False, overwrite=overwrite)
    