# -*- coding: utf-8 -*-
import arcgisscripting
import os

import arcpy

from flores import slope_calc, areas_watershed, flores
from beechie import import_data_to_saga, run_mrvbf, export_data_from_saga, fn_beechie
from showing_things import show_things


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
        gdb_path = arcpy.GetParameterAsText(0)
        dem_path = arcpy.GetParameterAsText(1)
        batch_points_path = arcpy.GetParameterAsText(2)
        drain_network_path = arcpy.GetParameterAsText(3)
        uttl = arcpy.GetParameterAsText(4)
        epsg = arcpy.GetParameterAsText(5)
        fac_path = arcpy.GetParameterAsText(6)

        mrvbf = gp.GetParameterAsText(7)
        par1 = gp.GetParameterAsText(8)
        par2 = gp.GetParameterAsText(9)
        par3 = gp.GetParameterAsText(10)
        par4 = gp.GetParameterAsText(11)
        par5 = gp.GetParameterAsText(12)
        show = gp.GetParameterAsText(13)
        par9 = gp.GetParameterAsText(14)
        par10 = gp.GetParameterAsText(15)
    else:
        gdb_path = r'C:\Users\jchav\AH_01\CATATUMBO\results\UTTL.gdb'
        dem_path = r'C:\Users\jchav\AH_01\CATATUMBO\data\DEM_Raw_Init_Catatumbo_Plus_750_3116.tif'
        batch_points_path = r'C:\Users\jchav\AH_01\CATATUMBO\results\UTTL.gdb\BatchPoints'
        drain_network_path = r'C:\Users\jchav\AH_01\CATATUMBO\results\UTTL.gdb\drainage_line'
        epsg = 3116
        uttl = r'C:\Users\jchav\AH_01\CATATUMBO\results\UTTL.gdb\UTTL_Basins'
        fac_path = r'C:\Users\jchav\AH_01\CATATUMBO\results\UTTL.gdb\fac'

        mrvbf = 'mrvbf'
        par1 = 8
        par2 = 0.4
        par3 = 0.35
        par4 = 4
        par5 = 3
        show = True
        par9 = r'C:\Users\jchav\AH_01\CATATUMBO\data\Qmax_Regional_UPME_CTr.tif'
        par10 = r'C:\Users\jchav\AH_01\CATATUMBO\data\Qmax_Regional_UPME_qTr.tif'

    gp.AddMessage('FLORES ...')
    slope_calc(batch_point=batch_points_path, workspace=gdb_path, drain=drain_network_path, epsg=epsg, dem=dem_path, uttl=uttl)
    areas_watershed(workspace=gdb_path, fac=fac_path, uttl=uttl)
    flores(workspace=gdb_path, uttl=uttl)
    gp.AddMessage('FLORES: was successfully')

    par6 = os.path.join(gdb_path, 'Drain_UTTL')

    gp.AddMessage('BECHIEE ...')
    temp_folder = r'{}\temp'.format(os.path.dirname(os.path.abspath(gdb_path)))
    if os.path.exists(temp_folder):
        gp.AddMessage('folder temp already exists')
    else:
        os.mkdir(temp_folder)
    gp.AddMessage('Running SAGA - MRVBF')
    import_data_to_saga(dem_path, temp_folder)
    run_mrvbf(temp=temp_folder, t_slope=par1, tv=par2, tr=par3, p_slope=par4, p=par5)
    export_data_from_saga(temp_folder, out_grid=mrvbf, gdb=gdb_path, show=show)
    gp.AddMessage('Running Beechie')
    fn_beechie(raster='{}/{}'.format(gdb_path, mrvbf), drain_shape=par6, uttl_basins=uttl, fac=fac_path, workspace=gdb_path, CTr=par9, qTr=par10)
    if show:
        show_things(uttl, 'UTTL', os.path.dirname(gdb_path))
    

if __name__ == '__main__':
    main(env=True)
