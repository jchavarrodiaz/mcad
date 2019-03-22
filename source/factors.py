# -*- coding: utf-8 -*-
import os

import arcpy


def save_mxd():
    mapdoc = arcpy.mapping.MapDocument('CURRENT')
    mapdoc.save()


def clear_layers():
    mxd = arcpy.mapping.MapDocument('CURRENT')
    for df in arcpy.mapping.ListDataFrames(mxd):
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            arcpy.mapping.RemoveLayer(df, lyr)
    del mxd


def compensation_factors(uttl, factors):

    gdb = os.path.dirname(uttl)

    arcpy.env.workspace = gdb
    arcpy.env.overwriteOutput = True

    ls_fields = factors.split(";")

    expression = '!{}! + !{}! + !{}! + !{}!'.format(*ls_fields)
    code_block = ''
    arcpy.AddField_management(uttl, 'Factores', 'SHORT', '', '', '10', '', 'NULLABLE', 'NON_REQUIRED', '')
    arcpy.CalculateField_management(uttl, 'Factores', expression, 'PYTHON_9.3', code_block)


def tif_export(uttl, name):
    gdb = os.path.dirname(uttl)
    cell_size_like = os.path.join(gdb, 'fac')
    arcpy.FeatureToRaster_conversion(uttl, 'Factores', name, cell_size_like)


def main(env):
    arcpy.CheckOutExtension('Spatial')

    if env:
        uttl = arcpy.GetParameterAsText(0)
        factors = arcpy.GetParameterAsText(1)
        make_tif = arcpy.GetParameterAsText(2)
        tif_name = arcpy.GetParameterAsText(3)

        clear_layers()
    else:
        uttl = r'C:\DIRECTOS\results\UTTL.gdb\UTTL_Basins'
        factors = 'Rareza;Reps_Value;sp_value;dci'
        make_tif = True
        tif_name = 'factores_compensacion'

    compensation_factors(uttl, factors)
    if make_tif:
        if arcpy.Exists(os.path.join(os.path.dirname(uttl), tif_name)):
            arcpy.Delete_management(os.path.dirname(uttl), tif_name)
        tif_export(uttl, tif_name)


if __name__ == '__main__':
    main(env=True)
