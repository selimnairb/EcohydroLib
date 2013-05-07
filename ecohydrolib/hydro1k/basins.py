"""@package ecohydrolib.hydro1k.basins
    
@brief Methods for querying HYDRO1k basins

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


def getCatchmentShapefileForHYDRO1kBasins(config, outputDir, catchmentFilename, basins):
    """ Get shapefile (in WGS 84) for the drainage area associated with a list of HYDRO1k basins
    
        @note No return value. catchmentFilename will be written to outputDir if successful
        
        @param config A Python ConfigParser containing the following sections and options:
            'GDAL/OGR' and option 'PATH_OF_OGR2OGR' (absolute path of ogr2ogr binary)
            'HYDRO1k' and option 'PATH_OF_HYDRO1K_BAS' (absolute path to HYDRO1k North America na_bas.e00)
        @param outputDir String representing the absolute/relative path of the directory into which output 
            rasters should be written
        @param catchmentFilename String representing name of file to save catchment shapefile to
        @param basins List of strings representing basin IDs; must be of the same level: 1, 2, 3, 4, 5, 6
        where level corresponds to the number of characters in the ID string.
        
        @exception ConfigParser.NoSectionError
        @exception ConfigParser.NoOptionError
        @exception IOError(errno.ENOTDIR) if outputDir is not a directory
        @exception IOError(errno.EACCESS) if outputDir is not writable
        @exception Exception of catchment shapefile extraction fails
    """
    hydro1kPath = config.get('HYDRO1k', 'PATH_OF_HYDRO1K_BAS')
    if not os.access(hydro1kPath, os.R_OK):
        raise IOError(errno.EACCES, "The catchment feature layer at %s is not readable" %
                      hydro1kPath)
    hydro1kPath = os.path.abspath(hydro1kPath)
    
    hydro1kLayerName = config.get('HYDRO1k', 'HYDRO1k_BAS_LAYER_NAME')
    
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
    
    catchmentFilename = os.path.join(outputDir, catchmentFilename)
    
    assert(len(basins) > 0)
    # Ensure all basin IDs are of the same level
    levelNum = len(basins[0])
    assert( all( len(i) == levelNum for i in basins ) )
    levelStr = "LEVEL%d" % (levelNum,)
    
    # Build query for basin identifiers
    ogrCommand = "%s -t_srs EPSG:4326  -f 'ESRI Shapefile' -where '%s=%s" % \
        (ogrCmdPath, levelStr, basins[0])
    for basin in basins[1:]:
        ogrCommand = ogrCommand + " OR %s=%s" % (levelStr, basin) 
    ogrCommand = ogrCommand +"' " + catchmentFilename + " " + hydro1kPath + " " + hydro1kLayerName
      
    # Extract polygons for specified basins
    #sys.stderr.write("ogr command: %s\n" % ogrCommand)
    returnCode = os.system(ogrCommand)
    if returnCode != 0:
        raise Exception("OGR command %s failed." % (ogrCommand,))  