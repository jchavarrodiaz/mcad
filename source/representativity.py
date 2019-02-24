# -*- coding: utf-8 -*-
import os

import arcpy
import pandas as pd

from flores import table2csv
from utilities import rename_fields


def clear_layers():
    mxd = arcpy.mapping.MapDocument('CURRENT')
    for df in arcpy.mapping.ListDataFrames(mxd):
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            arcpy.mapping.RemoveLayer(df, lyr)
    del mxd


def parks_reps(gdb, uttl, parks, epsg, pixel, config, id_join):

    results_folder = os.path.dirname(gdb)
    temp_folder = os.path.join(results_folder, 'temp')

    arcpy.env.workspace = results_folder
    arcpy.env.overwriteOutput = True

    xls_file = pd.ExcelFile(config)
    df_criteria = xls_file.parse('Representatividad', index_col='Clases')

    if arcpy.Exists(os.path.join(temp_folder, 'Shape_Reps_Reprojected.shp')):
        arcpy.Delete_management(os.path.join(temp_folder, 'Shape_Reps_Reprojected.shp'))

    if arcpy.Exists(os.path.join(gdb, 'Reps_Table')):
        arcpy.Delete_management(os.path.join(gdb, 'Reps_Table'))
        arcpy.DeleteField_management(uttl, [u'RUNAP', u'Reps_Value_Calc', u'Reps_Value', u'Reps_Clase'])

    if arcpy.Exists(os.path.join(temp_folder, 'UTTL_Basins.shp')):
        arcpy.Delete_management(os.path.join(temp_folder, 'UTTL_Basins.shp'))

    if arcpy.Exists(os.path.join(temp_folder, 'RUNAP_Table.dbf')):
        arcpy.Delete_management(os.path.join(temp_folder, 'RUNAP_Table.dbf'))

    arcpy.Project_management(in_dataset=parks, out_dataset=os.path.join(temp_folder, 'Shape_Reps_Reprojected.shp'), out_coor_system=epsg)

    arcpy.FeatureToRaster_conversion(os.path.join(temp_folder, 'Shape_Reps_Reprojected.shp'), "OBJECTID", os.path.join(temp_folder, 'RUNAP.tif'), pixel)

    arcpy.MakeFeatureLayer_management(uttl, 'UTTL')
    arcpy.CopyFeatures_management('UTTL', os.path.join(temp_folder, r'UTTL_Basins.shp'))
    arcpy.gp.ZonalStatisticsAsTable_sa(os.path.join(temp_folder, 'UTTL_Basins.shp'), id_join, os.path.join(temp_folder, 'RUNAP.tif'), os.path.join(temp_folder, 'RUNAP_Table.dbf'), "DATA", "MEAN")
    table2csv(os.path.join(temp_folder, 'RUNAP_Table.dbf'), os.path.join(temp_folder, 'RUNAP_Table.csv'))
    table2csv(uttl, os.path.join(temp_folder, 'UTTL_Table_Areas.csv'))

    df_runap = pd.DataFrame(pd.read_csv(os.path.join(temp_folder, 'RUNAP_Table.csv'), index_col=id_join)['AREA'])
    df_uttl = pd.DataFrame(pd.read_csv(os.path.join(temp_folder, 'UTTL_Table_Areas.csv'), index_col=id_join)['Shape_Area'])

    df_uttl['RUNAP'] = 0.0
    df_uttl.ix[df_runap.index, 'RUNAP'] = df_runap['AREA']
    df_uttl['Reps_Value_Calc'] = (df_uttl['RUNAP'] / df_uttl['Shape_Area']) * 100.

    df_uttl['Reps_Value'] = df_criteria.ix['No RP', 'Value']
    df_uttl['Reps_Clase'] = 'No Representativo'

    df_index_query = df_uttl[(df_uttl['Reps_Value_Calc'] > df_criteria.ix['Baja', 'Inferior']) & (df_uttl['Reps_Value_Calc'] <= df_criteria.ix['Baja', 'Superior'])].index
    df_uttl.ix[df_index_query, 'Reps_Value'] = df_criteria.ix['Baja', 'Value']
    df_uttl.ix[df_index_query, 'Reps_Clase'] = 'Baja'

    df_index_query = df_uttl[(df_uttl['Reps_Value_Calc'] > df_criteria.ix['Media', 'Inferior']) & (df_uttl['Reps_Value_Calc'] <= df_criteria.ix['Media', 'Superior'])].index
    df_uttl.ix[df_index_query, 'Reps_Value'] = df_criteria.ix['Media', 'Value']
    df_uttl.ix[df_index_query, 'Reps_Clase'] = 'Media'

    df_index_query = df_uttl[(df_uttl['Reps_Value_Calc'] > df_criteria.ix['Alta', 'Inferior']) & (df_uttl['Reps_Value_Calc'] <= df_criteria.ix['Alta', 'Superior'])].index
    df_uttl.ix[df_index_query, 'Reps_Value'] = df_criteria.ix['Alta', 'Value']
    df_uttl.ix[df_index_query, 'Reps_Clase'] = 'Alta'

    df_index_query = df_uttl[(df_uttl['Reps_Value_Calc'] > df_criteria.ix['Muy Alta', 'Inferior']) & (df_uttl['Reps_Value_Calc'] <= df_criteria.ix['Muy Alta', 'Superior'])].index
    df_uttl.ix[df_index_query, 'Reps_Value'] = df_criteria.ix['Muy Alta', 'Value']
    df_uttl.ix[df_index_query, 'Reps_Clase'] = 'Muy Alta'

    df_join = df_uttl[[u'RUNAP', u'Reps_Value_Calc', u'Reps_Value', u'Reps_Clase']].copy()
    df_join.to_csv(os.path.join(temp_folder, 'Reps_Table_Join.csv'))

    arcpy.TableToTable_conversion(os.path.join(temp_folder, 'Reps_Table_Join.csv'), gdb, 'Reps_Table')

    expression = 'str(!Name!)'
    code_block = ''
    arcpy.AddField_management(os.path.join(gdb, 'Reps_Table'), 'Code', 'TEXT', '', '', '10', '', 'NULLABLE', 'NON_REQUIRED', '')
    arcpy.CalculateField_management(os.path.join(gdb, 'Reps_Table'), 'Code', expression, 'PYTHON', code_block)

    arcpy.MakeFeatureLayer_management(uttl, 'UTTL')
    arcpy.AddJoin_management('UTTL', 'Name', os.path.join(gdb, 'Reps_Table'), 'Code')

    arcpy.CopyFeatures_management('UTTL', os.path.join(gdb, r'UTTL_Basins_Reps'))
    arcpy.Delete_management('UTTL')
    arcpy.Delete_management(uttl)

    arcpy.Rename_management(os.path.join(gdb, r'UTTL_Basins_Reps'), uttl)
    clear_layers()
    rename_fields(os.path.join(gdb, r'UTTL_Basins'))
    rename_fields(os.path.join(gdb, r'UTTL_Basins'), r'Reps_Table')

    base_name = ['Reps_Table_OBJECTID', 'Reps_Table_Name', 'Code']
    arcpy.DeleteField_management(uttl, [i for i in base_name])


def main(env):
    arcpy.CheckOutExtension('Spatial')

    if env:
        uttl = arcpy.GetParameterAsText(0)
        id_uttl = arcpy.GetParameterAsText(1)
        parks_path = arcpy.GetParameterAsText(2)
        epsg = arcpy.GetParameterAsText(3)
        pixel_size = arcpy.GetParameterAsText(4)
        config_file = arcpy.GetParameterAsText(5)
    else:
        uttl = r'C:\DIRECTOS\results\UTTL.gdb\UTTL_Basins'
        id_uttl = 'Name'
        parks_path = r'C:\DIRECTOS\data\RUNAP.shp'
        epsg = 3116
        pixel_size = '93'
        config_file = r'C:\DIRECTOS\data\config_criteria.xlsx'

    clear_layers()
    gdb_path = os.path.dirname(uttl)
    parks_reps(gdb_path, uttl, parks_path, epsg, pixel_size, config_file, id_uttl)


if __name__ == '__main__':
    main(env=True)
