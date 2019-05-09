# -*- coding: utf-8 -*-
import os
import arcgisscripting

import arcpy
import pandas as pd

from add_attribute import zonal_stats


def clear_layers():
    mxd = arcpy.mapping.MapDocument('CURRENT')
    for df in arcpy.mapping.ListDataFrames(mxd):
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            arcpy.mapping.RemoveLayer(df, lyr)
    del mxd


def classify_data(shapefile, oldFieldVals, newField, table):
    gp = arcgisscripting.create()
    gp.addField(shapefile, newField, 'TEXT', 25)

    rows = gp.UpdateCursor(shapefile)
    row = rows.Next()

    while row:
        row.SetValue(newField, table[row.GetValue(oldFieldVals)])
        rows.UpdateRow(row)
        row = rows.Next()


def dci(fdr, out_patch, gdb_path, uttl, config_file):

    result_folder = os.path.dirname(gdb_path)

    arcpy.env.workspace = result_folder
    arcpy.env.overwriteOutput = True

    downstream = os.path.join(result_folder, 'temp', 'downstream.tif')
    upstream = os.path.join(result_folder, 'temp', 'upstream.tif')

    arcpy.gp.FlowLength_sa(fdr, downstream, "DOWNSTREAM", "")
    arcpy.gp.FlowLength_sa(fdr, upstream, "UPSTREAM", "")

    arcpy.MakeRasterLayer_management(downstream, 'downstream')
    arcpy.MakeRasterLayer_management(upstream, 'upstream')

    arcpy.gp.RasterCalculator_sa('"upstream" / ("upstream" + "downstream")', os.path.join(gdb_path, out_patch))

    arcpy.gp.MakeRasterLayer_management(os.path.join(gdb_path, out_patch), 'dci')

    xls_file = pd.ExcelFile(config_file)
    df_criteria = xls_file.parse('Conectividad', index_col='Conectividad')
    very_high_low_input = df_criteria.ix['Muy Alta', 'Rango Inferior']
    high_low_input = df_criteria.ix['Alta', 'Rango Inferior']
    medium_low_input = df_criteria.ix['Media', 'Rango Inferior']
    low_low_input = df_criteria.ix['Baja', 'Rango Inferior']

    very_high_value = df_criteria.ix['Muy Alta', 'Value']
    high_value = df_criteria.ix['Alta', 'Value']
    medium_value = df_criteria.ix['Media', 'Value']
    low_value = df_criteria.ix['Baja', 'Value']
    very_low_value = df_criteria.ix['Muy Baja', 'Value']

    arcpy.gp.RasterCalculator_sa('Con("dci" <= {}, {}, Con(("dci" > {})  &  ("dci" <= {}), {}, Con(("dci" > {}) & ("dci" <= {}),{}, Con(("dci" > {}) & ("dci" <= {}),{}, {}))))'.format(low_low_input, very_low_value, low_low_input,
                                                                                                                                                                                        medium_low_input, low_value, medium_low_input,
                                                                                                                                                                                        high_low_input, medium_value, high_low_input,
                                                                                                                                                                                        very_high_low_input, high_value, very_high_value),
                                 os.path.join(gdb_path, 'dci_reclass'))

    arcpy.gp.RasterCalculator_sa('Con("dci" <= 0.005, 1.0, Con(("dci" > 0.005)  &  ("dci" <= 0.01), 1.5, Con(("dci" > 0.01) & ("dci" <= 0.1),2.0, Con(("dci" > 0.1) & ("dci" <= 0.3),2.5, 3.0))))',
                                 os.path.join(gdb_path, 'dci_reclass'))

    zonal_stats(uttl, os.path.join(gdb_path, 'dci_reclass'), 'dci', 'MAXIMUM')
    table = {val: key for (key, val) in df_criteria['Value'].to_dict().items()}
    classify_data(uttl, 'dci', 'conec_class', table)


def main(env):
    arcpy.CheckOutExtension('Spatial')

    if env:
        uttl = arcpy.GetParameterAsText(0)
        fdr_path = arcpy.GetParameterAsText(1)
        dci_output = arcpy.GetParameterAsText(2)
        config_file = arcpy.GetParameterAsText(3)
        clear_layers()
    else:
        uttl = r'C:\DIRECTOS\results\UTTL.gdb\UTTL_Basins'
        fdr_path = r'C:\DIRECTOS\results\UTTL.gdb\fdr'
        dci_output = 'dci'
        config_file = r'C:\DIRECTOS\data\config_criteria.xlsx'

    gdb_path = os.path.dirname(uttl)
    dci(fdr_path, dci_output, gdb_path, uttl, config_file)


if __name__ == '__main__':
    main(env=True)
