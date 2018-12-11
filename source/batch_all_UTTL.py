# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import arcpy
import ArcHydroTools
from arcpy.sa import *
import string,os,time,exceptions,arcgisscripting
import ArcHydroTools
import math
from Funciones import preproc
from Funciones import nodhidro
from Funciones import nodtopo
from Funciones import batc_points
from Funciones import gen_subwatershed
#Definiendo la referencia espacial
src=arcpy.SpatialReference(3116)
# Geoprocessor object
gp = arcgisscripting.create()

#Chequeando la extencion spatial
arcpy.CheckOutExtension("Spatial")

#Obteniendo datos desde el usuario

d=arcpy.GetParameterAsText(0) # Dem
FldSla = arcpy.GetParameterAsText(1) #Folder de salida
Nombregdb=arcpy.GetParameterAsText(2)#Nombre GDB
RedOpcional=arcpy.GetParameterAsText(3)
Umbral=arcpy.GetParameterAsText(4)#este umbral solo sirve para generar el condit pero no la red drenaje.
mostrar=arcpy.GetParameterAsText(5)
gdb_ruta=os.path.join(FldSla, Nombregdb+".gdb")
if os.path.exists(gdb_ruta) == True:
    arcpy.Delete_management(gdb_ruta)

laGDB=arcpy.CreateFileGDB_management(FldSla, Nombregdb+".gdb")

Textogdb=str(laGDB)
arcpy.env.addOutputsToMap = mostrar
laescala=arcpy.GetParameterAsText(6)
ladistancia=arcpy.GetParameterAsText(7)


if __name__ == '__main__':

    preproc(d, FldSla, Nombregdb, RedOpcional,Umbral)

    strfeature=os.path.join(Textogdb,"StreamFeature")
    strraster=os.path.join(Textogdb,"Str")
    fdr=os.path.join(Textogdb,"Fdr")
    fac=os.path.join(Textogdb,"Fac")
    gp.SetProgressor("default", "Nodos hidrologicos")
    gp.AddMessage("realizando nodos hidro...")
    nodhidro(strfeature,strraster,fdr,Textogdb)
    gridv=os.path.join(Textogdb,"hydroDEM")
    gp.SetProgressor("default", "Nodos topograficos")
    gp.AddMessage("realizando nodos topograficos...")
    dirtemp=os.path.dirname(Textogdb)
    nodtopo(gridv,laescala, fdr,strraster,strfeature,ladistancia, Textogdb)
    topo=os.path.join(Textogdb,"Nodos_topograficos")
    hidro=os.path.join(Textogdb,"nodos_hidro")
    batc_points(topo,hidro,Textogdb)
    gp.SetProgressor("default", "Batchpoints")
    gp.AddMessage("realizando batchpoints...")
    lospuntos=os.path.join(Textogdb,"BatchPoints_F")
    gp.SetProgressor("default", "Nodos subwatersheds")
    gp.AddMessage("realizando subwatershed...")
    gen_subwatershed(lospuntos,fdr,strraster, Textogdb)
