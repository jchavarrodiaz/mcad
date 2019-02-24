# -*- coding: utf-8 -*-
import os

import arcpy
import pandas as pd

from add_attribute import zonal_stats
from flores import table2csv
from utilities import rename_fields


def save_mxd():
    mapdoc = arcpy.mapping.MapDocument('CURRENT')
    mapdoc.save()


def clear_layers():
    mxd = arcpy.mapping.MapDocument('CURRENT')
    for df in arcpy.mapping.ListDataFrames(mxd):
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            arcpy.mapping.RemoveLayer(df, lyr)
    del mxd


def species(gdb, uttl, sp, epsg, id_join, config_file):

    results_folder = os.path.dirname(gdb)
    temp_folder = os.path.join(results_folder, 'temp')
    species_proj = os.path.join(temp_folder, 'species.tif')

    arcpy.env.workspace = results_folder
    arcpy.env.overwriteOutput = True

    if arcpy.Exists(os.path.join(gdb, 'Species_Table')):
        try:
            arcpy.Delete_management(os.path.join(gdb, 'Species_Table'))
            arcpy.DeleteField_management(uttl, [u'sp_mean', u'sp_value', u'sp_class'])
        except ImportError:
            pass

    xls_file = pd.ExcelFile(config_file)
    df_criteria = xls_file.parse('Especies_Sensibles', index_col='Clases')
    low_lim = df_criteria.ix['Baja', 'Superior']
    high_lim = df_criteria.ix['Alta', 'Inferior']

    arcpy.ProjectRaster_management(sp, species_proj, epsg, 'NEAREST')
    zonal_stats(uttl, species_proj, 'sp_mean')

    table2csv(uttl, os.path.join(temp_folder, 'species.csv'))
    arcpy.DeleteField_management(uttl, [u'sp_mean'])
    df_spe = pd.read_csv(os.path.join(temp_folder, 'species.csv'), index_col=id_join)

    df_spe['sp_mean'].fillna(value=0, inplace=True)
    df_spe['sp_mean'] = df_spe['sp_mean'] * 100.
    df_spe['sp_value'] = df_criteria.ix['Media', 'Value']
    df_spe.ix[df_spe[df_spe['sp_mean'] <= low_lim].index, 'sp_value'] = df_criteria.ix['Baja', 'Value']
    df_spe.ix[df_spe[df_spe['sp_mean'] > high_lim].index, 'sp_value'] = df_criteria.ix['Alta', 'Value']

    df_spe['sp_class'] = 'Media'
    df_spe.ix[df_spe[df_spe['sp_mean'] <= low_lim].index, 'sp_class'] = 'Baja'
    df_spe.ix[df_spe[df_spe['sp_mean'] > high_lim].index, 'sp_class'] = 'Alta'

    df_join = df_spe[['sp_mean', 'sp_value', 'sp_class']].copy()

    df_join.to_csv(os.path.join(temp_folder, 'Species_Table_Join.csv'))

    arcpy.TableToTable_conversion(os.path.join(temp_folder, 'Species_Table_Join.csv'), gdb, 'Species_Table')

    expression = 'str(!Name!)'
    code_block = ''
    arcpy.AddField_management(os.path.join(gdb, 'Species_Table'), 'Code', 'TEXT', '', '', '10', '', 'NULLABLE', 'NON_REQUIRED', '')
    arcpy.CalculateField_management(os.path.join(gdb, 'Species_Table'), 'Code', expression, 'PYTHON', code_block)

    arcpy.MakeFeatureLayer_management(uttl, 'UTTL')
    arcpy.AddJoin_management('UTTL', 'Name', os.path.join(gdb, 'Species_Table'), 'Code')

    arcpy.CopyFeatures_management('UTTL', os.path.join(gdb, r'UTTL_Basins_Species'))
    arcpy.Delete_management('UTTL')
    arcpy.Delete_management(uttl)

    arcpy.Rename_management(os.path.join(gdb, r'UTTL_Basins_Species'), uttl)
    clear_layers()
    rename_fields(os.path.join(gdb, r'UTTL_Basins'))
    rename_fields(os.path.join(gdb, r'UTTL_Basins'), r'Species_Table')

    base_name = ['OBJECTID_1', 'Name_1', 'Code']
    arcpy.DeleteField_management(uttl, [i for i in base_name])


def main(env):
    arcpy.CheckOutExtension('Spatial')

    if env:
        uttl = arcpy.GetParameterAsText(0)
        id_uttl = arcpy.GetParameterAsText(1)
        epsg = arcpy.GetParameterAsText(2)
        path_species = arcpy.GetParameterAsText(3)
        config_file = arcpy.GetParameterAsText(4)
        clear_layers()
        save_mxd()
    else:
        uttl = r'C:\DIRECTOS\results\UTTL.gdb\UTTL_Basins'
        id_uttl = 'Name'
        epsg = 3116
        path_species = r'C:\DIRECTOS\data\especies_sensibles\CaribeCutEcoAcua.tif'
        config_file = r'C:\DIRECTOS\data\config_criteria.xlsx'

    gdb_path = os.path.dirname(uttl)
    species(gdb_path, uttl, path_species, epsg, id_uttl, config_file)


if __name__ == '__main__':
    main(env=True)
