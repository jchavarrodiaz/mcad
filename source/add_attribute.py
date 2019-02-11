#!/usr/bin/env python
# -*- coding: utf-8 -*-
import arcgisscripting
import os
import sys

import arcpy
import numpy as np
import pandas as pd
import unicodedata
from arcpy.sa import *

gp = arcgisscripting.create()

# get spatial analyst extension, required for the tool
if arcpy.CheckExtension("Spatial") == "Available":
    arcpy.AddMessage("Checking out Spatial")
    arcpy.CheckOutExtension("Spatial")
else:
    arcpy.AddError("Unable to get spatial analyst extension")
    sys.exit(-2)


def check_arcmap_field(c):
    s = ''.join(c.split(' '))
    return ''.join([i for i in s])[:10]


def zonal_stats(feat, raster, new_name, stats='MEAN'):
    gdb_path = os.path.dirname(os.path.abspath(feat))
    arcpy.env.workspace = '{}'.format(os.path.dirname(os.path.abspath(gdb_path)))
    arcpy.env.overwriteOutput = True
    arcpy.env.qualifiedFieldNames = False

    gp.AddMessage('Making temps folders')
    temp_folder = '{}/temp'.format(os.path.dirname(os.path.abspath(gdb_path)))

    if os.path.exists(temp_folder):
        gp.AddMessage('folder temp already exists')
    else:
        os.mkdir(temp_folder)

    gp.AddMessage("Performing Zonal Statistics as Table")
    table = os.path.join(temp_folder, '{}.dbf'.format(os.path.basename(raster).split('.')[0]))
    ZonalStatisticsAsTable(feat, 'OBJECTID', raster, table, 'DATA', stats)
    # check if the 'to' field exists and if not found then add it
    if len(arcpy.ListFields(feat, new_name)) == 0:
        gp.AddMessage('Adding {} field'.format(new_name))
        arcpy.AddField_management(feat, new_name, 'DOUBLE')
    else:
        gp.AddMessage('Deleting {} field'.format(new_name))
        arcpy.DeleteField_management(feat, new_name)
        gp.AddMessage('Adding {} field'.format(new_name))
        arcpy.AddField_management(feat, new_name, 'DOUBLE')

    # joins are annoying but you #should# be able to do it this way
    # joins must be performed on a Layer or Table View object...
    arcpy.MakeFeatureLayer_management(feat, 'Layer')
    arcpy.AddJoin_management('Layer', 'OBJECTID', table, 'OBJECTID')
    if stats == 'MAXIMUM':
        stats = 'MAX'
    arcpy.CalculateField_management('Layer', new_name, '!{}.{}!'.format(os.path.basename(raster).split('.')[0], stats), 'PYTHON')


