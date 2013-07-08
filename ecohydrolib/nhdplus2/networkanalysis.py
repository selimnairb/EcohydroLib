"""@package ecohydrolib.nhdplus2.networkanalysis
    
@brief Methods for querying the NHDPlus V2 data set. Requires that a NHDPlus V2 
database be initialized from data archive files using NHDPlusSetup.py

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
import os
import errno
import time
import sqlite3
import re

import ogr

from ecohydrolib.spatialdata.utils import getBoundingBoxForShapefile
from ecohydrolib.spatialdata.utils import deleteShapefile

OGR_UPDATE_MODE = False
NORTH = 0
EAST = 90
OGR_SHAPEFILE_DRIVER_NAME = "ESRI Shapefile"
UPSTREAM_SEARCH_THRESHOLD = 998


def getNHDReachcodeAndMeasureForGageSourceFea(config, source_fea):
    """ Get NHD Reachcode and measure along reach for a 
        streamflow gage identified by a source_fea (e.g. USGS Site Number)
    
        @param config A Python ConfigParser containing the following sections and options:
            'NHDPLUS2', 'PATH_OF_NHDPLUS2_DB' (absolute path to NHDPlus2 SQLite3 database)
        @param source_fea String representing source_fea of GageLoc gage
         
        @return A tuple(string, float) representing the reachcode and measure; None if no gage was found.
        
        @raise ConfigParser.NoSectionError
        @raise ConfigParser.NoOptionError
        @raise IOError(errno.EACCES) if NHDPlus2 DB is not readable
    """
    nhddbPath = config.get('NHDPLUS2', 'PATH_OF_NHDPLUS2_DB')
    if not os.access(nhddbPath, os.R_OK):
        raise IOError(errno.EACCES, "The database at %s is not readable" %
                      nhddbPath)
    nhddbPath = os.path.abspath(nhddbPath)
    
    conn = sqlite3.connect(nhddbPath)
    
    cursor = conn.cursor()
    cursor.execute("""SELECT ReachCode,Measure FROM Gage_Loc WHERE Source_Fea=?""", (source_fea,))
    result = cursor.fetchone()
    if None == result:
        return None
    
    reachcode = result[0]
    measure = result[1]

    return (reachcode, measure)


def getLocationForStreamGageByGageSourceFea(config, source_fea):
    """ Get lat/lon, in WGS84 (EPSG:4326), from gage point layer (Gage_Loc) for
        gage identified by a source_fea (e.g. USGS Site Number)
    
        @param config A Python ConfigParser containing the following sections and options:
            'NHDPLUS2', 'PATH_OF_NHDPLUS2_GAGELOC' (absolute path to NHD GageLoc SQLite3 spatial database)
        @param source_fea String representing source_fea of GageLoc gage
         
        @return A tuple with (x,y) coordinates in 'EPSG:4326' (WGS 84)
    """
    whereFilter = "Source_Fea='%s'" % (source_fea,)
    result = getLocationForStreamGage(config, whereFilter)
    if result:
        return (result[0], result[1])
    return None


def getLocationForStreamGageByReachcodeAndMeasure(config, reachcode, measure):
    """ Get lat/lon, in WGS84 (EPSG:4326), from gage point layer (Gage_Loc) for
        gage identified by reachcode and measure
    
        @param config A Python ConfigParser containing the following sections and options:
            'NHDPLUS2', 'PATH_OF_NHDPLUS2_GAGELOC' (absolute path to NHD GageLoc SQLite3 spatial database)
        @param reachcode String representing NHD streamflow gage 
        @param measure Float representing the measure along reach where Stream Gage is located 
            in percent from downstream end of the one or more NHDFlowline features that are 
            assigned to the ReachCode (see NHDPlusV21 GageLoc table)
         
        @return A tuple with (x,y) coordinates in 'EPSG:4326' (WGS 84); None if gage was not found
    """
    whereFilter = "REACHCODE='%s' and Measure=%f" % (reachcode, measure)
    result = getLocationForStreamGage(config, whereFilter)
    if result:
        return (result[0], result[1])
    return None


def getLocationForStreamGage(config, whereFilter):
    """ Get lat/lon, in WGS84 (EPSG:4326), from gage point layer (Gage_Loc) for
        gage identified by reachcode and measure
    
        @param config A Python ConfigParser containing the following sections and options:
            'NHDPLUS2', 'PATH_OF_NHDPLUS2_GAGELOC' (absolute path to NHD GageLoc SQLite3 spatial database)
        @param whereFilter String representing the whereFilter to use
         
        @return A tuple with (x,y) coordinates in 'EPSG:4326' (WGS 84); None if gage was not found
        
        @raise ConfigParser.NoSectionError
        @raise ConfigParser.NoOptionError
        @raise Exception if unable to open gage database
        @raise IOError(errno.ENOTDIR) if GageLoc is not readable
    """
    gageLocPath = config.get('NHDPLUS2', 'PATH_OF_NHDPLUS2_GAGELOC')
    if not os.access(gageLocPath, os.R_OK):
        raise IOError(errno.EACCES, "The database at %s is not readable" %
                      gageLocPath)
    gageLocPath = os.path.abspath(gageLocPath)
    
    poDS = ogr.Open(gageLocPath, OGR_UPDATE_MODE)
    if not poDS:
        raise Exception("Unable to open gage database %s" (gageLocPath,))
    assert(poDS.GetLayerCount() > 0)
    poLayer = poDS.GetLayer(0)
    assert(poLayer)
    assert(poLayer.SetAttributeFilter(whereFilter) == 0)
    poFeature = poLayer.GetNextFeature()
    if poFeature:
        poGeometry = poFeature.GetGeometryRef()
        
        # Make sure spatial reference is EPSG:4326
        pattern = re.compile("\ssrsName=\"(.+)\">")
        gml = poGeometry.ExportToGML()
        result = pattern.search(gml)
        assert(result.group(1) == 'EPSG:4326')
        
        # Get coordinates
        x = poGeometry.GetX()
        y = poGeometry.GetY()
        return (x,y)
    return None
    

def getComIdForStreamGage(conn, reachcode, measure):
    """ Uses NHDFlowline and/or NHDReachCode_ComID table(s) to lookup the ComID associated with a stream gage
        identified by reach code and measure.
    
        @param conn An sqlite3 connection to a database that has the NHDFlowline and NHDReachCode_Comid tables
        @param reachcode An string representing the Reachcode
        #param measure A float representing the measure along reach where Stream Gage is located 
            in percent from downstream end of the one or more NHDFlowline features that are 
            assigned to the ReachCode (see NHDPlusV21 GageLoc table)
        
        @return An integer representing the ComID associated with a Reachcode, or -1 if a reach with Reachcode 
        was not found.

    """
    comID = -1
    cursor = conn.cursor()
    # NHDPlusV21:
    ## The NHDFlowline comid for a stream flow gage location can be determined from the 
    ## PlusFlowlineVAA where Gage_Loc.Reachcode = PlusFlowlineVAA.Reachcode and 
    ## Gage_Loc.measure => PlusFlowlineVAA.FromMeas and Gage_Loc.measure <= PlusFlowlineVAA.ToMeas.
    cursor.execute("""SELECT p.ComID FROM PlusflowlineVAA as p
