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
from subprocess import *

from owslib.wcs import WebCoverageService

from ecohydrolib.spatialdata.utils import RASTER_RESAMPLE_METHOD
from ecohydrolib.spatialdata.utils import resampleRaster

FORMAT_GEOTIFF = 'GeoTIFF'
FORMATS = set([FORMAT_GEOTIFF])
MIME_TYPE = {FORMAT_GEOTIFF: 'image/GeoTIFF'}

VARIABLE = {'clay': 'CLY',
            'silt': 'SLT',
            'sand': 'SND'
            }

URL_BASE = "http://www.asris.csiro.au/ArcGis/services/TERN/{variable}_ACLEP_AU_TRN_N/MapServer/WCSServer"
DC_PUBLISHER = "http://www.clw.csiro.au/aclep/soilandlandscapegrid/"

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
                                     srs='EPSG:4326',
                                     resx=0.000277777777778,
                                     resy=0.000277777777778,
                                     interpolation='bilinear',
                                     fmt=FORMAT_GEOTIFF, 
                                     overwrite=False,
                                     verbose=False,
                                     outfp=sys.stdout):
    """
        Download soil property rasters from http://www.clw.csiro.au/aclep/soilandlandscapegrid/
        For each property, rasters for the first 1-m of the soil profile will be downloaded
        from which the depth-weighted mean of the property will be calculated and stored in outpufDir
    
        @param config A Python ConfigParser (not currently used)
        @param outputDir String representing the absolute/relative path of the directory into which output raster should be written
        @param bbox Dict representing the lat/long coordinates and spatial reference of the bounding box area
            for which the raster is to be extracted.  The following keys must be specified: minX, minY, maxX, maxY, srs.
        @param srs String representing the spatial reference of the raster to be returned.
        @param resx Float representing the X resolution of the raster(s) to be returned
        @param resy Float representing the Y resolution of the raster(s) to be returned
        @param interpolation String representing resampling method to use. Must be one of spatialdatalib.utils.RASTER_RESAMPLE_METHOD.
        @param fmt String representing format of raster file.  Must be one of FORMATS.
        @param overwrite Boolean True if existing data should be overwritten
        @param verbose Boolean True if detailed output information should be printed to outfp
        @param outfp File-like object to which verbose output should be printed
    
        @return A dictionary mapping soil property names to soil property file path and WCS URL, i.e.
            dict[soilPropertyName] = (soilPropertyFilePath, WCS URL)
    
        @exception Exception if interpolation method is not known
        @exception Exception if fmt is not a known format
        @exception Exception if output already exists by overwrite is False
        @exception Exception if a gdal_calc.py command fails
    """
    if interpolation not in RASTER_RESAMPLE_METHOD:
        raise Exception("Interpolation method {0} is not of a known method {1}".format(interpolation,
                                                                                       RASTER_RESAMPLE_METHOD))
    if fmt not in FORMATS:
        raise Exception("Format {0} is not of a known format {1}".format(fmt, str(FORMATS)))
    if verbose:
        outfp.write("Acquiring soils data from {0}\n".format(DC_PUBLISHER))
    
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
    #print(tmpdir)
    
    bbox = [bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY']]
    
    # For each soil variable, download desired depth layers
    for v in VARIABLE.keys():
        variable = VARIABLE[v]
        
        soilPropertyName = "soil_raster_pct{var}".format(var=v)
        soilPropertyFilename = "{name}.tif".format(name=soilPropertyName)
        soilPropertyFilepathTmp = os.path.join(tmpdir, soilPropertyFilename)
        soilPropertyFilepath = os.path.join(outputDir, soilPropertyFilename)
        
        if verbose:
            outfp.write("Getting attribute {0} ...\n".format(soilPropertyName))
        
        delete = False
        if os.path.exists(soilPropertyFilepath):
            if not overwrite:
                raise Exception("File {0} already exists, and overwrite is false".format(soilPropertyFilepath))
            else:
                delete = True
        
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
                                    resx=resx, # their WCS seems to accept resx, resy in meters
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
        process = Popen(gdalCommand, cwd=outputDir, shell=True,
                        stdout=PIPE, stderr=PIPE)
        (process_stdout, process_stderr) = process.communicate()
        if process.returncode != 0:
            raise Exception("GDAL command {0} failed, returning {1}\nstdout:\n{2}\nstderr:\n{3}\n.".format(gdalCommand, 
                                                                                                           process.returncode,
                                                                                                           process_stdout,
                                                                                                           process_stderr))
        if verbose:
            outfp.write(process_stdout)
            outfp.write(process_stderr)
    
        # Resample raster
        if delete:
            os.unlink(soilPropertyFilepath)
        resampleRaster(config, outputDir, soilPropertyFilepathTmp, soilPropertyFilename,
                       'EPSG:4326', srs, resx, resy, resampleMethod=interpolation)
    
        soilPropertyRasters[soilPropertyName] = (soilPropertyFilepath, wcs.url)
    
    # Clean-up
    shutil.rmtree(tmpdir)
    
    return soilPropertyRasters
        
        