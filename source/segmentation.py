# -*- coding: utf-8 -*-
import os

import arcpy
import ArcHydroTools
import arcgisscripting

from showing_things import show_things


def uttl_maker(flow_grid, stream_grid, batch_point, basins, workspace):

    gp = arcgisscripting.create()
    folder = os.path.dirname(workspace)

    arcpy.env.workspace = folder
    arcpy.env.overwriteOutput = True
    arcpy.CheckOutExtension('spatial')

    arcpy.CopyFeatures_management(batch_point, os.path.join(workspace, 'DelBatchPoints'))

    gp.AddMessage('Loading Layers!...')

    # Loading Flow Direction and Stream Raster
    show_things(thing_path=flow_grid, lyr_name='Fdr', folder=folder)
    show_things(thing_path=stream_grid, lyr_name='Str', folder=folder)

    ArcHydroTools.SetTargetLocations("HydroConfig", "Layers", folder, '{}/untitled.gdb'.format(folder))
    ArcHydroTools.BatchSubwatershedDelineation(os.path.join(workspace, 'DelBatchPoints'), 'Fdr', 'Str', basins, 'Subwatershed_Points')

    arcpy.CopyFeatures_management(basins, os.path.join(folder, 'temp/{}.shp'.format(basins)))
    arcpy.CopyFeatures_management(os.path.join(folder, 'temp/{}.shp'.format(basins)), os.path.join(workspace, basins))
    arcpy.Delete_management(os.path.join(folder, 'temp/{}.shp'.format(basins)))

    gp.AddMessage('UTTL is Done!...')


def main(env):

    if env:
        gdb_path = arcpy.GetParameterAsText(0)
        fdr_path = arcpy.GetParameterAsText(1)
        stream_path = arcpy.GetParameterAsText(2)
        batchpoints_path = arcpy.GetParameterAsText(3)
        basins_name = arcpy.GetParameterAsText(4)
    else:
        gdb_path = r'D:\AH_03\results\UTTL.gdb'
        fdr_path = r'D:\AH_03\results\UTTL.gdb\fdr'
        stream_path = r'D:\AH_03\results\UTTL.gdb\Str'
        batchpoints_path = r'D:\AH_03\results\UTTL.gdb\BatchPoints'
        basins_name = 'UTTL_Basins'

    uttl_maker(flow_grid=fdr_path,
               stream_grid=stream_path,
               batch_point=batchpoints_path,
               basins=basins_name,
               workspace=gdb_path)


if __name__ == '__main__':
    main(env=True)
