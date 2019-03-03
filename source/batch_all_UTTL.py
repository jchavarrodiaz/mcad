# -*- coding: utf-8 -*-
import arcgisscripting
import os

import arcpy

from aconditioning_dem import dem_conditioning
from batch_points import merge_points
from hydro_points import extract_hydro_points
from knickpoints import knickpoints_extract, knickpoints_filter
from segmentation import uttl_maker


def save_mxd(folder, name):
    mapdoc = arcpy.mapping.MapDocument('CURRENT')
    mapdoc.saveACopy(os.path.join(folder, '{}.mxd'.format(name)))


def clear_layers():
    mxd = arcpy.mapping.MapDocument('CURRENT')
    for df in arcpy.mapping.ListDataFrames(mxd):
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            arcpy.mapping.RemoveLayer(df, lyr)
    del mxd


def main(env):
    arcpy.CheckOutExtension('Spatial')
    gp = arcgisscripting.create()

    if env:
        # from ArcMap
        # User input data
        dem_path = arcpy.GetParameterAsText(0)
        folder_out_path = arcpy.GetParameterAsText(1)
        gdb_name = arcpy.GetParameterAsText(2)
        drain_burning = arcpy.GetParameterAsText(3)
        threshold = arcpy.GetParameterAsText(4)
        show_layers = arcpy.GetParameterAsText(5)
        epsg = arcpy.GetParameterAsText(6)
        make_fill = arcpy.GetParameterAsText(7)

        equidistant = gp.GetParameter(8)
        knick_name = gp.GetParameterAsText(9)

        hydro_zone = gp.GetParameter(10)
        # mxd_project = gp.GetParameter(11)

    else:
        # from console
        dem_path = r'C:\DIRECTOS\data\HydroDEM_Directos_3116.tif'
        folder_out_path = r'C:\DIRECTOS\results'
        gdb_name = 'UTTL'
        drain_burning = ''
        threshold = 324  # TODO: estimate the threshold from the scale and resolution of dem
        show_layers = False
        epsg = 3116
        make_fill = True

        equidistant = 200
        knick_name = 'knickpoints'

        hydro_zone = 12
        # mxd_project = 'Untitled'

    temp = os.path.join(folder_out_path, 'temp')
    if not os.path.isdir(temp):
        os.mkdir(temp)
    save_mxd(folder=temp, name='Untitled')
    arcpy.env.workspace = folder_out_path
    arcpy.env.overwriteOutput = True
    if not os.path.exists(os.path.join(folder_out_path, '{}.gdb'.format(gdb_name))):
        arcpy.CreateFileGDB_management(folder_out_path, '{}.gdb'.format(gdb_name))

    gdb_path = os.path.join(folder_out_path, '{}.gdb'.format(gdb_name))
    dem_conditioning(dem=dem_path, folder=folder_out_path, gdb=gdb_name, threshold=threshold, show=show_layers, epsg=epsg, fill=make_fill, drain_network=drain_burning)

    drain_network = os.path.join(folder_out_path, '{}.gdb'.format(gdb_name), 'drainage_line')
    extract_hydro_points(drain=drain_network, show=show_layers, folder=folder_out_path, gdb=gdb_name)
    knickpoints_extract(raw_dem=dem_path, shape_out=knick_name, drain_network=drain_network, folder=folder_out_path, eq=equidistant, gdb=gdb_name, epsg=epsg)
    knickpoints_filter(folder=folder_out_path, gdb=gdb_name, knick=knick_name)
    topog_points = os.path.join(folder_out_path, '{}.gdb'.format(gdb_name), 'knickpoints_filter')
    hydro_points = os.path.join(folder_out_path, '{}.gdb'.format(gdb_name), 'hydro_points')
    merge_points(knickpoints=topog_points, hydropoints=hydro_points, folder_out=folder_out_path, gdb=gdb_path, zone=hydro_zone)

    batchpoints_path = os.path.join(gdb_path, 'BatchPoints')
    fdr = os.path.join(gdb_path, 'fdr')
    str_stream = os.path.join(gdb_path, 'Str')
    uttl_maker(flow_grid=fdr, stream_grid=str_stream, batch_point=batchpoints_path, basins='UTTL_Basins', workspace=gdb_path)
    clear_layers()


if __name__ == '__main__':
    main(env=True)