JOIN Gage_Loc as g ON p.ReachCode=g.ReachCode
WHERE (g.Measure >= p.FromMeas AND g.Measure <= p.ToMeas)
AND g.ReachCode=? AND g.Measure=?""", (reachcode, measure))
    result = cursor.fetchone()
    if None != result:
        comID = result[0]

    return comID


def getPlusFlowPredecessors(conn, comID):
    """ Get the immediate predecessors of the NHDPlus2 PlusFlow feature of comID
    
        @param conn A connection an SQLite3 database
        @param comdID String representing the ComID of the reach whose immediate predecessor reaches are to be discovered
        
        @return A list of immediate predecessor nodes in the NHDPlus2 PlusFlow graph
    """
    immediatePredecessors = []
    cursor = conn.cursor()
    cursor.execute("""SELECT FROMCOMID FROM PlusFlow WHERE TOCOMID=?""", (comID,))
    for row in cursor:
        immediatePredecessors.append(row[0])
    return immediatePredecessors


def getUpstreamReachesSQL(conn, comID, allUpstreamReaches):
    """ Recursively searches PlusFlow table in an SQLite database for all stream reaches
        upstream of a given reach.
    
        @note This method has no return value. Upstream reaches discovered are appended to allUpstreamReaches list.
    
        @param conn A connection to an SQLite3 database
        @param comID The ComID of the reach whose upstream reaches are to be discovered
        @param allUpstreamReaches A list containing integers representing comIDs of upstream reaches
    """
    upstream_reaches = getPlusFlowPredecessors(conn, comID)
    if len(upstream_reaches) == 0:
        return
    
    if len(upstream_reaches) == 1 and upstream_reaches[0] == 0:
        # We're at a headwater reach
        return

    # Foreach reach upstream of this reach
    for u in upstream_reaches:
        # Record the upstream reach
        allUpstreamReaches.append(u)
        # Fine reaches upstream of it
        getUpstreamReachesSQL(conn, u, allUpstreamReaches)
    
        
def getBoundingBoxForCatchmentsForGage(config, outputDir, reachcode, measure, deleteIntermediateFiles=True):
    """ Get bounding box coordinates (in WGS 84) for the drainage area associated with a given NHD 
        (National Hydrography Dataset) streamflow gage identified by a reach code and measure.
        
        @param config A Python ConfigParser containing the following sections and options:
            'GDAL/OGR' and option 'PATH_OF_OGR2OGR' (absolute path of ogr2ogr binary)
            'NHDPLUS2' and option 'PATH_OF_NHDPLUS2_DB' (absolute path to SQLite3 DB of NHDFlow data)
            'NHDPLUS2', 'PATH_OF_NHDPLUS2_CATCHMENT' (absolute path to NHD catchment SQLite3 spatial DB)
        @param outputDir String representing the absolute/relative path of the directory into which output rasters should be written
        @param reachcode String representing NHD streamflow gage 
        @param measure Float representing the measure along reach where Stream Gage is located 
            in percent from downstream end of the one or more NHDFlowline features that are 
            assigned to the ReachCode (see NHDPlusV21 GageLoc table)
        @param deleteIntermediateFiles A boolean, True if intermediate files generated from the analysis should be deleted
         
        @return A dictionary with keys: minX, minY, maxX, maxY, srs. The key srs is set to 'EPSG:4326' (WGS 84)
        
        @raise ConfigParser.NoSectionError
        @raise ConfigParser.NoOptionError
        @raise IOError(errno.ENOTDIR) if outputDir is not a directory
        @raise IOError(errno.EACCESS) if outputDir is not writable
    """
    nhddbPath = config.get('NHDPLUS2', 'PATH_OF_NHDPLUS2_DB')
    if not os.access(nhddbPath, os.R_OK):
        raise IOError(errno.EACCES, "The database at %s is not readable" %
                      nhddbPath)
    nhddbPath = os.path.abspath(nhddbPath)
        
    catchmentFeatureDBPath = config.get('NHDPLUS2', 'PATH_OF_NHDPLUS2_CATCHMENT')
    if not os.access(catchmentFeatureDBPath, os.R_OK):
        raise IOError(errno.EACCES, "The catchment feature DB at %s is not readable" %
                      catchmentFeatureDBPath)
    catchmentFeatureDBPath = os.path.abspath(catchmentFeatureDBPath)
    
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
    
    # Connect to DB
    conn = sqlite3.connect(nhddbPath)
    
    comID = getComIdForStreamGage(conn, reachcode, measure)
    #sys.stderr.write("Gage with reachcode %s, measure %f has ComID %d" % (reachcode, measure, comID))
    
    # Get upstream reaches
    upstream_reaches = []
    getUpstreamReachesSQL(conn, comID, upstream_reaches)
    #sys.stderr.write("Upstream reaches: ")
    #sys.stderr.write(upstream_reaches)
    
    # Extract polygons for upstream catchments
    catchmentOut = os.path.join(outputDir, "catchment-%s.shp" % time.time())
    ogrCommand = "%s -s_srs EPSG:4326 -t_srs EPSG:4326  -f 'ESRI Shapefile' -sql 'SELECT * FROM catchment WHERE featureid=%s" % (ogrCmdPath, comID) # NHDPlusV2
    for reach in upstream_reaches:
        ogrCommand = ogrCommand + " OR featureid=%s" % reach # NHDPlusV2
    ogrCommand = ogrCommand +"' " + catchmentOut + " " + catchmentFeatureDBPath  
    #sys.stderr.write("ogr command: %s" % ogrCommand)
    os.system(ogrCommand)
    
    bbox = getBoundingBoxForShapefile(catchmentOut)
    
    # Clean-up temporary shapefile/ancillary files
    if deleteIntermediateFiles:
        deleteShapefile(catchmentOut)
    
    conn.close()

    return bbox
 
 
def getCatchmentShapefileForGage(config, outputDir, catchmentFilename, reachcode, measure, deleteIntermediateFiles=True):
    """ Get shapefile (in WGS 84) for the drainage area associated with a given NHD 
        (National Hydrography Dataset) streamflow gage identified by a reach code and measure.
        
        @note Capable of handling gages with more than 1000 upstream reaches 
        @note No return value. catchmentFilename will be written to outputDir if successful
        
        @param config A Python ConfigParser containing the following sections and options:
            'NHDPLUS2' and option 'PATH_OF_NHDPLUS2_DB' (absolute path to SQLite3 DB of NHDFlow data)
            'NHDPLUS2', 'PATH_OF_NHDPLUS2_CATCHMENT' (absolute path to NHD catchment shapefile)
        @param outputDir String representing the absolute/relative path of the directory into which output 
            rasters should be written
        @param catchmentFilename String representing name of file to save catchment shapefile to
        @param reachcode String representing NHD streamflow gage 
        @param measure Float representing the measure along reach where Stream Gage is located 
            in percent from downstream end of the one or more NHDFlowline features that are 
            assigned to the ReachCode (see NHDPlusV21 GageLoc table)
         
        @raise ConfigParser.NoSectionError
        @raise ConfigParser.NoOptionError
        @raise IOError(errno.ENOTDIR) if outputDir is not a directory
        @raise IOError(errno.EACCESS) if outputDir is not writable
    """
    nhddbPath = config.get('NHDPLUS2', 'PATH_OF_NHDPLUS2_DB')
    if not os.access(nhddbPath, os.R_OK):
        raise IOError(errno.EACCES, "The database at %s is not readable" %
                      nhddbPath)
    nhddbPath = os.path.abspath(nhddbPath)
        
    catchmentFeatureDBPath = config.get('NHDPLUS2', 'PATH_OF_NHDPLUS2_CATCHMENT')
    if not os.access(catchmentFeatureDBPath, os.R_OK):
        raise IOError(errno.EACCES, "The catchment feature DB at %s is not readable" %
                      catchmentFeatureDBPath)
    catchmentFeatureDBPath = os.path.abspath(catchmentFeatureDBPath)
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    catchmentFilename = os.path.join(outputDir, catchmentFilename)
    
    # Connect to DB
    conn = sqlite3.connect(nhddbPath)
    
    comID = getComIdForStreamGage(conn, reachcode, measure)
    #sys.stderr.write("Gage with reachcode %s, measure %f has ComID %d" % (reachcode, measure, comID))
    
    # Get upstream reaches
    reaches = [comID]
    getUpstreamReachesSQL(conn, comID, reaches)
    #sys.stderr.write("Upstream reaches: ")
    #sys.stderr.write(upstream_reaches)
    conn.close()
    
    # Open input layer
    ogr.UseExceptions()
    poDS = ogr.Open(catchmentFeatureDBPath, OGR_UPDATE_MODE)
    if not poDS:
        raise Exception("Unable to open catchment feature database %s" (catchmentFeatureDBPath,))
    assert(poDS.GetLayerCount() > 0)
    poLayer = poDS.GetLayer(0)
    assert(poLayer)
    
    # Create output data source
    poDriver = ogr.GetDriverByName(OGR_SHAPEFILE_DRIVER_NAME)
    assert(poDriver)
    poODS = poDriver.CreateDataSource(catchmentFilename)
    assert(poODS != None)
    poOLayer = poODS.CreateLayer("catchment", poLayer.GetSpatialRef(), poLayer.GetGeomType())
    
    # Create fields in output layer
    layerDefn = poLayer.GetLayerDefn()
    i = 0
    fieldCount = layerDefn.GetFieldCount()
    while i < fieldCount:
        fieldDefn = layerDefn.GetFieldDefn(i)
        poOLayer.CreateField(fieldDefn)
        i = i + 1

    # Copy features
    numReaches = len(reaches)
    # Copy features in batches of UPSTREAM_SEARCH_THRESHOLD to overcome limit in 
    #   OGR driver for input layer
    start = 0
    end = UPSTREAM_SEARCH_THRESHOLD
    while end < numReaches:
        whereFilter = "featureid=%s" % (reaches[start],)
        for reach in reaches[start+1:end]:
            whereFilter = whereFilter + " OR featureid=%s" % (reach,)
        # Copy features
        assert(poLayer.SetAttributeFilter(whereFilter) == 0)
        inFeature = poLayer.GetNextFeature()
        while inFeature:
            poOLayer.CreateFeature(inFeature)
            inFeature.Destroy()
            inFeature = poLayer.GetNextFeature()
        start = end
        end = end + UPSTREAM_SEARCH_THRESHOLD
    # Copy remaining features
    whereFilter = "featureid=%s" % (reaches[start],)
    for reach in reaches[start+1:end]:
        whereFilter = whereFilter + " OR featureid=%s" % (reach,)
    # Copy features
    assert(poLayer.SetAttributeFilter(whereFilter) == 0)
    inFeature = poLayer.GetNextFeature()
    while inFeature:
        poOLayer.CreateFeature(inFeature)
        inFeature.Destroy()
        inFeature = poLayer.GetNextFeature()
        