# -*- coding: utf-8 -*-

import arcgisscripting
import os

import ArcHydroTools
import arcpy


def add_layer(layer):
    mxd = arcpy.mapping.MapDocument('CURRENT')
    df = arcpy.mapping.ListDataFrames(mxd, '*')[0]
    add = arcpy.mapping.Layer(layer)
    arcpy.mapping.AddLayer(df, add)


def dem_conditioning(dem, folder, gdb, threshold, show, epsg, fill, drain_network=None):

    gp = arcgisscripting.create()

    arcpy.env.addOutputsToMap = show
    gdb_path = os.path.join(folder, '{}.gdb'.format(gdb))

    # temporary work folder at the end of the tool the files are deleted
    if not os.path.exists(os.path.join(folder, 'temp')):
        os.makedirs(os.path.join(folder, 'temp'))

    gp.SetProgressor('step', 'starting pre-processing digital terrain model...')
    gp.SetProgressorPosition(0)

    dem_work_path = dem

    if fill:
        gp.SetProgressorPosition(10)
        gp.AddMessage('Terrain Pre-processing ... Fill')
        ArcHydroTools.FillSinks(dem_work_path, os.path.join(gdb_path, r'fill'))
    else:
        arcpy.CopyRaster_management(dem_work_path, os.path.join(gdb_path, r'fill'))

    if drain_network:
        gp.AddMessage('DEM Reconditioning ...')

        # TODO: It is necessary to verify that the drainage network is in the same reference system of the DEM
        # TODO: The drainage network must be a feature line NOT polygons. Another option is to burn streams by
        # rasterizing the hydrography and doing maps algebra

        deep_burning = arcpy.GetRasterProperties_management(in_raster=dem_work_path, property_type='CELLSIZEX')

        gp.SetProgressorPosition(13)
        gp.AddMessage('Processing AgreeDem ...')
        ArcHydroTools.DEMReconditioning(Input_Raw_DEM_Raster=os.path.join(gdb_path, r'fill'),
                                        Input_Stream_Raster_or_Feature_Class=drain_network,
                                        Number_of_Cells_for_Stream_Buffer=1,
                                        Smooth_Drop_in_Z_Units=deep_burning,
                                        Sharp_Drop_in_Z_Units=deep_burning * 10.,
                                        Output_AGREE_DEM_Raster=os.path.join(gdb_path, r'AgreeDEM'))

        gp.SetProgressorPosition(16)
        gp.AddMessage('Processing hydroDEM ...')
        ArcHydroTools.FillSinks(Input_DEM_Raster=os.path.join(gdb_path, r'AgreeDEM'),
                                Output_Hydro_DEM_Raster=os.path.join(gdb_path, r'fill'))

    gp.SetProgressorPosition(20)
    gp.AddMessage('Processing Flow Direction ...')
    ArcHydroTools.FlowDirection(Input_Hydro_DEM_Raster=os.path.join(gdb_path, r'fill'),
                                Output_Flow_Direction_Raster=os.path.join(gdb_path, r'fdr'))

    gp.SetProgressorPosition(30)
    gp.AddMessage('Processing Flow Accumulation...')
    ArcHydroTools.FlowAccumulation(os.path.join(gdb_path, r'fdr'), os.path.join(gdb_path, r'fac'))

    gp.SetProgressorPosition(40)
    gp.AddMessage('Processing Stream Raster ...')
    ArcHydroTools.StreamDefinition(os.path.join(gdb_path, r'fac'), threshold, os.path.join(gdb_path, r'Str'))

    gp.SetProgressorPosition(50)
    gp.AddMessage('Processing Stream Segmentation ...')
    ArcHydroTools.StreamSegmentation(os.path.join(gdb_path, r'str'), os.path.join(gdb_path, 'fdr'),
                                     os.path.join(gdb_path, 'strlnk'))

    gp.SetProgressorPosition(60)
    gp.AddMessage('Processing Catchment Grid ...')
    ArcHydroTools.CatchmentGridDelineation(os.path.join(gdb_path, r'fdr'), os.path.join(gdb_path, 'strlnk'),
                                           os.path.join(gdb_path, 'cat'))

    gp.SetProgressorPosition(70)
    gp.AddMessage('Processing Catchment Polygon ...')
    ArcHydroTools.CatchmentPolyProcessing(os.path.join(gdb_path, r'cat'), os.path.join(gdb_path, 'catchment'))

    gp.SetProgressorPosition(80)
    gp.AddMessage('Processing Drainage Line ...')
    ArcHydroTools.DrainageLineProcessing(os.path.join(gdb_path, r'strlnk'), os.path.join(gdb_path, 'fdr'),
                                         os.path.join(gdb_path, 'drainage_line'))

    # Removing all geometries whose length is less than the pixel size
    arcpy.MakeFeatureLayer_management(os.path.join(gdb_path, 'drainage_line'), 'drain')
    arcpy.SelectLayerByAttribute_management('drain', "NEW_SELECTION", ' "Shape_Length" > 0 ')
    arcpy.CopyFeatures_management("drain", os.path.join(folder, 'temp', 'drain_line.shp'))
    arcpy.DeleteFeatures_management(os.path.join(gdb_path, 'drainage_line'))
    # arcpy.Delete_management(os.path.join(gdb_path, 'drainage_line'), '')
    arcpy.CopyFeatures_management(os.path.join(folder, 'temp', 'drain_line.shp'),
                                  os.path.join(gdb_path, 'drainage_line'))

    gp.SetProgressorPosition(90)
    gp.AddMessage('Processing Adjoint Catchment ...')
    ArcHydroTools.AdjointCatchment(os.path.join(gdb_path, r'drainage_line'), os.path.join(gdb_path, 'catchment'),
                                   os.path.join(gdb_path, 'adjoint_catchment'))

    gp.SetProgressorPosition(95)
    gp.AddMessage('Processing Drainage Point ...')
    ArcHydroTools.DrainagePointProcessing(os.path.join(gdb_path, r'fac'), os.path.join(gdb_path, 'cat'),
                                          os.path.join(gdb_path, 'catchment'), os.path.join(gdb_path, 'drainage_point'))

    gp.SetProgressorPosition(100)
    gp.AddMessage('Finish')


