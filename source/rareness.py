# -*- coding: utf-8 -*-
import os

import arcpy
import pandas as pd

from add_attribute import zonal_stats


def save_mxd(folder, name):
    mapdoc = arcpy.mapping.MapDocument('CURRENT')
    mapdoc.saveACopy(os.path.join(folder, '{}.mxd'.format(name)))


def clear_layers():
    mxd = arcpy.mapping.MapDocument('CURRENT')
    for df in arcpy.mapping.ListDataFrames(mxd):
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            arcpy.mapping.RemoveLayer(df, lyr)
    del mxd


def rareness(gdb, uttl, ah, zh, epsg, config):

    results_folder = os.path.dirname(gdb)
    temp_folder = os.path.join(results_folder, 'temp')
    zh_path = os.path.join(temp_folder, 'zh_temp.tif')

    arcpy.env.workspace = results_folder
    arcpy.env.overwriteOutput = True

    xls_file = pd.ExcelFile(config)
    df_zone_areas = xls_file.parse('ZH_Areas')[['ZH', 'Area_m2']]
    df_zone_areas.columns = ['ZH', 'ZH_Area']

    df_criteria = xls_file.parse('Rareza_Criterio_1', index_col='CLASE')

    ah_areas = {1: 103255800000,
                2: 272163400000,
                3: 346227100000,
                4: 341818300000,
                5: 77981870000}

    arcpy.ProjectRaster_management(zh, zh_path, epsg, 'NEAREST')

    zonal_stats(uttl, zh_path, 'ZH', 'MAJORITY')
    arcpy.TableToTable_conversion(uttl, temp_folder, 'UTTL_table_rare.csv')

    df_uttl = pd.read_csv(os.path.join(temp_folder, 'UTTL_table_rare.csv'), delimiter=',')
    df_type = pd.DataFrame(df_uttl.groupby(['TIPOLOGIA']).sum()['Shape_Area']).reset_index()
    df_type.columns = ['TIPOLOGIA', 'Cluster_Area']

    df_uttl = df_uttl.merge(right=df_type, on='TIPOLOGIA', how='left')
    df_uttl['AH_Area'] = ah_areas[ah]
    df_uttl['ZH'] = df_uttl['ZH'].values.astype(int)
    df_uttl = df_uttl.merge(right=df_zone_areas, on='ZH', how='left')
    df_uttl['Rar_Crit1_AH'] = (df_uttl['Cluster_Area'] / df_uttl['AH_Area']) * 100.
    df_uttl['Rar_Crit1_ZH'] = (df_uttl['Cluster_Area'] / df_uttl['ZH_Area']) * 100.

    cr_ah_upper = df_criteria.ix['Muy raro', 'AH_SUP_LIM_CERRADO']
    cr_ah_lower = df_criteria.ix['Poco raro', 'AH_INF']

    df_uttl['Rar_Crit1_AH_Class'] = df_criteria.ix['Medianamente raro', 'K']
    df_uttl.ix[df_uttl[df_uttl['Rar_Crit1_AH'] <= cr_ah_upper].index, 'Rar_Crit1_AH_Class'] = df_criteria.ix['Muy raro', 'K']
    df_uttl.ix[df_uttl[df_uttl['Rar_Crit1_AH'] > cr_ah_lower].index, 'Rar_Crit1_AH_Class'] = df_criteria.ix['Poco raro', 'K']

    cr_zh_upper = df_criteria.ix['Muy raro', 'ZH_SUP_LIM_CERRADO']
    cr_zh_lower = df_criteria.ix['Poco raro', 'ZH_INF']

    df_uttl['Rar_Crit1_ZH_Class'] = df_criteria.ix['Medianamente raro', 'K']
    df_uttl.ix[df_uttl[df_uttl['Rar_Crit1_ZH'] <= cr_zh_upper].index, 'Rar_Crit1_ZH_Class'] = df_criteria.ix['Muy raro', 'K']
    df_uttl.ix[df_uttl[df_uttl['Rar_Crit1_ZH'] > cr_zh_lower].index, 'Rar_Crit1_ZH_Class'] = df_criteria.ix['Poco raro', 'K']

    df_uttl['Rareza'] = (df_uttl['Rar_Crit1_ZH_Class'] + df_uttl['Rar_Crit1_AH_Class']) / 2.
    df_join = df_uttl[['Name', 'Rareza']]
    ls_val = [str(x) for x in df_join['Name']]
    df_join.loc[:, 'Name'] = ls_val
    df_join.to_csv(os.path.join(temp_folder, 'UTTL_table_rare_Class.csv'), index=False, )

    # Join Table to UTTL Segmentation Polygons
    if arcpy.Exists(os.path.join(gdb, 'Rareza')):
        arcpy.Delete_management(os.path.join(gdb, 'Rareza'))

    arcpy.TableToTable_conversion(os.path.join(temp_folder, 'UTTL_table_rare_Class.csv'), gdb, 'Rareza')

    expression = 'str(!Name!)'
    code_block = ''
    arcpy.AddField_management(os.path.join(gdb, 'Rareza'), 'Code', 'TEXT', '', '', '10', '', 'NULLABLE', 'NON_REQUIRED', '')
    arcpy.CalculateField_management(os.path.join(gdb, 'Rareza'), 'Code', expression, 'PYTHON', code_block)

    arcpy.MakeFeatureLayer_management(uttl, 'UTTL')
    arcpy.AddJoin_management('UTTL', 'Name', os.path.join(gdb, 'Rareza'), 'Code')

    arcpy.CopyFeatures_management('UTTL', os.path.join(temp_folder, r'UTTL_Basins.shp'))
    arcpy.CopyFeatures_management(os.path.join(temp_folder, r'UTTL_Basins.shp'), os.path.join(gdb, r'UTTL_Basins'))

    arcpy.DeleteFeatures_management(os.path.join(temp_folder, r'UTTL_Basins.shp'))

    del_field = ['OBJECTID_1', 'Name_1', 'Code', 'Shape_Leng']
    arcpy.DeleteField_management(os.path.join(gdb, r'UTTL_Basins'), [x for x in del_field])


def main(env):
    arcpy.CheckOutExtension('Spatial')

    if env:
        gdb_path = arcpy.GetParameterAsText(0)
        uttl = arcpy.GetParameterAsText(1)
        ah = arcpy.GetParameterAsText(2)
        zh_raster = arcpy.GetParameterAsText(3)
        epsg = arcpy.GetParameterAsText(4)
        config_file = arcpy.GetParameterAsText(5)
    else:
        gdb_path = r'C:\DIRECTOS\results\UTTL.gdb'
        uttl = r'C:\DIRECTOS\results\UTTL.gdb\UTTL_Basins'
        ah = '1'
        zh_raster = r'C:\DIRECTOS\data\ZH_IDEAM_ENA2014.tif'
        epsg = 3116
        config_file = r'C:\MCAD\development\data\config_criteria.xlsx'

    clear_layers()
    save_mxd(os.path.join(os.path.dirname(gdb_path), 'temp'), 'Factores')
    rareness(gdb_path, uttl, int(ah), zh_raster, epsg, config_file)


if __name__ == '__main__':
    main(env=True)
