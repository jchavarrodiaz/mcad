# -*- coding: utf-8 -*-
import os

import arcpy
import ArcHydroTools
import arcgisscripting


def uttl_maker(flow_grid, stream_grid, batch_point, basins, workspace):

    gp = arcgisscripting.create()
    folder = os.path.dirname(workspace)
    arcpy.env.workspace = folder
    arcpy.env.overwriteOutput = True
    arcpy.CheckOutExtension('spatial')

    arcpy.CopyFeatures_management(batch_point, os.path.join(workspace, 'DelBatchPoints'))

    gp.AddMessage('Loading Layers!...')

    # TODO: Load Raster Layers for fdr and str rasters

    ArcHydroTools.BatchSubwatershedDelineation(os.path.join(workspace, 'DelBatchPoints'),
                                               os.path.basename(flow_grid), os.path.basename(stream_grid),
                                               basins, 'SubWatershedPoints')

    arcpy.CopyFeatures_management(basins, os.path.join(folder, 'temp/{}.shp'.format(basins)))
    arcpy.Delete_management(os.path.join(workspace, 'Layers'))
    arcpy.Delete_management(os.path.join(workspace, 'APUNIQUEID'))
    arcpy.Delete_management(os.path.join(workspace, 'LAYERKEYTABLE'))
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
    '''
    This tool only can run in the ArcMap-ArcGis
    Check if the data is storage in disk C://
    Load the Fdr and Str rasters in Table of Content
    Before run, save the mxd project
    '''
    main(env=True)
