EcohydrologyWorkflowLib
=======================

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
    * Neither the name of the University of North Carolina at Chapel Hill nor 
      the names of its contributors may be used to endorse or promote products
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


Authors
-------
Brian Miles <brian_miles@unc.edu>
Lawrence E. Band <lband@email.unc.edu>


Introduction
------------
TODO: WRITE


Required runtime software
-------------------------
* GDAL/OGR binaries (throughout)
* Seven Zip binary (NHDPlusV2Setup.py)
* SQLite3 binary (NHDPlusV2Setup.py)
* Unix find binary (NHDPlusV2Setup.py)


Required data
-------------
* NLCD 2006 raster (TODO: add download URL)
* NHDPlus V2 dataset (TODO: add download URL)


NHDPlus V2 database setup
-------------------------
TODO: WRITE


Configuration files
-------------------
TODO: WRITE


How to use - A typical workflow
-------------------------------
TODO: FINISH
1. GetNHDStreamflowGageIdentifiersAndLocation.py

2. GetCatchmentShapefileForStreamflowGage.py

3. GetBoundingboxFromStudyAreaShapefile.py

4. GetDEMForBoundingbox.py

5. GetNLCDForBoundingbox.py

6. GetSSURGOFeaturesForBoundingbox.py



