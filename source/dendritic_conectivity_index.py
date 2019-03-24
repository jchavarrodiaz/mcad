# -*- coding: utf-8 -*-
import os

import arcpy

from add_attribute import zonal_stats


def clear_layers():
    mxd = arcpy.mapping.MapDocument('CURRENT')
    for df in arcpy.mapping.ListDataFrames(mxd):
        for lyr in arcpy.mapping.ListLayers(mxd, "", df):
            arcpy.mapping.RemoveLayer(df, lyr)
    del mxd


def dci(fdr, out_patch, gdb_path, uttl):

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

    arcpy.gp.RasterCalculator_sa('Con("dci" <= 0.005, 1.0, Con(("dci" > 0.005)  &  ("dci" <= 0.01), 1.5, Con(("dci" > 0.01) & ("dci" <= 0.1),2.0, Con(("dci" > 0.1) & ("dci" <= 0.3),2.5, 3.0))))',
                                 os.path.join(gdb_path, 'dci_reclass'))

    zonal_stats(uttl, os.path.join(gdb_path, 'dci_reclass'), 'dci', 'MAXIMUM')


def main(env):
    arcpy.CheckOutExtension('Spatial')

    if env:
        uttl = arcpy.GetParameterAsText(0)
        fdr_path = arcpy.GetParameterAsText(1)
        dci_output = arcpy.GetParameterAsText(2)
        clear_layers()
    else:
        uttl = r'C:\DIRECTOS\results\UTTL.gdb\UTTL_Basins'
        fdr_path = r'C:\DIRECTOS\results\UTTL.gdb\fdr'
        dci_output = 'dci'

    gdb_path = os.path.dirname(uttl)
    dci(fdr_path, dci_output, gdb_path, uttl)


if __name__ == '__main__':
    main(env=True)
