# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# knickpoint python.py
# Created on: 16/10/2012
# Author: Gustavo Lopes Queiroz
# Contact: gustavo.lopes.queiroz@gmail.com
# Special thanks to: Edenilson Nascimento, the code's co-author; and Eduardo
# Salamuni, Ph.D., Professor and research coordinator.
# ---------------------------------------------------------------------------

import os

import arcpy
import ArcHydroTools
import arcgisscripting
import math


def extract_length(line, geom):
    ft = line.GetValue(geom)
    return ft.Length


def points_list(line, geom):
    ft = line.GetValue(geom)
    ls_points = []
    pt = 0
    pt_total = ft.PartCount
    while pt < pt_total:
        part = ft.GetPart(pt)
        vertex = part.Next()
        while vertex:
            if vertex:
                ls_points.append([vertex.X, vertex.Y, vertex.Z])
            vertex = part.Next()
        pt += 1
    return ls_points


def calc_horizontal_distance(x1, y1, x2, y2):
    return math.sqrt(math.pow(math.fabs(x1 - x2), 2) + math.pow(math.fabs(y1 - y2), 2))


def knickpoints_extract(raw_dem, shape_out, drain_network, folder, eq, gdb, epsg):
    arcpy.env.overwriteOutput = True
    gp = arcgisscripting.create()
    gp.CheckOutExtension('spatial')

    # Temporary folder
    temp_folder = os.path.join(folder, 'temp')
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
    if not os.path.join(folder, '{}.gdb'.format(gdb)):
        arcpy.CreateFileGDB_management(folder, '{}.gdb'.format(gdb))

    try:

        gp.SetProgressor('default', 'creating a 3D drain network from based on 2D drainage network and DEM ...')
        drain_2D = drain_network

        ArcHydroTools.Construct3DLine(in_line2d_features=drain_2D, in_rawdem_raster=raw_dem,
                                      out_line3d_features=os.path.join(folder, '{}.gdb'.format(gdb), 'Drain3D'))
        ArcHydroTools.Smooth3DLine(in_line3d_features=os.path.join(folder, '{}.gdb'.format(gdb), 'Drain3D'),
                                   out_smoothline3d_features=os.path.join(folder, '{}.gdb'.format(gdb),
                                                                          'SmoothDrain3D_UTM'))

        transform_in = gp.Describe(os.path.join(folder, '{}.gdb'.format(gdb), 'SmoothDrain3D_UTM'))
        ref_in = transform_in.SpatialReference
        arcpy.Project_management(in_dataset=os.path.join(folder, '{}.gdb'.format(gdb), 'SmoothDrain3D_UTM'),
                                 out_dataset=os.path.join(folder, '{}.gdb'.format(gdb), 'SmoothDrain3D'),
                                 out_coor_system=epsg,
                                 transform_method="",
                                 in_coor_system=ref_in,
                                 preserve_shape="NO_PRESERVE_SHAPE", max_deviation="", vertical="NO_VERTICAL")

        # Identify geometry field
        describe_lyr = gp.Describe(os.path.join(folder, '{}.gdb'.format(gdb), 'SmoothDrain3D'))
        geometry_types = describe_lyr.ShapeFieldName

        gp.SetProgressor('default', 'Processing RDE ...')
        msg_error = 'RDE index measuring failed'

        gp.SetProgressorPosition(0)
        gp.AddMessage('Creating point layer...')

        gp.CreateFeatureclass_management(os.path.join(folder, '{}.gdb'.format(gdb)), shape_out, 'POINT', '', 'DISABLED',
                                         'DISABLED', epsg)
        path_knicks = os.path.join(folder, '{}.gdb'.format(gdb), shape_out)
        gp.AddField_management(path_knicks, 'rde_t', 'DOUBLE')
        gp.AddField_management(path_knicks, 'RDEs', 'DOUBLE')
        gp.AddField_management(path_knicks, 'RDEsRDEt', 'DOUBLE')
        gp.AddField_management(path_knicks, 'OrdemAnom', 'SHORT')

        gp.AddMessage('Calculating RDE indexes...')

        cursor_rde = gp.SearchCursor(os.path.join(folder, '{}.gdb'.format(gdb), 'SmoothDrain3D'))
        line_3d = cursor_rde.Next()

        while line_3d:
            feat_vertex = points_list(line=line_3d, geom=geometry_types)
            # Calculate rde_t ----> rde_t = altimetric distance between the two ends / ln( river length )
            rde_t = (feat_vertex[0][2] - feat_vertex[-1][2]) / max(0.0001, math.log(extract_length(line_3d,
                                                                                                   geometry_types)))
            point_x = -1
            point_y = -1
            comp_segment = 0
            ext_source = 0
            valor_pixel_sum = feat_vertex[0][2]
            v = 0
            print len(feat_vertex), line_3d.getValue("OBJECTID")

            while v < len(feat_vertex):
                if rde_t < 1:
                    break
                if valor_pixel_sum - feat_vertex[v][2] >= int(eq) / 2 and point_x == -1 and point_y == -1:
                    point_x = feat_vertex[v][0]
                    point_y = feat_vertex[v][1]
                if valor_pixel_sum - feat_vertex[v][2] >= int(eq):
                    # Measure RDEs
                    RDEs = ((valor_pixel_sum - feat_vertex[v][2]) / comp_segment) * ext_source
                    # Check if there is an anomaly
                    if RDEs / max(0.0001, rde_t) >= 2:
                        # Create anomaly point
                        cursor_points = gp.InsertCursor(path_knicks)
                        line_point = cursor_points.NewRow()
                        point = gp.CreateObject('Point')
                        point.X = point_x
                        point.Y = point_y
                        line_point.Shape = point
                        line_point.RDEs = RDEs
                        line_point.RDEt = rde_t
                        line_point.RDEsRDEt = RDEs / max(0.0001, rde_t)
                        if RDEs / max(0.0001, rde_t) >= 2:
                            if RDEs / max(0.0001, rde_t) >= 10:
                                line_point.OrdemAnom = 1
                            else:
                                line_point.OrdemAnom = 2
                        cursor_points.InsertRow(line_point)

                        del cursor_points, line_point
                    valor_pixel_sum = feat_vertex[v][2]
                    comp_segment = 0
                    point_x = -1
                    point_y = -1
                v += 1
                if v == len(feat_vertex) - 1:
                    break
                else:
                    comp_segment += calc_horizontal_distance(feat_vertex[v][0], feat_vertex[v][1],
                                                             feat_vertex[v - 1][0], feat_vertex[v - 1][1])
                    ext_source += calc_horizontal_distance(feat_vertex[v][0], feat_vertex[v][1], feat_vertex[v - 1][0],
                                                           feat_vertex[v - 1][1])
            line_3d = cursor_rde.Next()

        arcpy.AddXY_management(in_features=os.path.join(folder, '{}.gdb'.format(gdb), shape_out))
        gp.AddMessage('Knickpoint Finder was successful')

    except Exception, e:
        gp.AddError('Error! ' + msg_error)
        gp.AddError(e)


