"""@package ecohydrolib.util
    
@brief Catch-all location for miscellaneous utility functions

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


def getAbsolutePathOfItem(item):
    """ Attempt to get absolute path of items that exist in the file system.
        For non-existant items, quote spaces.
    
        @param item String representing item
        @return String representing the absolute path of the item.  If the item
        is not an existing file, the item string will be returned, but any 
        spaces will be quoted
    """
    if os.path.exists(item):
        result = os.path.abspath(item)
    else:
        if item.find(' ') != -1:
            # If a non-path item has spaces in it, quote them
            result = '"' + item + '"'
        else:
            result = item
            
    return result

def isExecutable(filepath):
        """ Check if a path is an executable file
            @param filepath String representing the path
            @return True if the path represents an executable file
        """
        return os.path.isfile(filepath) and os.access(filepath, os.X_OK)

def getAbsolutePathOfExecutable(program):
    """ Return the absolute path of an executable by searching through the
        PATH environment variable. 
        
        @note Adapted from http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
         
        @param program String representing the program
        
        @return The absolute path of the program, or None if the program was
        not found
    """
    fpath, fname = os.path.split(program)
    if fpath:
        if isExecutable(program):
            return os.path.abspath(program)
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            executable = os.path.join(path, program)
            if isExecutable(executable):
                return executable

    return None