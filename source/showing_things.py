# -*- coding: utf-8 -*-
import arcgisscripting
import os

import arcpy


def show_things(thing_path, lyr_name, folder):

    gp = arcgisscripting.create()

    # Adding the layer to the table of contents
    mxd = arcpy.mapping.MapDocument("current")
    df = arcpy.mapping.ListDataFrames(mxd, "Layers")[0]

    file_type = arcpy.Describe(thing_path).dataType

    if file_type == u'RasterDataset':
        if not arcpy.Exists(thing_path):
            name_temp = os.path.join(folder, 'temp', '{}.tif'.format(os.path.split(thing_path)[-1]))
            arcpy.CopyRaster_management(thing_path, name_temp)
            arcpy.MakeRasterLayer_management(in_raster=name_temp, out_rasterlayer=lyr_name)
        else:
            arcpy.MakeRasterLayer_management(in_raster=thing_path, out_rasterlayer=lyr_name)
    elif (file_type == u'ShapeFile') or (file_type == u'FeatureClass'):
        if not arcpy.Exists(thing_path):
            name_temp = os.path.join(folder, 'temp', '{}.shp'.format(os.path.split(thing_path)[-1]))
            arcpy.CopyFeatures_management(thing_path, name_temp)
            arcpy.MakeFeatureLayer_management(in_features=name_temp, out_layer=lyr_name)
        else:
            arcpy.MakeFeatureLayer_management(in_features=thing_path, out_layer=lyr_name)
    else:
        gp.AddMessage('input file is not a raster or vector format')

    arcpy.SaveToLayerFile_management(lyr_name, os.path.join(folder, 'temp', '{}.lyr'.format(os.path.split(thing_path)[-1])), "ABSOLUTE")
    add_layer = arcpy.mapping.Layer(os.path.join(folder, 'temp', '{}.lyr'.format(os.path.split(thing_path)[-1])))
    arcpy.mapping.AddLayer(df, add_layer)
    arcpy.RefreshActiveView()
    arcpy.RefreshTOC()


def main():
    thing = arcpy.GetParameterAsText(0)
    lyr = arcpy.GetParameterAsText(1)
    folder = arcpy.GetParameterAsText(2)
    show_things(thing, lyr, folder)


if __name__ == '__main__':
    main()