def attribute_from_vector(feat, obj, field, id_index):
    gdb_path = os.path.dirname(os.path.abspath(feat))
    arcpy.env.workspace = '{}'.format(os.path.dirname(os.path.abspath(gdb_path)))
    arcpy.env.overwriteOutput = True
    arcpy.env.qualifiedFieldNames = False

    gp.AddMessage('Making temps folders')
    temp_folder = r'{}\temp'.format(os.path.dirname(os.path.abspath(gdb_path)))

    if os.path.exists(temp_folder):
        gp.AddMessage('folder temp already exists')
    else:
        os.mkdir(temp_folder)

    # check if the 'to' field exists and if not found then add it
    if len(arcpy.ListFields(feat, field)) == 0:
        gp.AddMessage('the {} field doesnt exist'.format(field))
    else:
        gp.AddMessage('The {} field already exits'.format(field))
        arcpy.DeleteField_management(feat, field)

    gp.AddMessage('Intersect Analysis')
    arcpy.Intersect_analysis(in_features='{} #;{} #'.format(feat, obj),
                             out_feature_class='{}/UTTL_Basins_Intersect'.format(temp_folder),
                             join_attributes='NO_FID', cluster_tolerance="-1 Unknown",
                             output_type='INPUT')

    arcpy.AddField_management('{}/UTTL_Basins_Intersect.shp'.format(temp_folder), "Up_Area", "DOUBLE")
    exp = "!SHAPE.AREA@SQUAREKILOMETERS!"
    arcpy.CalculateField_management('{}/UTTL_Basins_Intersect.shp'.format(temp_folder), "Up_Area", exp, "PYTHON_9.3")

    arcpy.TableToTable_conversion('{}/UTTL_Basins_Intersect.shp'.format(temp_folder), temp_folder, 'UTTL_Basins_Intersect.csv')

    field = check_arcmap_field(field)
    df_table = pd.read_csv('{}/UTTL_Basins_Intersect.csv'.format(temp_folder))[[id_index, field, 'Up_Area']]

    idx = df_table.groupby(by=id_index, sort=False)['Up_Area'].transform(max) == df_table['Up_Area']
    df_sel_table = df_table[idx]

    df_join_table = df_sel_table.copy()
    df_join_table['Code'] = [str(i) for i in df_sel_table[id_index]]
    df_join_table.drop(labels=[id_index, 'Up_Area'], axis=1, inplace=True)
    df_join_table.columns = [field, id_index]

    df_join_table.to_csv('{}/UTTL_Basins_NewVectorAttribute.csv'.format(temp_folder))

    # check if the 'to' field exists and if not found then add it
    if len(arcpy.ListFields(feat, field)) == 0:
        gp.AddMessage('Adding {} field'.format(field))
        arcpy.AddField_management(feat, field, 'TEXT')
    else:
        gp.AddMessage('Deleting {} field'.format(field))
        arcpy.DeleteField_management(feat, field)
        gp.AddMessage('Adding {} field'.format(field))
        arcpy.AddField_management(feat, field, 'TEXT')

    x = np.array(np.rec.fromrecords(df_join_table.values))
    names = df_join_table.dtypes.index.tolist()
    x.dtype.names = tuple(names)
    arcpy.da.NumPyArrayToTable(x, r'{}\{}'.format(gdb_path, field))

    # joins are annoying but you #should# be able to do it this way
    # joins must be performed on a Layer or Table View object...
    arcpy.MakeFeatureLayer_management(feat, 'Layer')
    arcpy.AddJoin_management('Layer', id_index, r'{}\{}'.format(gdb_path, field), id_index)
    arcpy.CalculateField_management('Layer', field, '!{}.{}!'.format(field, field), 'PYTHON_9.3')
    gp.AddMessage('attribute {} added successfully'.format(field))


def add_attribute(object, feature, stats, new_att, uttl):

    filetype = arcpy.Describe(object).dataType

    if filetype == u'RasterDataset':
        zonal_stats(feat=feature, raster=object, new_name=new_att, stats=stats)
    elif (filetype == u'ShapeFile') or (filetype == u'FeatureClass'):
        attribute_from_vector(feat=feature, obj=object, field=new_att, id_index=uttl)
    else:
        gp.AddMessage('El archivo ingresado no corresponde con un formato matricial o vectorial')


def main(env):

    if env:
        uttl_feature = arcpy.GetParameterAsText(0)  # UTTL Polygons
        id_uttl_name = arcpy.GetParameterAsText(1)  # ID Name for UTTL Basin
        new_object = arcpy.GetParameterAsText(2)  # new object (raster or vector) from extract new information and add to attribute table of uttl units
        stats_type = arcpy.GetParameterAsText(3)  # MEAN, MODE, ..., etc.
        field_new_name = arcpy.GetParameterAsText(4)  # new name for uttl's attribute

        new = unicodedata.normalize('NFD', field_new_name).encode('ascii', 'ignore')

        add_attribute(object=new_object, feature=uttl_feature, stats=stats_type, new_att=new, uttl=id_uttl_name)

    else:
        uttl_feature = r'C:\Users\jchav\AH_01\CATATUMBO\results\UTTL.gdb\UTTL_Basins'  # UTTL Polygons
        id_uttl_name = 'Name'
        new_object = r'C:\Users\jchav\AH_01\CATATUMBO\data\Regimen_Hidrologico\Regimen_Hidrologico_3116.shp'  # new object (raster or vector) for from extract new information and add to attribute table of uttl units
        stats_type = 'MEAN'  # MEAN, MODE, ..., etc.
        field_new_name = u'regimen'  # new name for uttl's attribute [the field name with less of 10 characters]

        new = unicodedata.normalize('NFD', field_new_name).encode('ascii', 'ignore')

        add_attribute(object=new_object, feature=uttl_feature, stats=stats_type, new_att=new, uttl=id_uttl_name)


if __name__ == '__main__':
    main(env=True)
