# -*- coding: utf-8 -*-
import os

import arcpy
import pandas as pd

from add_attribute import zonal_stats


def rareness(gdb, uttl, ah, zh, epsg):

    ah_areas = {1: 103255800000,
                2: 272163400000,
                3: 346227100000,
                4: 341818300000,
                5: 77981870000}

    results_folder = os.path.dirname(gdb)
    temp_folder = os.path.join(results_folder, 'temp')
    zh_path = os.path.join(temp_folder, 'zh_temp.tif')

    arcpy.ProjectRaster_management(zh, zh_path, epsg, 'NEAREST')

    zonal_stats(uttl, zh_path, 'Area_ZH', 'MAJORITY')
    arcpy.TableToTable_conversion(uttl, temp_folder, 'uttl.csv')

    df_uttl = pd.read_csv(os.path.join(temp_folder, 'UTTL_table_rare.csv'), delimiter=',', index_col='Name')
    df_type = pd.DataFrame(df_uttl.groupby(['TIPOLOGIA']).sum()['Shape_Area']).reset_index()
    df_type.columns = ['TIPOLOGIA', 'Area_Tipo']

    df_uttl = df_uttl.merge(right=df_type, on='TIPOLOGIA', how='left')
    df_uttl['Area_AH'] = ah_areas[ah]

    df_uttl['rare_AH']




    return


def main(env):
    arcpy.CheckOutExtension('Spatial')

    if env:
        gdb_path = arcpy.GetParameterAsText(0)
        uttl = arcpy.GetParameterAsText(1)
        ah = arcpy.GetParameterValue(2)
        zh_raster = arcpy.GetParameterValue(3)
        epsg = arcpy.GetParameterAsText(4)
    else:
        gdb_path = r'C:\DIRECTOS\results\UTTL.gdb'
        uttl = r'C:\DIRECTOS\results\UTTL.gdb\UTTL_Basins'
        ah = 1
        zh_raster = r'C:\DIRECTOS\data\ZH_IDEAM_ENA2014.tif'
        epsg = 3116

    rareness(gdb_path, uttl, ah, zh_raster, epsg)


if __name__ == '__main__':
    main(env=True)
