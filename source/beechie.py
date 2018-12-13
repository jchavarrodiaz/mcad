import arcgisscripting
import os
import subprocess

import arcpy
from arcpy import env
from arcpy.sa import *

import pandas as pd
import numpy as np


def add_layer(layer):
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd, "*")[0]
    load_layer = arcpy.mapping.Layer(layer)
    arcpy.mapping.AddLayer(df, load_layer)


def import_data_to_saga(mde_loc, temp):
    gp = arcgisscripting.create()
    gp.AddMessage('Copying data to SAGA ...')
    mde_out = '-GRIDS={}/saga_mde'.format(temp)
    mde_in = '-FILES={}'.format(mde_loc)
    trf = '-TRANSFORM 1'
    command = ['saga_cmd', 'io_gdal', '0', mde_out, mde_in, trf]
    gp.AddMessage(command)
    p1 = subprocess.Popen(command, stdout=subprocess.PIPE)
    output = p1.communicate()[0]
    gp.AddMessage(output)


def run_mrvbf(temp, t_slope=16., tv=0.4, tr=0.35, p_slope=4.0, p=3.0):
    '''
    Calculation of the 'multiresolution index of valley bottom flatness' (MRVBF)
    and the complementary 'multiresolution index of the ridge top flatness' (MRRTF).
    References:
    Gallant, J.C., Dowling, T.I. (2003): 'A multiresolution index of valley bottom
    flatness for mapping depositional areas', Water Resources Research, 39/12:1347-1359

    :param temp: temporal folder results
    :param t_slope: Initial Threshold for Slope default 16.0
    :param tv: Threshold for Elevation Percentile (Lowness) default 0.4
    :param tr: Threshold for Elevation Percentile (Upness) default 0.35
    :param p_slope: Shape Parameter for Slope default 4.0
    :param p: Shape Parameter for Elevation Percentile default 3.0
    :return: MRVBF and MRRTF Grid (output)
    '''
    gp = arcgisscripting.create()
    mde_par = '-DEM={}/saga_mde.sgrd'.format(temp)
    mrvbf_out = '-MRVBF={}/mrvbf'.format(temp)
    mrrtf_out = '-MRRTF={}/mrrtf'.format(temp)
    t_slope = '-T_SLOPE={}'.format(str(t_slope))
    t_pctl_v = '-T_PCTL_V={}'.format(str(tv))
    t_pctl_r = '-T_PCTL_R={}'.format(str(tr))
    p_slope = '-P_SLOPE={}'.format(str(p_slope))
    p_pctl = '-P_PCTL={}'.format(str(p))
    update = '-UPDATE=1'
    classify = '-CLASSIFY=1'
    max_res = '-MAX_RES=100'
    command = ['saga_cmd', 'ta_morphometry', '8', mde_par, mrvbf_out, mrrtf_out,
               t_slope, t_pctl_v, t_pctl_r, p_slope, p_pctl, update, classify,
               max_res]
    gp.AddMessage(command)
    p1 = subprocess.Popen(command, stdout=subprocess.PIPE)
    output = p1.communicate()[0]
    gp.AddMessage(output)


def export_data_from_saga(temp, out_grid, gdb, show):
    gp = arcgisscripting.create()
    mde_out = '-GRIDS:{}/{}.sgrd'.format(temp, out_grid)
    out_tif = '-FILE:{}/{}.tif'.format(temp, out_grid)
    command = ['saga_cmd', 'io_gdal', '2', mde_out, out_tif]
    gp.AddMessage(command)
    p1 = subprocess.Popen(command, stdout=subprocess.PIPE)
    output = p1.communicate()[0]
    gp.AddMessage(output)

    arcpy.env.workspace = gdb
    arcpy.env.overwriteOutput = True
    arcpy.CopyRaster_management(in_raster='{}/{}.tif'.format(temp, out_grid),
                                out_rasterdataset='{}/{}'.format(gdb, out_grid))

    arcpy.MakeRasterLayer_management(in_raster=r'{}/{}'.format(gdb, out_grid), out_rasterlayer='mrvbf_index')
    arcpy.gp.RasterCalculator_sa('Con("mrvbf_index"  != 0, 1, SetNull("mrvbf_index","mrvbf_index","VALUE = 0"))',
                                 r'{}/{}_reclass'.format(gdb, out_grid))


