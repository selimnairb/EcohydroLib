"""@package ecohydrolib.geosciaus.soilwcs
    
@brief Query soils data from WCS service provided by CSIRO/Geoscience Australia

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
import os, sys, errno
import tempfile
import shutil
import ConfigParser

from owslib.wcs import WebCoverageService

from ecohydrolib.spatialdata.utils import resampleRaster

FORMAT_GEOTIFF = 'GeoTIFF'
MIME_TYPE = {FORMAT_GEOTIFF: 'image/GeoTIFF'}

# VARIABLE = {'clay': 'CLY',
#             'silt': 'SLT',
#             'sand': 'SND'
#             }

VARIABLE = {'clay': 'CLY'}

URL_BASE = "http://www.asris.csiro.au/ArcGis/services/TERN/{variable}_ACLEP_AU_TRN_N/MapServer/WCSServer"

COVERAGES = ["{variable}_000_005_EV_N_P_AU_TRN_N_1",  # 0-5cm 
             "{variable}_005_015_EV_N_P_AU_TRN_N_4",  # 5-15cm
             "{variable}_015_030_EV_N_P_AU_TRN_N_7",  # 15-30cm
             "{variable}_030_060_EV_N_P_AU_TRN_N_10", # 30-60cm
             "{variable}_060_100_EV_N_P_AU_TRN_N_13", # 60-100cm
            ]

WEIGHTS = {COVERAGES[0]: float(5)/float(100),     # 0-5cm
           COVERAGES[1]: float(10)/float(100),    # 5-15cm
           COVERAGES[2]: float(15)/float(100),    # 15-30cm
           COVERAGES[3]: float(30)/float(100),    # 30-60cm
           COVERAGES[4]: float(40)/float(100),    # 60-100cm  
          }


def ordinalToAlpha(ordinal):
    """
        Return unicode character ranging from A-Z for ordinal values from 1-26
    """
    assert(ordinal >= 1)
    assert(ordinal <= 26)
    o = ordinal + 64 # Map to ASCII/UNICODE value for capital letters
    return unichr(o)
    

# Example URL: http://www.asris.csiro.au/ArcGis/services/TERN/CLY_ACLEP_AU_TRN_N/MapServer/WCSServer?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage&COVERAGE=CLY_000_005_EV_N_P_AU_TRN_N_1&FORMAT=GeoTIFF&BBOX=147.539,-37.024,147.786,-36.830&RESX=0.000277777777778&RESY=0.000277777777778&CRS=EPSG:4283&RESPONSE_CRS=EPSG:4326&INTERPOLATION=bilinear&Band=1
# http://www.asris.csiro.au/ArcGis/services/TERN/CLY_ACLEP_AU_TRN_N/MapServer/WCSServer?SERVICE=WCS&REQUEST=GetCoverage&VERSION=1.0.0&COVERAGE=1&FORMAT=GeoTIFF&BBOX=147.539,-37.024,147.786,-36.830&RESX=0.000277777777778&RESY=0.000277777777778&CRS=EPSG:4283&RESPONSE_CRS=EPSG:4326&INTERPOLATION=bilinear&Band=1
# Clay: http://www.asris.csiro.au/ArcGis/services/TERN/CLY_ACLEP_AU_TRN_N/MapServer/WCSServer?SERVICE=WCS&REQUEST=GetCapabilities
# Silt: http://www.asris.csiro.au/ArcGis/services/TERN/SLT_ACLEP_AU_TRN_N/MapServer/WCSServer?SERVICE=WCS&REQUEST=GetCapabilities
# Sand: http://www.asris.csiro.au/ArcGis/services/TERN/SND_ACLEP_AU_TRN_N/MapServer/WCSServer?SERVICE=WCS&REQUEST=GetCapabilities

def _getCoverageIDsAndWeightsForCoverageTitle(wcs, variable):
    coverages = wcs.items()
    coverage_ids = {}
    coverage_weights = {}
    for coverage in coverages:
        #print('id: %s, title %s' % (coverage[0], coverage[1].title))
        id = coverage[0]
        title = coverage[1].title
        for c in COVERAGES:
            cov = c.format(variable=variable)
            if title == cov:
                coverage_ids[cov] = id
                coverage_weights[cov] = WEIGHTS[c]
         
    return (coverage_ids, coverage_weights)

def getSoilsRasterDataForBoundingBox(config, outputDir, bbox, 
                                     crs='EPSG:4326',
                                     #response_crs='EPSG:4326',
                                     resx=0.000277777777778,
                                     resy=0.000277777777778,
                                     interpolation='bilinear',
                                     fmt=FORMAT_GEOTIFF, 
                                     overwrite=False):
    """
    
        @exception Exception if a gdal_calc.py command fails
    """
    soilPropertyRasters = {}
    
    #import logging
    #logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    #owslib_log = logging.getLogger('owslib')
    # Add formatting and handlers as needed
    #owslib_log.setLevel(logging.DEBUG)
    
    # Set-up gdal_calc.py command
    gdalBase = None
    try:
        gdalBase = config.get('GDAL/OGR', 'GDAL_BASE')
    except ConfigParser.NoOptionError:
        gdalBase = os.path.dirname(config.get('GDAL/OGR', 'PATH_OF_GDAL_WARP'))
    
    gdalCmdPath = os.path.join(gdalBase, 'gdal_calc.py')
    if not os.access(gdalCmdPath, os.X_OK):
        raise IOError(errno.EACCES, "The gdal_calc.py binary at %s is not executable" %
                      gdalCmdPath)
    gdalCmdPath = os.path.abspath(gdalCmdPath)
    
    tmpdir = tempfile.mkdtemp()
    print(tmpdir)
    
    bbox = [bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY']]
    
    # For each soil variable, download desired depth layers
    for v in VARIABLE.keys():
        variable = VARIABLE[v]
        url = URL_BASE.format(variable=variable)

        wcs = WebCoverageService(url, version='1.0.0')
        (coverages, weights_abs) = _getCoverageIDsAndWeightsForCoverageTitle(wcs, variable)
        
        outfiles = []
        weights = []
        for c in coverages.keys():
            coverage = coverages[c]
            weights.append(weights_abs[c])
            #coverage = c.format(variable=variable)
            wcsfp = wcs.getCoverage(identifier=coverage, bbox=bbox,
                                    crs='EPSG:4326',
                                    resx=resx,
                                    resy=resy,
                                    format=fmt)
            filename = os.path.join(tmpdir, "{coverage}.tif".format(coverage=c))
            outfiles.append(filename)
            f = open(filename, 'wb')
            f.write(wcsfp.read())
            f.close()
        
        # Compute depth-length weighted-average for each coverage using gdal_calc.py
        assert(len(outfiles) == len(COVERAGES))
        gdalCommand = gdalCmdPath
        
        soilPropertyName = "soil_avg{var}_rast".format(var=v)
        soilPropertyFilename = "{name}.tif".format(name=soilPropertyName)
        soilPropertyFilepathTmp = os.path.join(tmpdir, soilPropertyFilename)
        soilPropertyFilepath = os.path.join(outputDir, soilPropertyFilename)
        
        calcStr = '0' # Identity element for addition
        for (i, outfile) in enumerate(outfiles):
            ord = i + 1
            var_label = ordinalToAlpha(ord)
            gdalCommand += " -{var} {outfile}".format(var=var_label, outfile=outfile)
            calcStr += "+({weight}*{var})".format(weight=weights[i],
                                                  var=var_label)
            
        gdalCommand += " --calc='{calc}' --outfile={outfile} --type='Float32' --format=GTiff --co='COMPRESS=LZW'".format(calc=calcStr,
                                                                                                                         outfile=soilPropertyFilepathTmp)
        
        #print("GDAL command:\n{0}".format(gdalCommand))
        returnCode = os.system(gdalCommand)
        if returnCode != 0:
            raise Exception("GDAL command %s failed." % (gdalCommand,))     
    
        # Resample raster
        resampleRaster(config, outputDir, soilPropertyFilepathTmp, soilPropertyFilename,
                       'EPSG:4326', crs, resx, resy)
    
        soilPropertyRasters[soilPropertyName] = soilPropertyFilepath
    
    # Clean-up
    #shutil.rmtree(tmpdir)
    
    return soilPropertyRasters
        
        