def main(env):

    arcpy.CheckOutExtension('Spatial')

    if env:
        # from ArcMap
        # User input data
        dem_path = arcpy.GetParameterAsText(0)
        folder_out_path = arcpy.GetParameterAsText(1)
        gdb_name = arcpy.GetParameterAsText(2)
        drain_burning = arcpy.GetParameterAsText(3)
        threshold = arcpy.GetParameterAsText(4)
        show_layers = arcpy.GetParameterAsText(5)
        hydro_zone = arcpy.GetParameterAsText(6)
        make_fill = arcpy.GetParameterAsText(7)
    else:
        # from console
        dem_path = r'D:\AH_03\data\HydroDEM_Orinoco_plus_500_3117.tif'
        folder_out_path = r'D:\AH_03\results'
        gdb_name = 'UTTL'
        drain_burning = ''
        threshold = 324  # TODO: estimate the threshold from the scale and resolution of dem
        show_layers = False
        hydro_zone = 3117
        make_fill = False

    arcpy.env.workspace = folder_out_path
    arcpy.env.overwriteOutput = True
    if not os.path.exists(os.path.join(folder_out_path, '{}.gdb'.format(gdb_name))):
        arcpy.CreateFileGDB_management(folder_out_path, '{}.gdb'.format(gdb_name))

    dem_conditioning(dem=dem_path, folder=folder_out_path, gdb=gdb_name, threshold=threshold, show=show_layers,
                     epsg=hydro_zone, fill=make_fill, drain_network=drain_burning)


if __name__ == '__main__':
    main(env=False)
