# -*- coding: utf-8 -*-
import os

import arcpy
import pandas as pd


def parks_reps(gdb, uttl, parks, epsg, config):

    results_folder = os.path.dirname(gdb)
    temp_folder = os.path.join(results_folder, 'temp')

    arcpy.env.workspace = results_folder
    arcpy.env.overwriteOutput = True

    xls_file = pd.ExcelFile(config)
    df_crieria = xls_file.parse('Representatividad')

    # Replace a layer/table view name with a path to a dataset (which can be a layer file) or create the layer/table view within the script
    # The following inputs are layers or table views: "RUNAP"
    arcpy.Project_management(in_dataset=parks, out_dataset=os.path.join(temp_folder, os.path.split(parks)[-1]), out_coor_system=epsg)

    # Continuar con:
    # RUNAP to raster
    # addAtribute ZOnal Stats COUNT CELLS


def main(env):
    arcpy.CheckOutExtension('Spatial')

    if env:
        uttl = arcpy.GetParameterAsText(0)
        parks_path = arcpy.GetParameterAsText(1)
        epsg = arcpy.GetParameterAsText(2)
        config_file = arcpy.GetParameterAsText(3)
    else:
        uttl = r'C:\DIRECTOS\results\UTTL.gdb\UTTL_Basins'
        parks_path = r'C:\DIRECTOS\data\RUNAP.shp'
        epsg = 3116
        config_file = r'C:\MCAD\development\data\config_criteria.xlsx'

    gdb_path = os.path.dirname(uttl)
    parks_reps(gdb_path, uttl, parks_path, epsg, config_file)


if __name__ == '__main__':
    main(env=False)
