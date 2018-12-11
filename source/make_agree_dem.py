# -*- coding: utf-8 -*-

import arcgisscripting
import os

import ArcHydroTools
import arcpy

# Replace a layer/table view name with a path to a dataset (which can be a layer file)
# or create the layer/table view within the script
# The following inputs are layers or table views: "dobles", "srtm_orinoco_4326.tif"
arcpy.PolygonToRaster_conversion(in_features="dobles", value_field="RuleID",
                                 out_rasterdataset="D:/BASES/AGREE_DEM/Rasterize/orinoco_dobles.tif",
                                 cell_assignment="MAXIMUM_COMBINED_AREA", priority_field="RuleID",
                                 cellsize="srtm_orinoco_4326.tif")
