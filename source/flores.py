# -*- coding: utf-8 -*-
import arcgisscripting
import csv
import os

import ArcHydroTools
import arcpy
import pandas as pd
from arcpy.sa import *


def add_layer(layer):
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd, "*")[0]
    load_layer = arcpy.mapping.Layer(layer)
    arcpy.mapping.AddLayer(df, load_layer)


def table2csv(input_tbl, csv_filepath):
    fld_list = arcpy.ListFields(input_tbl)
    fld_names = [fld.name for fld in fld_list]
    with open(csv_filepath, 'wb') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(fld_names)
        with arcpy.da.SearchCursor(input_tbl, fld_names) as cursor:
            for row in cursor:
                writer.writerow(row)
        print csv_filepath + " CREATED"
    csv_file.close()


def flores_class(table, workspace):
    arcpy.env.workspace = workspace
    arcpy.env.overwriteOutput = True
    folder = os.path.dirname(workspace)

    df_table = pd.read_csv(table, index_col='Name')
    df_table['SPI'] = df_table['Slope'] * df_table['Areas_Km2'] ** 0.4
    df_table['Flores'] = None

    df_table.ix[df_table[(df_table['Slope'] <= 0.025) & (df_table['SPI'] <= 0.055)].index, 'Flores'] = 'Pool-riffle'
    df_table.ix[df_table[(df_table['Slope'] <= 0.025) & (df_table['SPI'] > 0.055)].index, 'Flores'] = 'Plane-bed'
    df_table.ix[df_table[(df_table['Slope'] > 0.025) & (df_table['SPI'] <= 0.206)].index, 'Flores'] = 'Step-pool'
    df_table.ix[df_table[(df_table['Slope'] > 0.025) & (df_table['SPI'] > 0.206)].index, 'Flores'] = 'Cascade'
    df_table.index = df_table.index.map(unicode)

    df_table.to_csv(os.path.join(folder, r'temp/TableFloresClassification.csv'), index_label='Name')
    arcpy.Delete_management(os.path.join(workspace, 'TableFloresClassificationJoin'))
    arcpy.TableToTable_conversion(os.path.join(folder, r'temp/TableFloresClassification.csv'), workspace, 'TableFloresClassificationJoin')

    expression = 'str(!Name!)'
    code_block = ''
    arcpy.AddField_management(os.path.join(workspace, 'TableFloresClassificationJoin'), 'Code', 'TEXT', '', '', '10', '', 'NULLABLE', 'NON_REQUIRED', '')
    arcpy.CalculateField_management(os.path.join(workspace, 'TableFloresClassificationJoin'), 'Code', expression, 'PYTHON', code_block)

    return os.path.join(workspace, 'TableFloresClassificationJoin')


