"""@package ecohydrolib.climatedata.ghcndquery
    
@brief Query NCDC Global Historical Climatology Network dataset for daily
climate data

@note Requires pyspatialite 3.0.1

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
import re
import httplib
from pyspatialite import dbapi2 as spatialite


# Example URL http://www1.ncdc.noaa.gov/pub/data/ghcn/daily/all/US1NCDH0006.dly
HOST = 'www1.ncdc.noaa.gov'
URL_PROTO = '/pub/data/ghcn/daily/all/{station_id}.dly'

_SRS = int(4326)
_BUFF_LEN = 4096 * 10


def findStationsWithinBoundingBox(config, bbox):
    """ Find stations that lie within a bounding box
    
        @param config ConfigParser containing the section 'GHCND' and option 
        'PATH_OF_STATION_DB'
        @param bbox A dict containing keys: minX, minY, maxX, maxY, srs, where srs='EPSG:4326'
        
        @return A list of GHCN station attributes for each station within the bounding box:
        [id, lat, lon, elevation, name]
        
        @code
        import os
        import ConfigParser
        from ecohydrolib.metadata import GenericMetadata
        from ecohydrolib.climatedata.ghcndquery import findStationsWithinBoundingBox
        studyArea = GenericMetadata.readStudyAreaEntries(projectDir)
        bbox = studyArea['bbox_wgs84'].split()
        bbox = dict({'minX': float(bbox[0]), 'minY': float(bbox[1]), 'maxX': float(bbox[2]), 'maxY': float(bbox[3]), 'srs': 'EPSG:4326'})
            
        configFile = os.environ['ECOHYDROWORKFLOW_CFG']
        config = ConfigParser.RawConfigParser()
        config.read(configFile)
        
        stations = findStationsWithinBoundingBox(config,bbox)
        @endcode 
    """
    stations = []
    pattern = re.compile("^POINT\((-?\d+\.?\d*) (-?\d+\.?\d*)\)$")
    
    ghcnDB = config.get('GHCND', 'PATH_OF_STATION_DB')
    
    conn = spatialite.connect(ghcnDB)
    cursor = conn.cursor()
    # Spatialite/SQLite3 won't subsitute parameter strings within quotes, so we have to do it the unsafe way.  This should be okay as
    # we are dealing with numeric values that we are converting to numeric types before building the query string.
    sql = u"SELECT id,AsText(coord),elevation_m,name FROM ghcn_station WHERE Within(coord, BuildMbr(%f,%f,%f,%f));" %\
    (bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY'])
    cursor.execute(sql)
    results = cursor.fetchall()
    conn.close()
    for result in results:
        # Unpack the coordinates
        match = pattern.match(result[1])
        assert(match)
        lon = float(match.group(1))
        lat = float(match.group(2))
        stations.append([result[0], lat, lon, result[2], result[3]])
    return stations


def findStationNearestToCoordinates(config, longitude, latitude):
    """Determine identifier of station nearest to longitude, latitude coordinates.
    
        @param config ConfigParser containing the section 'GHCND' and option 
        'PATH_OF_STATION_DB'
        @param longitude Float representing WGS84 longitude
        @param latitude Float representing WGS84 latitude
        
        @return Tuple of the form (station_id, longitude, latitude, elevation_meters, name, distance),
        None if no gage is found.
        
        @code
        from ecohydrolib.climatedata.ghcndquery import findStationNearestToCoordinates
        import ConfigParser
        config = ConfigParser.RawConfigParser()
        config.read('./bin/macosx2.cfg')
        lon = -76.7443397486
        lat = 39.2955590994
        nearest = findStationNearestToCoordinates(config, lon, lat)
        from ecohydrolib.climatedata.ghcndquery import getClimateDataForStation
        outputDir = '/tmp'
        outfileName = 'clim.txt'
        getClimateDataForStation(config, outputDir, outfileName, nearest[0])
        @endcode
    """
    ghcnDB = config.get('GHCND', 'PATH_OF_STATION_DB')
    
    conn = spatialite.connect(ghcnDB)
    cursor = conn.cursor()
    # Spatialite/SQLite3 won't subsitute parameter strings within quotes, so we have to do it the unsafe way.  This should be okay as
    # we are dealing with numeric values that we are converting to numeric types before building the query string.
    sql = u"SELECT id,AsText(coord),elevation_m,name,Distance(GeomFromText('POINT(%f %f)', %d), coord) as dist FROM ghcn_station order by dist asc limit 1" %\
    (float(longitude), float(latitude), _SRS)
    cursor.execute(sql)
    nearest = cursor.fetchone()
    conn.close()
    if nearest:
        # Unpack the coordinates
        pattern = re.compile("^POINT\((-?\d+\.\d+) (-?\d+\.\d+)\)$")
        match = pattern.match(nearest[1])
        assert(match)
        lon = float(match.group(1))
        lat = float(match.group(2))
        return (nearest[0], lon, lat, nearest[2], nearest[3], nearest[4])
    return None
    

def getClimateDataForStation(config, outputDir, outFilename, stationID, overwrite=True):
    """Fetch climate timeseries data for a GHCN daily station
    
        @param config A Python ConfigParser (not currently used)
        @param outputDir String representing the absolute/relative path of the directory into which output DEM should be written
        @param outDEMFilename String representing the name of the DEM file to be written
        @param stationID String representing unique identifier of station
        @param overwrite Boolean value indicating whether or not the file indicated by filename should be overwritten.
            If False and filename exists, IOError exception will be thrown with errno.EEXIST
        @param overwrite Boolean value indicating whether or not the file indicated by filename should be overwritten.
            If False and filename exists, IOError exception will be thrown with errno.EEXIST
    
        @raise IOError if outputDir is not a writable directory
        @raise IOError if outFilename already exists and overwrite is False (see above)
        
        @return True if timeseries data were fetched and False if not
    """
    dataFetched = False
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    outFilepath = os.path.join(outputDir, outFilename)
    
    if os.path.exists(outFilepath):
        if overwrite: 
            os.unlink(outFilepath)
        else:
            raise IOError(errno.EEXIST, "File %s already exists" % outFilepath)
    
    url = URL_PROTO.format(station_id=stationID)
    
    conn = httplib.HTTPConnection(HOST)
    conn.request('GET', url)
    res = conn.getresponse(buffering=True)
    
    assert(200 == res.status)
    
    data = res.read(_BUFF_LEN)
    if data: 
        dataOut = open(outFilepath, 'wb')
        dataFetched = True
        while data:
            dataOut.write(data)
            data = res.read(_BUFF_LEN)
        dataOut.close()
        
    return dataFetched