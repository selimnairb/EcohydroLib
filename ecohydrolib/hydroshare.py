"""@package ecohydrolib.hydroshare
    
@brief Utilities for interacting with HydroShare (http://www.hydroshare.org/)

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
import sys
import os
import tempfile
import zipfile
import shutil

from hs_restclient import HydroShare, HydroShareAuthBasic

from clint.textui.progress import Bar


def create_console_callback(size):
    """ 
    Create progress callback suitable for displaying the progress of a
    requests_toolbelt.MultipartEncoderMonitor to a text console.
    
    @param size int representing the number of bytes to be read be the
    MultipartEncoderMonitor
    """
    bar = Bar(expected_size=size, filled_char=u'\u25A0', every=1024)
    def callback(monitor):
        bar.show(monitor.bytes_read)
    return callback

def _getResourceURL(resource_id, hs_host='www.hydroshare.org', hs_port=None, use_https=False):
    # Hackish temporary function until the HydroShare API makes it
    # possible to get the web client URL for a resource programatically
    if hs_host is None:
        hs_host = 'www.hydroshare.org'
    scheme = None 
    if use_https:
        scheme = 'https://'
    else:
        scheme = 'http://'
    url = None
    if hs_port:
        url = "{scheme}{host}:{port}/resource/{id}/".format(scheme=scheme,
                                                            host=hs_host,
                                                            port=hs_port,
                                                            id=resource_id)
    else:
        url = "{scheme}{host}/resource/{id}/".format(scheme=scheme,
                                                     host=hs_host,
                                                     id=resource_id)
    return url

def _addToZip((project_dir, zfile), dirname, names):
    clean_dir = os.path.relpath(dirname, project_dir)
    for name in names:
        filename = os.path.join(dirname, name)
        arcname = os.path.join(clean_dir, name)
        zfile.write(filename, arcname)

def get_password_authentication(username, password):
    """
    Get HydroShare authentication object that can be
    used to authenticate using a username and password
    
    @param username string
    @param password string
    
    @return HydroShareAuth object
    """
    return HydroShareAuthBasic(username, password)

def create_hydroshare_resource(context,
                               auth,
                               title,
                               hydroshare_host='www.hydroshare.org', 
                               hydroshare_port=None, use_https=False,
                               resource_type='GenericResource',
                               abstract=None,
                               keywords=None,
                               create_callback=None,
                               verbose=False,
                               outfp=sys.stderr):
    """
    Create HydroShare resource of an EcohydroLib project
    
    @param context ecohydrolib.Context object
    @param auth hs_restclient.HydroShareAuth object
    @param title string representing the title of the resource
    @param hydroshare_host string representing DNS name of the HydroShare 
        server in which to create the resource
    @param hydroshare_port int representing the TCP port of the HydroShare 
        server
    @param use_https True if HTTPS should be used.  Default: False
    @param resource_type string representing the HydroShare resource type
        that should be used to create the resource
    @param abstract string representing the abstract of the resource
    @param keywords list of strings representing the keywords to assign
        to the resource
    @param create_callback user-defined callable that takes as input a 
        file size in bytes, and generates a callable to provide feedback 
        to the user about the progress of the upload of resource_file.  
        For more information, see:
        http://toolbelt.readthedocs.org/en/latest/uploading-data.html#monitoring-your-streaming-multipart-upload
    @param verbose Boolean True if detailed output information should be printed to outfp
    @param outfp File-like object to which verbose output should be printed
    
    @return string representing the ID of the newly created resource
    """
    temp_dir = tempfile.mkdtemp()
    zip_filename = "{0}.zip".format(os.path.basename(context.projectDir))
    zip_filepath = os.path.join(temp_dir, zip_filename)
    
    # Zip up the project for upload ...
    if verbose:
        outfp.write("Creating archive...")
        outfp.flush()
    zfile = zipfile.ZipFile(zip_filepath, 'w', 
                            zipfile.ZIP_DEFLATED,
                            True)
    os.path.walk(context.projectDir, _addToZip, (context.projectDir, zfile))
    zfile.close()
    if verbose:
        outfp.write("done\n")
        outfp.flush()
    
    # Make upload progress callback
    progress_callback = None
    if create_callback:
        s = os.stat(zip_filepath)
        progress_callback = create_callback(s.st_size)
    
    if verbose:
        outfp.write("Uploading to HydroShare...")
        outfp.flush()
        # This next line is needed for some text-based progress indicators 
        # to properly render.
        outfp.write("                               \nThis is a hack\r")
        outfp.flush()
    if hydroshare_host:
        hs = HydroShare(hostname=hydroshare_host, port=hydroshare_port,
                        use_https=use_https, auth=auth)
    else:
        hs = HydroShare(port=hydroshare_port,
                        use_https=use_https, auth=auth)
    resource_id = None
    try:
        resource_id = hs.createResource(resource_type, title, 
                                        resource_file=zip_filepath, resource_filename=zip_filename, 
                                        abstract=abstract, keywords=keywords,
                                        progress_callback=progress_callback)
        if verbose:
            url = _getResourceURL(resource_id, 
                                  hydroshare_host, hs_port=hydroshare_port, 
                                  use_https=use_https)
            outfp.write("\nNew resource created at:\n{0}\n".format(url))
            outfp.flush()
    except Exception as e:
        raise e
    finally:
        shutil.rmtree(temp_dir)
    
    return resource_id