def slope_calc(batch_point, workspace, drain, epsg, dem, uttl):

    gp = arcgisscripting.create()
    gp.CheckOutExtension("Spatial")
    gp.SetProgressor('default', 'starting vertex extraction...')
    arcpy.env.overwriteOutput = True

    folder = os.path.dirname(workspace)
    UTTL_Basins = uttl.split('/')[-1]

    ArcHydroTools.Construct3DLine(in_line2d_features=drain, in_rawdem_raster=dem, out_line3d_features=os.path.join(workspace, 'Drain3D'))
    ArcHydroTools.Smooth3DLine(in_line3d_features=os.path.join(workspace, 'Drain3D'),
                               out_smoothline3d_features=os.path.join(workspace, 'SmoothDrain3D_UTM'))

    transform_in = gp.Describe(os.path.join(workspace, 'SmoothDrain3D_UTM'))
    ref_in = transform_in.SpatialReference
    arcpy.Project_management(in_dataset=os.path.join(workspace, 'SmoothDrain3D_UTM'),
                             out_dataset=os.path.join(workspace, 'SmoothDrain3D'),
                             out_coor_system=epsg,
                             transform_method="",
                             in_coor_system=ref_in,
                             preserve_shape="NO_PRESERVE_SHAPE", max_deviation="", vertical="NO_VERTICAL")

    arcpy.SplitLineAtPoint_management(os.path.join(workspace, 'SmoothDrain3D'), batch_point, os.path.join(folder, r'Temp/SmoothDrain3DSplit.shp'))

    arcpy.AddField_management(os.path.join(folder, r'Temp/SmoothDrain3DSplit.shp'), 'Slope', 'FLOAT', 6, 4, "", 'Slope', 'NULLABLE', 'REQUIRED')

    arcpy.AddGeometryAttributes_management(os.path.join(folder, r'Temp/SmoothDrain3DSplit.shp'), 'LENGTH')
    arcpy.AddGeometryAttributes_management(os.path.join(folder, r'Temp/SmoothDrain3DSplit.shp'), 'LINE_START_MID_END')
    arcpy.CalculateField_management(os.path.join(folder, r'Temp/SmoothDrain3DSplit.shp'), 'Slope', '( !START_Z! - !END_Z! ) / !LENGTH!', 'PYTHON', '#')

    keep_field = ['FID', 'Shape', 'LENGTH', 'START_Z', 'END_Z', 'Slope']
    fields = [x.name for x in arcpy.ListFields(os.path.join(folder, r'Temp/SmoothDrain3DSplit.shp'))]

    arcpy.DeleteField_management(os.path.join(folder, r'Temp/SmoothDrain3DSplit.shp'), [x for x in fields if x not in keep_field])

    arcpy.MakeFeatureLayer_management(os.path.join(workspace, UTTL_Basins), 'UTTL_Basins')
    arcpy.MakeFeatureLayer_management(os.path.join(folder, r'Temp/SmoothDrain3DSplit.shp'), 'SmoothDrain3DSplit')

    arcpy.Intersect_analysis(in_features='UTTL_Basins #;SmoothDrain3DSplit #',
                             out_feature_class=os.path.join(folder, r'Temp/SmoothDrain3DSplitIntersect.shp'),
                             join_attributes='NO_FID', cluster_tolerance='-1 Unknown',
                             output_type='INPUT')

    arcpy.Dissolve_management(in_features=os.path.join(folder, r'Temp/SmoothDrain3DSplitIntersect.shp'),
                              out_feature_class=os.path.join(folder, r'Temp/SD3DSIDissolve.shp'),
                              dissolve_field='Name',
                              statistics_fields='LENGTH MAX;Shape_area MAX;Slope MAX;START_Z MAX;END_Z MIN',
                              multi_part='MULTI_PART', unsplit_lines='DISSOLVE_LINES')

    arcpy.CopyFeatures_management(os.path.join(folder, r'Temp/SD3DSIDissolve.shp'), os.path.join(workspace, r'Drain_UTTL'))

    table2csv(os.path.join(folder, r'Temp/SD3DSIDissolve.shp'), os.path.join(folder, r'Temp/TableSlope.csv'))
    df_slope = pd.read_csv(os.path.join(folder, r'Temp/TableSlope.csv'), index_col='Name')
    df_slope.drop(['FID', 'Shape', 'MAX_Shape_'], axis=1, inplace=True)
    df_slope.columns = ['Length', 'Slope', 'Start Z', 'End Z']
    df_slope.index.name = 'Name'
    df_slope.to_csv(os.path.join(folder, r'temp/TableSlope.csv'), header=True)

    # Deleting Temporally Files
    arcpy.Delete_management(os.path.join(folder, r'Temp/SD3DSIDissolve.shp'))
    arcpy.Delete_management(os.path.join(folder, r'Temp/SmoothDrain3DSplit.shp'))
    arcpy.Delete_management(os.path.join(folder, r'Temp/SmoothDrain3DSplitIntersect.shp'))
    arcpy.Delete_management(os.path.join(workspace, 'Drain3D'))
    arcpy.Delete_management(os.path.join(workspace, 'SmoothDrain3D_UTM'))

    gp.AddMessage('Slope Algorithm was successful')


def areas_watershed(workspace, fac, uttl):

    gp = arcgisscripting.create()
    gp.CheckOutExtension("Spatial")
    gp.SetProgressor('default', 'Watershed Areas...')
    arcpy.env.overwriteOutput = True

    folder = os.path.dirname(workspace)

    # Calculate a Watershed Areas
    gp.AddMessage('Calculating the watershed areas...')
    # ----------------------------------------------------------------------------------------

    size_pixel = arcpy.Describe(fac).children[0].meanCellHeight
    ZonalStatisticsAsTable(uttl, 'Name', fac, os.path.join(workspace, 'TempTableAreas'), 'DATA', 'MAXIMUM')
    table2csv(os.path.join(workspace, 'TempTableAreas'), os.path.join(folder, r'temp/TableAreas.csv'))
    df_areas = pd.read_csv(os.path.join(folder, r'temp/TableAreas.csv'), index_col='Name')
    df_areas['Areas_Km2'] = (df_areas['MAX'] * size_pixel ** 2) / 1e6
    df_areas.index.name = 'Name'
    df_areas['Areas_Km2'].to_csv(os.path.join(folder, r'temp/TableAreas.csv'), header=True)
    arcpy.Delete_management(os.path.join(workspace, 'TempTableAreas'))

    gp.AddMessage('Watershed Areas Algorithm was successful')


