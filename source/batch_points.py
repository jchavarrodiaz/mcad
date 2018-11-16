# -*- coding: utf-8 -*-

import os
import numpy
import arcpy
import arcgisscripting


def merge_points(knickpoints, hydropoints, folder_out, gdb, zone):
    arcpy.env.overwriteOutput = True
    gp = arcgisscripting.create()
    gp.CheckOutExtension('spatial')

    # Temporary folder
    temp_folder = os.path.join(folder_out, 'temp')
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
    if not gdb:
        arcpy.CreateFileGDB_management(gdb)

    arcpy.Merge_management([knickpoints, hydropoints], os.path.join(temp_folder, 'merge_points.shp'))
    arcpy.MakeFeatureLayer_management(os.path.join(temp_folder, 'merge_points.shp'), 'lyr')
    arcpy.SelectLayerByAttribute_management('lyr', 'NEW_SELECTION', '"OrdemAnom" < 2')
    arcpy.CopyFeatures_management('lyr', os.path.join(temp_folder, 'pre_batchpoints.shp'))
    
    field_obj_list = arcpy.ListFields(os.path.join(temp_folder, 'pre_batchpoints.shp'))

    arcpy.CopyFeatures_management(os.path.join(temp_folder, 'pre_batchpoints.shp'), os.path.join(gdb, 'BatchPoints'))
    arcpy.DeleteField_management(os.path.join(gdb, 'BatchPoints'), [x.name for x in field_obj_list][2:])

    arcpy.MakeFeatureLayer_management(os.path.join(gdb, 'BatchPoints'), 'lyr_temp')
    total_points = int(arcpy.GetCount_management('lyr_temp').getOutput(0))

    arcpy.AddField_management(os.path.join(gdb, 'BatchPoints'), 'Name', 'TEXT', 9, "", "", 'Name', 'NULLABLE', 'REQUIRED')
    arcpy.AddField_management(os.path.join(gdb, 'BatchPoints'), 'Descript', 'TEXT', 9, "", "", 'Descript', 'NULLABLE', 'REQUIRED')
    arcpy.AddField_management(os.path.join(gdb, 'BatchPoints'), 'BatchDone', 'SHORT', 9, "", "", 'BatchDone', 'NULLABLE', 'REQUIRED')
    arcpy.AddField_management(os.path.join(gdb, 'BatchPoints'), 'SnapOn', 'SHORT', 9, "", "", 'SnapOn', 'NULLABLE', 'REQUIRED')
    arcpy.AddField_management(os.path.join(gdb, 'BatchPoints'), 'SrcType', 'TEXT', 9, "", "", 'SrcType', 'NULLABLE', 'REQUIRED')

    start_code = {1: 1000000,
                  2: 2000000,
                  3: 3000000,
                  4: 4000000,
                  5: 5000000}

    nstart = start_code[zone]

    arcpy.CalculateField_management(in_table=os.path.join(gdb, 'BatchPoints'), field="Name", expression="!OBJECTID! + {}".format(nstart), expression_type="PYTHON", code_block="")
    # arcpy.CalculateField_management(os.path.join(gdb, 'BatchPoints'), 'Name', expression, 'PYTHON', code_block)
    arcpy.CalculateField_management(os.path.join(gdb, 'BatchPoints'), 'Descript', "\"subwateshed\"", 'PYTHON')
    arcpy.CalculateField_management(os.path.join(gdb, 'BatchPoints'), 'BatchDone', 0, 'PYTHON')
    arcpy.CalculateField_management(os.path.join(gdb, 'BatchPoints'), 'SnapOn', 1, 'PYTHON')
    arcpy.CalculateField_management(os.path.join(gdb, 'BatchPoints'), 'SrcType', "\"Outlet\"", 'PYTHON')


def main(env):
    gp = arcgisscripting.create()
    gp.CheckOutExtension('spatial')

    if env:
        gdb_path = arcpy.GetParameterAsText(0)
        topog_points = arcpy.GetParameterAsText(1)
        hydro_points = arcpy.GetParameterAsText(2)
        hydro_zone = arcpy.GetParameter(3)
    else:
        gdb_path = r'E:\AH_02\UTTL.gdb'
        topog_points = r'E:\AH_02\UTTL.gdb\knickpoints'
        hydro_points = r'E:\AH_02\UTTL.gdb\hydro_points'
        hydro_zone = 2

    folder = os.path.dirname(gdb_path)
    merge_points(knickpoints=topog_points, hydropoints=hydro_points, folder_out=folder, gdb=gdb_path, zone=hydro_zone)


if __name__ == '__main__':
    main(env=True)
