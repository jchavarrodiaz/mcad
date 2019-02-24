# -*- coding: utf-8 -*-
import os

import arcpy
import pandas as pd


def clear_layers():
    mxd = arcpy.mapping.MapDocument('CURRENT')
    for df in arcpy.mapping.ListDataFrames(mxd):
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            arcpy.mapping.RemoveLayer(df, lyr)
    del mxd


def rename_fields(shape_path, str_remove=None):

    clear_layers()

    if str_remove is None:
        str_remove = os.path.split(shape_path)[-1]

    field_list = arcpy.ListFields(shape_path)
    for field in field_list:
        if str(str_remove) in str(field.name):
            try:
                new_basename = str(field.name).replace('{}_'.format(str(str_remove)), '')
                arcpy.AlterField_management(shape_path, field.name, new_basename)
            except :
                print 'The {} already exists into the attribute table'.format(new_basename)


def main(env):
    arcpy.CheckOutExtension('Spatial')
    if env:
        shp_path = arcpy.GetParameterAsText(0)
        str_remove = arcpy.GetParameterAsText(1)
    else:
        shp_path = r'C:\DIRECTOS\results\UTTL.gdb\UTTL_Basins'
        str_remove = None

    print str_remove

    rename_fields(shp_path, str_remove)


if __name__ == '__main__':
    main(env=False)