def fn_beechie(raster, drain_shape, uttl_basins, fac, workspace, CTr, qTr):
    """
    Esta funcion estima el grado de confinamiento
    correspondiente a un tramo de corriente a
    partir de los resultados del modulo MRVBF
    de Saga y el ancho trenzado de acuerdo con
    el modelo de regresion en funcion del area.
    :param raster: Es el raster reclasificado de MRVBF
    :param drain_shape: Es el vectorial de los tramos de corriente de las UTTL
    :param uttl_basins: Es el vectorial de las UTTL
    :return: Agrega al shape de UTTL un atributo llamado w_valley, area_MRVBF, WB, DoC
    """
    gp = arcgisscripting.create()
    gp.CheckOutExtension("Spatial")
    arcpy.env.workspace = '{}'.format(os.path.dirname(os.path.abspath(workspace)))
    arcpy.env.overwriteOutput = True
    arcpy.env.qualifiedFieldNames = False
    temp_folder = '{}/temp'.format(os.path.dirname(workspace))

    gp.AddMessage('Wvalley width ... ')

    arcpy.gp.RasterCalculator_sa('Con(IsNull("{}"),0,"{}")'.format(raster, raster),
                                 '{}/temp_mrvbf.tif'.format(temp_folder))
    arcpy.gp.ZonalStatisticsAsTable_sa(uttl_basins, "Name", '{}/temp_mrvbf.tif'.format(temp_folder),
                                       '{}/mrvbf_stats'.format(temp_folder), "NODATA", "SUM")
    arcpy.TableToExcel_conversion('{}/mrvbf_stats'.format(temp_folder), '{}/mrvbf_stats.xls'.format(temp_folder))
    arcpy.TableToExcel_conversion(drain_shape, '{}/drain_lengths.xls'.format(temp_folder))

    x_size = float(arcpy.GetRasterProperties_management(raster, "CELLSIZEX").getOutput(0))
    y_size = float(arcpy.GetRasterProperties_management(raster, "CELLSIZEY").getOutput(0))

    df_stats = pd.ExcelFile('{}/mrvbf_stats.xls'.format(temp_folder)).parse(sheetname='mrvbf_stats',
                                                                            index_col='NAME')
    df_drain = pd.ExcelFile('{}/drain_lengths.xls'.format(temp_folder)).parse(sheetname='drain_lengths',
                                                                              index_col='Name')
    df_stats['Area_MRVBF'] = df_stats['SUM'] * x_size * y_size
    df_stats['w_valley'] = df_stats['Area_MRVBF'] / df_drain['Shape_Length']
    df_stats.index.name = 'Code'

    gp.AddMessage('Width braided valley  ... ')

    arcpy.TableToExcel_conversion(uttl_basins, '{}/UTTL_table.xls'.format(temp_folder))
    df_uttl = pd.ExcelFile('{}/UTTL_table.xls'.format(temp_folder)).parse(sheetname='UTTL_table', index_col='Name')
    df_stats['WB'] = 17.748 * (df_uttl['Areas_Km2'] ** 0.3508)
    df_stats['DoC'] = df_stats['w_valley'] / df_stats['WB']

    gp.AddMessage('Regionalization Q max Discharge UPME Methodology ... ')

    spatial_ref = arcpy.Describe(uttl_basins).spatialReference
    CTr_path = CTr
    qTr_path = qTr

    arcpy.ProjectRaster_management(CTr_path, '{}/CTr_reproject.tif'.format(temp_folder), spatial_ref, "NEAREST",
                                   '{} {}'.format(x_size, y_size), "#", "#", arcpy.Describe(CTr_path).spatialReference)
    arcpy.ProjectRaster_management(qTr_path, '{}/qTr_reproject.tif'.format(temp_folder), spatial_ref, "NEAREST",
                                   '{} {}'.format(x_size, y_size), "#", "#", arcpy.Describe(qTr_path).spatialReference)
    arcpy.ProjectRaster_management(fac, '{}/fac_reproject.tif'.format(temp_folder), spatial_ref, "NEAREST",
                                   '{} {}'.format(x_size, y_size), "#", "#", arcpy.Describe(fac).spatialReference)

    arcpy.MakeRasterLayer_management('{}/CTr_reproject.tif'.format(temp_folder), 'CTr')
    arcpy.MakeRasterLayer_management('{}/qTr_reproject.tif'.format(temp_folder), 'qTr')
    arcpy.MakeRasterLayer_management('{}/fac_reproject.tif'.format(temp_folder), 'fac')

    arcpy.gp.RasterCalculator_sa('"{}" * Power(("{}" * {} * {}) / 1000000,"{}")'.format('CTr', 'fac', x_size, y_size,
                                                                                        'qTr'),
                                 "{}/Qmax".format(workspace))

    arcpy.gp.ZonalStatisticsAsTable_sa(uttl_basins, "Name", '{}/Qmax'.format(workspace),
                                       '{}/Qmax_stats'.format(temp_folder), "DATA", "MAXIMUM")
    arcpy.TableToExcel_conversion('{}/Qmax_stats'.format(temp_folder), '{}/Qmax_stats.xls'.format(temp_folder))
    df_stats['Qmax'] = pd.ExcelFile('{}/Qmax_stats.xls'.format(temp_folder)).parse(sheetname='Qmax_stats',
                                                                                   index_col='NAME')['MAX']
    # Qmax Classification
    df_stats['Qmax_Class'] = 'Alto'

    low = np.percentile(df_stats['Qmax'], 25)
    low_medium = np.percentile(df_stats['Qmax'], 50)
    high_medium = np.percentile(df_stats['Qmax'], 75)

    df_stats.ix[df_stats[df_stats['Qmax'] < low].index, 'Qmax_Class'] = 'Bajo'
    df_stats.ix[df_stats[(df_stats['Qmax'] >= low) & (df_stats['Qmax'] < low_medium)].index, 'Qmax_Class'] = 'Medio Bajo'
    df_stats.ix[df_stats[(df_stats['Qmax'] >= low_medium) & (df_stats['Qmax'] < high_medium)].index, 'Qmax_Class'] = 'Medio Alto'

    df_stats['Slope'] = df_uttl['Slope']

    gp.AddMessage('Classification of streams alignment based on slope-flow thresholds ... ')

    df_stats['Beechie'] = None
    df_stats['BeechieNew'] = 'Inconfinados'
    df_stats['Smax'] = 0.1 * (df_stats['Qmax'] ** -0.42)
    df_stats['Smin'] = 0.05 * (df_stats['Qmax'] ** -0.61)

    df_stats.ix[df_stats[df_stats['DoC'] < 4.].index, 'Beechie'] = 'Confinados'
    df_stats.ix[df_stats[(df_stats['Slope'] > df_stats['Smax']) & (df_stats['DoC'] > 4.)].index, 'Beechie'] = 'Trenzados'
    df_stats.ix[df_stats[(df_stats['Slope'] < df_stats['Smax']) & (df_stats['Qmax'] < 15.) & (df_stats['DoC'] > 4.)].index, 'Beechie'] = 'Rectos'
    df_stats.ix[df_stats[(df_stats['Slope'] < df_stats['Smin']) & (df_stats['Qmax'] > 15.) & (df_stats['DoC'] > 4.)].index, 'Beechie'] = 'Meandricos'
    df_stats.ix[df_stats[(df_stats['Slope'] > df_stats['Smin']) & (df_stats['Slope'] < df_stats['Smax']) & (df_stats['Qmax'] > 15.) & (df_stats['DoC'] > 4.)].index, 'Beechie'] = 'Trenzados-Islas'

    # Beechie Reclass
    df_stats.ix[df_stats[df_stats['Beechie'] == 'Confinados'].index, 'BeechieNew'] = 'Confinados'

    df_stats.index = [str(i) for i in df_stats.index]
    df_stats.index.name = 'Code'
    df_stats[['w_valley', 'WB', 'DoC', 'Qmax', 'Qmax_Class', 'Smax', 'Smin', 'Beechie', 'BeechieNew']].to_csv('{}/Beechie_Table.csv'.format(temp_folder), index_label='Code')

    arcpy.TableToTable_conversion('{}/Beechie_Table.csv'.format(temp_folder), workspace, 'Beechie')

    expression = 'str(!Code!)'
    code_block = ''
    arcpy.AddField_management(os.path.join(workspace, 'Beechie'), 'STRCODE', 'TEXT', '', '', '10', '', 'NULLABLE', 'NON_REQUIRED', '')
    arcpy.CalculateField_management(os.path.join(workspace, 'Beechie'), 'STRCODE', expression, 'PYTHON', code_block)

    # Join Table to UTTL Segmentation Polygons
    arcpy.MakeFeatureLayer_management(uttl_basins, 'UTTL')
    arcpy.AddJoin_management('UTTL', 'Name', os.path.join(workspace, 'Beechie'), 'STRCODE')
    arcpy.CopyFeatures_management('UTTL', os.path.join(temp_folder, r'UTTL_Beechie.shp'))
    arcpy.DeleteField_management(os.path.join(temp_folder, r'UTTL_Beechie.shp'), ['Shape_Leng', 'Shape_Area', 'OBJECTID_1', 'Code', 'STRCODE'])

    arcpy.DeleteFeatures_management(os.path.join(workspace, r'UTTL_Basins'))
    arcpy.CopyFeatures_management(os.path.join(temp_folder, r'UTTL_Beechie.shp'), os.path.join(workspace, r'UTTL_Basins'))