def flores(workspace, uttl):

    gp = arcgisscripting.create()
    gp.CheckOutExtension("Spatial")
    gp.SetProgressor('default', 'Flores Classification ...')
    arcpy.env.workspace = workspace
    arcpy.env.overwriteOutput = True
    arcpy.env.qualifiedFieldNames = False

    folder = os.path.dirname(workspace)

    # Classification
    df_join = pd.concat([pd.read_csv(os.path.join(folder, r'Temp/TableAreas.csv'), index_col='Name'),
                         pd.read_csv(os.path.join(folder, r'Temp/TableSlope.csv'), index_col='Name')], axis=1)

    df_join.index.name = 'Name'
    df_join.to_csv(os.path.join(folder, r'Temp/TableFlores.csv'), header=True)

    path_table_class = flores_class(os.path.join(folder, r'Temp/TableFlores.csv'), workspace=workspace)

    # Join Table to UTTL Segmentation Polygons
    arcpy.MakeFeatureLayer_management(uttl, 'UTTL')
    arcpy.AddJoin_management('UTTL', 'Name', path_table_class, 'Code')
    arcpy.CopyFeatures_management('UTTL', os.path.join(folder, r'temp/UTTL_Flores.shp'))

    field_obj_list = arcpy.ListFields(os.path.join(folder, r'temp/UTTL_Flores.shp'))
    keep_field = ['FID', 'Shape', 'Name', 'Areas_Km2', 'Slope', 'Flores']
    arcpy.DeleteField_management(os.path.join(folder, r'temp/UTTL_Flores.shp'), [x.name for x in field_obj_list if x.name not in keep_field])

    arcpy.CopyFeatures_management(os.path.join(folder, r'temp/UTTL_Flores.shp'), os.path.join(workspace, 'UTTL_Basins'))
    arcpy.Delete_management(os.path.join(folder, r'temp/UTTL_Flores.shp'))
    arcpy.Delete_management(os.path.join(folder, r'temp/TableAreas.csv'))
    arcpy.Delete_management(os.path.join(folder, r'temp/TableFlores.csv'))
    arcpy.Delete_management(os.path.join(folder, r'temp/TableFloresClassification.csv'))
    arcpy.Delete_management(os.path.join(folder, r'temp/TableSlope.csv'))

    gp.AddMessage('Valley Confinement Algorithm was successful')


def main(env):

    if env:
        gdb_path = arcpy.GetParameterAsText(0)
        dem_path = arcpy.GetParameterAsText(1)
        batchpoints_path = arcpy.GetParameterAsText(2)
        drain_network_path = arcpy.GetParameterAsText(3)
        uttl = arcpy.GetParameterAsText(4)
        hydro_zone = arcpy.GetParameterAsText(5)
        fac_path = arcpy.GetParameterAsText(6)
    else:
        gdb_path = r'D:/Work/POTENTIAL_ARCPY/TEST/results/UTTL.gdb'
        dem_path = r'D:/Work/POTENTIAL_ARCPY/TEST/data/dem_test.tif'
        batchpoints_path = r'D:/Work/POTENTIAL_ARCPY/TEST/results/UTTL.gdb/BatchPoints'
        drain_network_path = r'D:/Work/POTENTIAL_ARCPY/TEST/results/UTTL.gdb/drainage_line'
        hydro_zone = 3116
        uttl = r'D:/Work/POTENTIAL_ARCPY/TEST/results/UTTL.gdb/UTTL_Basins'
        fac_path = r'D:/Work/POTENTIAL_ARCPY/TEST/results/UTTL.gdb/fac'

    slope_calc(batch_point=batchpoints_path, workspace=gdb_path, drain=drain_network_path, epsg=hydro_zone, dem=dem_path, uttl=uttl)
    areas_watershed(workspace=gdb_path, fac=fac_path, uttl=uttl)
    flores(workspace=gdb_path, uttl=uttl)


if __name__ == '__main__':
    main(env=True)
