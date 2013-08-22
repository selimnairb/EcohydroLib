"""@package ecohydrolib.solim.inference
    
@brief Infer soil properties from SSURGO and terrain data using SOLIM framework

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


ATTRIBUTES = ['avgSand','avgSilt','avgClay','avgKsat','avgPorosity']
ATTRIBUTE_SEP = ','
FILE_EXT = 'tif'

def inferSoilPropertiesForSSURGOAndTerrainData(config, outputDir, shpFilepath, demFilepath, \
                                               featureAttrList=ATTRIBUTES):
    """ Infer soil properties from SSURGO and terrain data using SOLIM framework
    
        @param config ConfigParser containing the section 'SOLIM' and option 'PATH_OF_SOLIM'
        @param outputDir String representing the absolute/relative path of the directory into which shapefile should be written
        @param shpFilepath String representing the absolute path of the shapefile containing SSURGO features
        @param featureAttrList List containing the SSURGO attributes for which soil property inference is to be performed
        @param demFilepath String representing the absolute path of the DEM terrain data
        
        @return Dictionary containing the keys for each soil attribute and values of the names of the raster files generated for that attribute
        
        @exception IOError(errno.EACCES) if SOLIM binary is not executable
        @exception Exception if SOLIM command fails
    """
    solimCmdPath = config.get('SOLIM', 'PATH_OF_SOLIM')
    if not os.access(solimCmdPath, os.X_OK):
        raise IOError(errno.EACCES, "SOLIM command %s is not executable" % (solimCmdPath,))
    
    if not os.path.isdir(outputDir):
        raise IOError(errno.ENOTDIR, "Output directory %s is not a directory" % (outputDir,))
    if not os.access(outputDir, os.W_OK):
        raise IOError(errno.EACCES, "Not allowed to write to output directory %s" % (outputDir,))
    outputDir = os.path.abspath(outputDir)
    
    if not os.access(shpFilepath, os.R_OK):
        raise IOError(errno.EACCES, "Not allowed to read SSURGO feature shapefile %s" % (shpFilepath,))
    if not os.path.isfile(shpFilepath):
        raise IOError(errno.ENOENT, "SSURGO feature shapefile %s does not exist" % (shpFilepath,))
    shpFilepath = os.path.abspath(shpFilepath)
    
    if not os.access(demFilepath, os.R_OK):
        raise IOError(errno.EACCES, "Not allowed to read terrain DEM file %s" % (demFilepath,))
    if not os.path.isfile(demFilepath):
        raise IOError(errno.ENOENT, "Terrain DEM file %s does not exist" % (demFilepath,))
    demFilepath = os.path.abspath(demFilepath)
    
    solimCommand = "%s %s mukey %s %s %s" % \
        (solimCmdPath, shpFilepath, demFilepath, outputDir, ATTRIBUTE_SEP.join(featureAttrList))
    #print solimCommand
    returnCode = os.system(solimCommand)
    if returnCode != 0:
        raise Exception("SOLIM command %s failed, returning %d" % (solimCommand, returnCode) )
    
    filesCreated = dict()
    for attr in featureAttrList:
        filename = attr + os.extsep + FILE_EXT
        if not os.path.exists(os.path.join(outputDir, filename)):
            raise Exception("SOLIM failed to create file %s in directory %s" % \
                            (filename, outputDir) )
        filesCreated[attr] = filename
    
    return filesCreated