def temp():
    df_stats = pd.ExcelFile('D:/Work/POTENTIAL_ARCPY/TEST/results/temp/Beechie_Table.xls').parse('Beechie', index_col='Code')
    df_stats.ix[df_stats[df_stats['DoC'] < 4.].index, 'Beechie'] = 'Confinados'
    df_stats.ix[df_stats[(df_stats['Slope'] > df_stats['Smax']) & (df_stats['DoC'] > 4.)].index, 'Beechie'] = 'Trenzados'
    df_stats.ix[df_stats[(df_stats['Slope'] < df_stats['Smax']) & (df_stats['Qmax'] < 15.) & (df_stats['DoC'] > 4.)].index, 'Beechie'] = 'Rectos'
    df_stats.ix[df_stats[(df_stats['Slope'] < df_stats['Smin']) & (df_stats['Qmax'] > 15.) & (df_stats['DoC'] > 4.)].index, 'Beechie'] = 'Meandricos'
    df_stats.ix[df_stats[(df_stats['Slope'] > df_stats['Smin']) & (df_stats['Slope'] < df_stats['Smax']) & (df_stats['Qmax'] > 15.) & (df_stats['DoC'] > 4.)].index, 'Beechie'] = 'Trenzados-Islas'


def main(env):
    gp = arcgisscripting.create()
    gp.CheckOutExtension("Spatial")

    if env:
        mdt_file = gp.GetParameterAsText(0)
        gdb_path = gp.GetParameterAsText(1)
        name_out = gp.GetParameterAsText(2)
        par1 = gp.GetParameterAsText(3)
        par2 = gp.GetParameterAsText(4)
        par3 = gp.GetParameterAsText(5)
        par4 = gp.GetParameterAsText(6)
        par5 = gp.GetParameterAsText(7)
        show = gp.GetParameterAsText(8)
        par6 = gp.GetParameterAsText(9)
        par7 = gp.GetParameterAsText(10)
        par8 = gp.GetParameterAsText(11)
        par9 = gp.GetParameterAsText(12)
        par10 = gp.GetParameterAsText(13)
    else:
        mdt_file = r'E:\AH_02\data\srtm_col_3116.tif'
        gdb_path = r'E:\AH_02\UTTL.gdb'
        name_out = 'mrvbf'
        par1 = 8
        par2 = 0.4
        par3 = 0.35
        par4 = 4
        par5 = 3
        show = True
        par6 = r'E:\AH_02\UTTL.gdb\Drain_UTTL'
        par7 = r'E:\AH_02\UTTL.gdb\UTTL_Basins'
        par8 = r'E:\AH_02\UTTL.gdb\fac'
        par9 = r'E:\AH_02\data\Qmax_Regional_UPME_CTr.tif'
        par10 = r'E:\AH_02\data\Qmax_Regional_UPME_qTr.tif'

    gp.AddMessage('Making temps folders')
    temp_folder = '{}/temp'.format(os.path.dirname(os.path.abspath(gdb_path)))

    if os.path.exists(temp_folder):
        gp.AddMessage('folder temp already exists')
    else:
        os.mkdir(temp_folder)

    import_data_to_saga(mdt_file, temp_folder)
    run_mrvbf(temp=temp_folder, t_slope=par1, tv=par2, tr=par3, p_slope=par4, p=par5)
    export_data_from_saga(temp_folder, out_grid=name_out, gdb=gdb_path, show=show)

    fn_beechie(raster='{}/{}'.format(gdb_path, name_out), drain_shape=par6, uttl_basins=par7, fac=par8, workspace=gdb_path, CTr=par9, qTr=par10)


if __name__ == "__main__":
    # temp()
    main(env=False)
