"""@package ecohydrolib.tests.test_nhdwebsvc
    
    @brief Test methods for ecohydrolib.nhdplus2.webservice
    
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
    
    Usage: 
    @code
    python -m unittest test_metadata
    @endcode
    
""" 
import unittest
import traceback
import os, sys
import tempfile, shutil

from ecohydrolib.context import Context

from ecohydrolib.nhdplus2.webservice import WebserviceError
from ecohydrolib.nhdplus2.webservice import getCatchmentFeaturesForStreamflowGage
from ecohydrolib.nhdplus2.webservice import locateStreamflowGage
from ecohydrolib.nhdplus2.webservice import RESPONSE_OK

class Test(unittest.TestCase):

    def setUp(self):
        self.projectDir = tempfile.mkdtemp()
        self.context = Context(projectDir=self.projectDir)
        
    def tearDown(self):
        shutil.rmtree(self.projectDir)

    def testLocateStreamflowGage(self):
        badGage = "3ti04ti04tgi0"
        (response, url) = locateStreamflowGage(self.context.config, badGage)
        self.assertTrue( response['message'] == "Illegal gageid '%s'" % (badGage,) )
        
        unknownGage = "123456789101112"
        (response, url) = locateStreamflowGage(self.context.config, unknownGage)
        self.assertTrue( response['message'] == "Reachcode for gage '%s' not found" % (unknownGage,) )

        goodGage = "01589312"
        (response, url) = locateStreamflowGage(self.context.config, goodGage)
        self.assertTrue( response['message'] == RESPONSE_OK )
        self.assertTrue( response['measure'] == 75.06239 )
        self.assertTrue( response['gage_lon'] == -76.74433974864309 )
        self.assertTrue( response['gage_lat'] == 39.295559099434264 )
        self.assertTrue( response['reachcode'] == "02060003000745" )

    def testGetCatchmentFeaturesForStreamflowGage(self):
        goodReachcode = "02060003000745"
        goodMeasure = 75.06239
        badReachcode = "klsdklasd"
        badMeasure = "sdfklfkl"

        # Bad reachcode
        exceptionThrown = False
        try:
            (shapefileName, url) = getCatchmentFeaturesForStreamflowGage(self.context.config, self.projectDir,
                                                                         'catchment', badReachcode, goodMeasure)
        except WebserviceError:
            exceptionThrown = True
        except Exception:
            raise
        
        self.assertTrue( exceptionThrown )
        
        # Bad measure
        exceptionThrown = False
        try:
            (shapefileName, url) = getCatchmentFeaturesForStreamflowGage(self.context.config, self.projectDir,
                                                                         'catchment', goodReachcode, badMeasure)
        except WebserviceError:
            exceptionThrown = True
        except Exception:
            raise
        
        self.assertTrue( exceptionThrown )
        
        # Good case
        exceptionThrown = False
        try:
            (shapefileName, url) = getCatchmentFeaturesForStreamflowGage(self.context.config, self.projectDir,
                                                                         'catchment', goodReachcode, goodMeasure)
        except:
            traceback.print_exc(file=sys.stdout)
            exceptionThrown = True
        
        self.assertTrue( not exceptionThrown )
        self.assertTrue( shapefileName == 'catchment.shp' )
        self.assertTrue( os.path.exists( os.path.join( self.projectDir, shapefileName ) ) )

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()