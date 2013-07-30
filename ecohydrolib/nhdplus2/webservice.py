"""@package ecohydrolib.nhdplus2.webservice
    
@brief Methods for querying the NHDPlus V2 data set via custom web service

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
import json
import textwrap
import tempfile, shutil

from ecohydrolib.spatialdata.utils import OGR_SHAPEFILE_DRIVER_NAME
from ecohydrolib.spatialdata.utils import OGR_DRIVERS

_DEFAULT_CRS = 'EPSG:4326'
_BUFF_LEN = 4096 * 10

HOST = 'ga-dev-wssi.renci.org'
URL_PROTO_GAGE_LOC = '/cgi-bin/LocateStreamflowGage?gageid={gageid}'
URL_PROTO_CATCHMENT = '/cgi-bin/GetCatchmentFeaturesForStreamflowGage?reachcode={reachcode}&measure={measure}'

CONTENT_TYPE = 'application/json'
CONTENT_TYPE_ERROR = 'text/plain'
RESPONSE_OK = 'OK'

class WebserviceError(Exception):
    def __init__(self, url, error):
        msg = "Encountered the following error when accessing URL %s, error: %s" % \
            (url, error)
        super(WebserviceError, self).__init__(msg)

def locateStreamflowGage(config, gageid):
    """ Query NHDPlus V2 web service for location information for streamflow gage
        listed in the NHDPlus V2 dataset
    
        @param config A Python ConfigParser (not currently used)
        @param gageid String representing streamflow gage ID (e.g. typically USGS site identifier)
        
        @return Tuple(A dictionary with keys: message, measure, reachcode, gage_lon, gage_lat 
        if location data were fetched or dictionary with key 'message' if not, URL of the request)
    """
    response = {}
    
    url = URL_PROTO_GAGE_LOC.format(gageid=gageid)
    urlFetched = "http://%s%s" % (HOST, url)
    
    conn = httplib.HTTPConnection(HOST)
    try:
        conn.request('GET', url)
        res = conn.getresponse(buffering=False)
    except socket.error as e:
        msg = "Encountered the following error when trying to get gage location from %s. Error: %s.  Please try again later or contact the developer." % \
            (urlFetched, str(e) )
        sys.stderr.write( textwrap.fill(msg) )
        return ( response, urlFetched )
    
    if 200 != res.status:
        msg = "HTTP response %d %s encountered when querying %s.  Please try again later or contact the developer." % \
            (res.status, res.reason, urlFetched)
        sys.stderr.write( textwrap.fill(msg) ) 
        return ( response, urlFetched )
    
    contentType = res.getheader('Content-Type')
    
    if contentType.find(CONTENT_TYPE) != -1:
        # The data returned were of the type expected, read the data
        response = json.load(res)
            
    else:
        msg = "Query from URL %s returned content type %s, was expecting type %s.  Operation failed." % \
            (urlFetched, contentType, CONTENT_TYPE)
        sys.stderr.write( textwrap.fill(msg) )
    
    return (response, urlFetched)

def getCatchmentFeaturesForStreamflowGage(config, outputDir,
                                          catchmentFilename, reachcode, measure,
                                          format=OGR_SHAPEFILE_DRIVER_NAME):
    """ Query NHDPlus V2 web service for features (in WGS 84) for 
        the drainage area associated with a given NHD (National 
        Hydrography Dataset) streamflow gage identified by a reach 
        code and measure.
        
        @param config A Python ConfigParser (not currently used)
        @param outputDir String representing the absolute/relative
        path of the directory into which output rasters should be
        written
        @param format String representing OGR driver to use
        @param catchmentFilename String representing name of file to
        save catchment features to.  The appropriate extension will be added to the file name
        @param reachcode String representing NHD streamflow gage 
        @param measure Float representing the measure along reach
        where Stream Gage is located in percent from downstream
        end of the one or more NHDFlowline features that are
        assigned to the ReachCode (see NHDPlusV21 GageLoc table)
        
        @return Tuple(String representing the name of the dataset in outputDir created to hold
        the features, URL of the request)
         
        @raise IOError(errno.EACCESS) if OGR binary is not executable
        @raise IOError(errno.ENOTDIR) if outputDir is not a directory
        @raise IOError(errno.EACCESS) if outputDir is not writable
        @raise Exception if output format is not known
        @raise WebserviceError if an error occurred calling the web service
    """
    ogrCmdPath = config.get('GDAL/OGR', 'PATH_OF_OGR2OGR')
    if not os.access(ogrCmdPath, os.X_OK):
        raise IOError(errno.EACCES, "The ogr2ogr binary at %s is not executable" %
                      ogrCmdPath)
    ogrCmdPath = os.path.abspath(ogrCmdPath)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    if not format in OGR_DRIVERS.keys():
        raise Exception("Output format '%s' is not known" % (format,) )
    
    catchmentFilename ="%s%s%s" % ( catchmentFilename, os.extsep, OGR_DRIVERS[format] )
    catchmentFilepath = os.path.join(outputDir, catchmentFilename)
    
    url = URL_PROTO_CATCHMENT.format( reachcode=reachcode, measure=str(measure) )
    urlFetched = "http://%s%s" % (HOST, url)
    
    conn = httplib.HTTPConnection(HOST)
    try:
        conn.request('GET', url)
        res = conn.getresponse(buffering=True)
    except socket.error as e:
        raise WebserviceError(urlFetched, str(e))
    
    if 200 != res.status:
        error = "%d %s" % (res.status, res.reason)
        raise WebserviceError(urlFetched, error)
    
    contentType = res.getheader('Content-Type')
    
    if contentType.find(CONTENT_TYPE_ERROR) != -1:
        error = res.read()
        raise WebserviceError(urlFetched, error)
    
    elif contentType.find(CONTENT_TYPE) != -1:
        # The data returned were of the type expected, read the data
        tmpdir = tempfile.mkdtemp()
        
        failure = False
        data = res.read(_BUFF_LEN)
        if data:            
            tmpfile = os.path.join( tmpdir, 'catchment.geojson' )
            f = open(tmpfile, 'wb')
            while data:
                f.write(data)
                data = res.read(_BUFF_LEN)
            f.close()
            # Convert GeoJSON to ESRI Shapfile using OGR
            ogrCommand = "%s -s_srs EPSG:4326 -t_srs EPSG:4326 -f '%s' %s %s" % (ogrCmdPath, format, catchmentFilepath, tmpfile)
            os.system(ogrCommand)
            if not os.path.exists(catchmentFilepath):
                failure = False
        
        shutil.rmtree(tmpdir)
        if failure:
            raise WebserviceError(urlFetched, "Failed to store catchment features in file %s" % (catchmentFilepath,) )
    else:
        error = "Recieved content type %s but expected type %s" % (contentType, CONTENT_TYPE)
        raise WebserviceError(urlFetched, error)
    
    return (catchmentFilename, urlFetched)