# -*- coding: utf-8 -*-

import os
import arcpy
import arcgisscripting


def extract_hydro_points(drain, show, folder, gdb):
    gp = arcgisscripting.create()
    gp.CheckOutExtension("Spatial")
    gp.SetProgressor('default', 'starting vertex extraction...')
    arcpy.env.overwriteOutput = True
    arcpy.env.addOutputsToMap = show

    if not os.path.exists(os.path.join(folder, '{}.gdb'.format(gdb))):
        arcpy.CreateFileGDB_management(out_folder_path=folder, out_name='{}.gdb'.format(gdb))

    gp.AddMessage('Processing Extract Vertex ...')
    arcpy.Intersect_analysis(in_features='{} #'.format(drain),
                             out_feature_class=os.path.join(folder, 'temp', 'hydro_multi_points.shp'),
                             join_attributes='ALL', cluster_tolerance='-1 Unknown',
                             output_type='POINT')

    arcpy.AddXY_management(in_features=os.path.join(folder, 'temp', 'hydro_multi_points.shp'))
    arcpy.DeleteIdentical_management(in_dataset=os.path.join(folder, 'temp', 'hydro_multi_points.shp'),
                                     fields="POINT_X;POINT_Y", xy_tolerance="", z_tolerance="0")
    arcpy.MultipartToSinglepart_management(in_features=os.path.join(folder, 'temp', 'hydro_multi_points.shp'),
                                           out_feature_class=os.path.join(folder, '{}.gdb'.format(gdb), 'hydro_points'))

    gp.AddMessage('Finish')


def extract_drainage_points(drain_points, epsg, gdb, folder, show):
    gp = arcgisscripting.create()
    gp.CheckOutExtension("Spatial")
    gp.SetProgressor('default', 'starting vertex extraction...')
    arcpy.env.overwriteOutput = True
    arcpy.env.addOutputsToMap = show

    if not os.path.exists(os.path.join(folder, '{}.gdb'.format(gdb))):
        arcpy.CreateFileGDB_management(out_folder_path=folder, out_name='{}.gdb'.format(gdb))

    gp.AddMessage('Processing Extract Vertex ...')

    spatial_ref = arcpy.Describe(drain_points).spatialReference

    arcpy.Project_management(in_dataset=drain_points, out_dataset=os.path.join(folder, '{}.gdb'.format(gdb),
                                                                               'hydro_points'),
                             out_coor_system=epsg,
                             transform_method="",
                             in_coor_system=spatial_ref,
                             preserve_shape="NO_PRESERVE_SHAPE", max_deviation="", vertical="NO_VERTICAL")

    gp.AddMessage('Finish')


def main(env):
    gp = arcgisscripting.create()
    if env:
        drain_network = arcpy.GetParameterAsText(0)
        drain_points = arcpy.GetParameterAsText(1)
        show_layers = arcpy.GetParameterAsText(2)
        folder_out_path = arcpy.GetParameterAsText(3)
        gdb_name = arcpy.GetParameterAsText(4)
        hydro_zone = arcpy.GetParameterAsText(5)
    else:
        drain_network = r'C:/temp/results/UTTL.gdb/drainage_line'
        drain_points = r'C:/temp/results/UTTL.gdb/drainage_point'
        show_layers = False
        folder_out_path = os.path.join('C:/temp/results')
        gdb_name = 'UTTL'
        hydro_zone = 3116

    if drain_network != '':
        extract_hydro_points(drain=drain_network,
                             show=show_layers,
                             folder=folder_out_path,
                             gdb=gdb_name)
    elif drain_points != '':
        extract_drainage_points(drain_points=drain_points,
                                epsg=hydro_zone,
                                gdb=gdb_name,
                                folder=folder_out_path,
                                show=show_layers)
    else:
        gp.SetProgressor('default',
                         'You must specify at least one of both: a drain network or a drainage points vertex')


if __name__ == '__main__':
    main(env=True)
