from ecohydrolib.spatialdata.utils import writeCoordinatePairsToPointShapefile
out = "/Users/miles/Dropbox/EarthCube-Multilayered/RHESSys-workflow/scratchspace"
layer = "DR5_gage"
idAttr = "gage_id"
coords = [ (-76.7443397486, 39.2955590994) ]
ids = [ '01589312' ]
writeCoordinatePairsToPointShapefile(out, layer, idAttr, ids, coords)