def knickpoints_filter(folder, gdb, knick):
    arcpy.env.overwriteOutput = True
    gp = arcgisscripting.create()
    gp.CheckOutExtension('spatial')

    # Temporary folder
    temp_folder = os.path.join(folder, 'temp')
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)
    if not os.path.join(folder, '{}.gdb'.format(gdb)):
        arcpy.CreateFileGDB_management(folder, '{}.gdb'.format(gdb))

    arcpy.MakeFeatureLayer_management(os.path.join(folder, gdb, knick), 'knick')
    arcpy.SelectLayerByAttribute_management('knick', 'NEW_SELECTION', '"OrdemAnom" < 2')
    arcpy.CopyFeatures_management('knick', os.path.join(folder, gdb, '{}_filter'.format(knick)))


def main(env):
    gp = arcgisscripting.create()
    gp.CheckOutExtension('spatial')
    if env:
        dem_path = gp.GetParameterAsText(0)
        equidistant = gp.GetParameter(1)
        knick_name = gp.GetParameterAsText(2)
        drainage_line_path = gp.GetParameterAsText(3)
        folder = gp.GetParameterAsText(4)
        gdb_name = gp.GetParameterAsText(5)
        epsg = gp.GetParameterAsText(6)
    else:
        dem_path = r'E:\AH_02\data\strm_MC.tif'
        equidistant = 200
        knick_name = r'knickpoints'
        drainage_line_path = r'E:\AH_02\UTTL.gdb\drainage_line'
        folder = r'E:\AH_02'
        gdb_name = r'UTTL'
        epsg = 3116

    knickpoints_extract(raw_dem=dem_path,
                        shape_out=knick_name,
                        drain_network=drainage_line_path,
                        folder=folder,
                        eq=equidistant,
                        gdb=gdb_name, epsg=epsg)

    knickpoints_filter(folder=folder, gdb=gdb_name, knick=knick_name)


if __name__ == '__main__':
    main(env=True)
