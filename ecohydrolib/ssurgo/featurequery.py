"""@package ecohydrolib.ssurgo.featurequery
    
@brief Make feature queries against USDA Soil Data Mart OGC web service interface

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
import sys
import errno
import xml.sax
import json
import shutil
import multiprocessing
import gc

from owslib.wfs import WebFeatureService

from ecohydrolib.spatialdata.utils import calculateBoundingBoxArea
from ecohydrolib.spatialdata.utils import tileBoundingBox
from ecohydrolib.spatialdata.utils import convertGMLToGeoJSON
from ecohydrolib.spatialdata.utils import mergeFeatureLayers
from ecohydrolib.spatialdata.utils import convertGeoJSONToShapefile
from ecohydrolib.spatialdata.utils import OGR_SHAPEFILE_DRIVER_NAME
from attributequery import getParentMatKsatTexturePercentClaySiltSandForComponentsInMUKEYs
from attributequery import joinSSURGOAttributesToFeaturesByMUKEY_GeoJSON
from attributequery import computeWeightedAverageKsatClaySandSilt
from saxhandlers import SSURGOFeatureHandler       

MAX_SSURGO_EXTENT = 10100000000 # 10,100,000,000 sq. meters
MAX_SSURGO_EXTENT = MAX_SSURGO_EXTENT / 4.0 # Large queries take a long time, reduce threshold for tiling
SSURGO_BBOX_TILE_DIVISOR = 8.0

SSURGO_WFS_TIMEOUT_SEC = 3600
SSURGO_GML_MAX_DOWNLOAD_ATTEMPTS = 4
WFS_URL = 'http://SDMDataAccess.nrcs.usda.gov/Spatial/SDMWGS84Geographic.wfs'

def getMapunitFeaturesForBoundingBox(config, outputDir, bbox, tileBbox=False, t_srs='EPSG:4326', 
                                     tileDivisor=SSURGO_BBOX_TILE_DIVISOR,
                                     keepOriginals=False,
                                     overwrite=True,
                                     nprocesses=None):
    """ Query USDA Soil Data Mart for SSURGO MapunitPolyExtended features with a given bounding box.
        Features will be written to one or more shapefiles, one file for each bboxTile tile,
        stored in the specified output directory. The filename will be returned as a string.
        Will fetch SSURGO tabular data (see ssurgolib.attributequery.ATTRIBUTE_LIST for a list
        of attributes) and join those data to the features in the final shapefiles(s).
    
        @note Will silently exit if features already exist.
    
        @param config onfigParser containing the section 'GDAL/OGR' and option 'PATH_OF_OGR2OGR'
        @param outputDir String representing the absolute/relative path of the directory into which features should be written
        @param bbox A dict containing keys: minX, minY, maxX, maxY, srs, where srs='EPSG:4326'
        @param tileBoundingBox True if bounding box should be tiled if extent exceeds featurequery.MAX_SSURGO_EXTENT
        @param t_srs String representing the spatial reference system of the output shapefiles, of the form 'EPSG:XXXX'
        @param tileDivisor Float representing amount by which to divide tile slides.
        @param keepOriginals Boolean, if True original feature layers will be retained (otherwise they will be deleted)
        @param overwrite Boolean, if True any existing files will be overwritten
        @param nprocesses Integer representing number of processes to use for fetching SSURGO tiles in parallel (used only if bounding box needs to be tiled).
               if None, multiprocessing.cpu_count() will be used.
        
        @return A list of strings representing the name of the shapefile(s) to which the mapunit features were saved.
        
        @exception IOError if output directory is not a directory
        @exception IOError if output directory is not writable
        @exception Exception if tileDivisor is not a postive float > 0.0.
        @exception Exception if bounding box area is greater than MAX_SSURGO_EXTENT
        @exception Exception if no MUKEYs were returned
    """
    if type(tileDivisor) != float or tileDivisor <= 0.0:
        raise Exception("Tile divisor must be a float > 0.0.")
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)

    typeName = 'MapunitPolyExtended'

    if tileBbox:
        bboxes = tileBoundingBox(bbox, MAX_SSURGO_EXTENT, t_srs, tileDivisor)
        sys.stderr.write("Dividing bounding box %s into %d tiles\n" % (str(bbox), len(bboxes)))
    else:
        bboxArea = calculateBoundingBoxArea(bbox, t_srs)
        if bboxArea > MAX_SSURGO_EXTENT:
            raise Exception("Bounding box area %.2f sq. km is greater than %.2f sq. km.  You must tile the bounding box." % (bboxArea/1000/1000, MAX_SSURGO_EXTENT/1000/1000,))
        bboxes = [bbox]
    
    numTiles = len(bboxes)
    assert(numTiles >= 1)
    
    outFiles = []
    if numTiles == 1:
        # No tiling, fetch SSURGO features for bbox in the current process
        geojsonFilename = _getMapunitFeaturesForBoundingBoxTile(config, outputDir, bboxes[0], typeName, 1, numTiles)
        outFiles.append(geojsonFilename)
    else:
        # Fetch SSURGO feature tiles in parallel
        if nprocesses is None:
            nprocesses = multiprocessing.cpu_count()
        assert(type(nprocesses) == int)
        assert(nprocesses > 0)
        
        # Start my pool
        pool = multiprocessing.Pool( nprocesses )
        tasks = []
        
        # Build task list
        i = 1
        for bboxTile in bboxes:
            tasks.append( (config, outputDir, bboxTile, typeName, i, numTiles) ) 
            i += 1

        # Send tasks to pool (i.e. fetch SSURGO features for each tile in parallel)
        results = [pool.apply_async(_getMapunitFeaturesForBoundingBoxTile, t) for t in tasks]
        
        # Get resulting filenames for each tile
        for result in results:
            outFiles.append(result.get())
    
        pool.close()
        pool.join()
    
    # Join tiled data if necessary
    if len(outFiles) > 1:
        sys.stderr.write('Merging tiled features to single shapefile...')
        sys.stderr.flush()
        shpFilepath = mergeFeatureLayers(config, outputDir, outFiles, typeName,
                                         outFormat=OGR_SHAPEFILE_DRIVER_NAME,
                                         keepOriginals=keepOriginals,
                                         t_srs=t_srs,
                                         overwrite=overwrite)
        shpFilename = os.path.basename(shpFilepath)
        sys.stderr.write('done\n')
    else:
        # Convert GeoJSON to shapefile
        filepath = outFiles[0]
        sys.stderr.write('Converting SSURGO features from GeoJSON to shapefile format...')
        sys.stderr.flush()
        shpFilename = convertGeoJSONToShapefile(config, outputDir, filepath, typeName, t_srs=t_srs)
        os.unlink(filepath)
        sys.stderr.write('done\n')   
    
    return shpFilename
    
def _getMapunitFeaturesForBoundingBoxTile(config, outputDir, bboxTile, typeName, currTile, numTiles):
    minX = bboxTile['minX']; minY = bboxTile['minY']; maxX = bboxTile['maxX']; maxY = bboxTile['maxY']
    bboxLabel = str(minX) + "_" + str(minY) + "_" + str(maxX) + "_" + str(maxY)

    gmlFilename = "%s_bbox_%s-attr.gml" % (typeName, bboxLabel)
    gmlFilepath = os.path.join(outputDir, gmlFilename)
    geoJSONLayername = "%s_bbox_%s-attr" % (typeName, bboxLabel)

    if not os.path.exists(gmlFilepath):
        sys.stderr.write("Fetching SSURGO data for tile %s of %s, bbox: %s\n" % (currTile, numTiles, bboxLabel))
        sys.stderr.flush()
    
        wfs = WebFeatureService(WFS_URL, version='1.0.0', timeout=SSURGO_WFS_TIMEOUT_SEC)
        filter = "<Filter><BBOX><PropertyName>Geometry</PropertyName> <Box srsName='EPSG:4326'><coordinates>%f,%f %f,%f</coordinates> </Box></BBOX></Filter>" % (minX, minY, maxX, maxY)
        
        intGmlFilename = "%s_bbox_%s.gml" % (typeName, bboxLabel)
        intGmlFilepath = os.path.join(outputDir, intGmlFilename)
        ssurgoFeatureHandler = SSURGOFeatureHandler()
        
        downloadComplete = False
        downloadAttempts = 0
        while not downloadComplete:
            try:
                gml = wfs.getfeature(typename=(typeName,), filter=filter, propertyname=None)
        
                # Write intermediate GML to a file
                out = open(intGmlFilepath, 'w')
                out.write(gml.read())
                out.close()
                
                # Parse GML to get list of MUKEYs
                gmlFile = open(intGmlFilepath, 'r')
                xml.sax.parse(gmlFile, ssurgoFeatureHandler)
                gmlFile.close()
                downloadComplete = True
            except xml.sax.SAXParseException as e:
                # Try to re-download
                downloadAttempts += 1
                if downloadAttempts > SSURGO_GML_MAX_DOWNLOAD_ATTEMPTS:
                    raise Exception("Giving up on downloading tile {0} of {1} after {2} attempts.  There may be something wrong with the web service.  Try again later.".format(currTile, numTiles, downloadAttempts))
                else:
                    sys.stderr.write("Initial download of tile {0} of {1} possibly incomplete, error: {0}.  Retrying...".format(currTile, numTiles, str(e)))
                    sys.stderr.flush()
                    
        mukeys = ssurgoFeatureHandler.mukeys
        
        if len(mukeys) < 1:
            raise Exception("No SSURGO features returned from WFS query.  SSURGO GML format may have changed.\nPlease contact the developer.")
        
        # Get attributes (ksat, texture, %clay, %silt, and %sand) for all components in MUKEYS
        attributes = getParentMatKsatTexturePercentClaySiltSandForComponentsInMUKEYs(mukeys)
        
        # Compute weighted average of soil properties across all components in each map unit
        avgAttributes = computeWeightedAverageKsatClaySandSilt(attributes)
        
        # Convert GML to GeoJSON so that we can add fields easily (GDAL 1.10+ validates GML schema 
        #   and won't let us add fields)
        tmpGeoJSONFilename = convertGMLToGeoJSON(config, outputDir, intGmlFilepath, geoJSONLayername)
        tmpGeoJSONFilepath = os.path.join(outputDir, tmpGeoJSONFilename)
        
        # Join map unit component-averaged soil properties to attribute table in GeoJSON file
        tmpGeoJSONFile = open(tmpGeoJSONFilepath, 'r')
        geojson = json.load(tmpGeoJSONFile)
        tmpGeoJSONFile.close()
        joinSSURGOAttributesToFeaturesByMUKEY_GeoJSON(geojson, typeName, avgAttributes)
        
        # Write joined GeoJSON to a file
        out = open(tmpGeoJSONFilepath, 'w')
        json.dump(geojson, out)
        out.close()
        
        # Delete intermediate files
        os.unlink(intGmlFilepath)
        
        return tmpGeoJSONFilepath
    