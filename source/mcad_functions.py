#DEFINICION DE FUNCIONES
# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
import arcpy
import ArcHydroTools
from arcpy.sa import *
import string,os,time,exceptions,arcgisscripting


#Definiendo la referencia espacial
src=arcpy.SpatialReference(3116)
# Geoprocessor object
gp = arcgisscripting.create()
#Chequeando la extencion spatial
arcpy.CheckOutExtension("Spatial")
def addLayer(layer):
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df=arcpy.mapping.ListDataFrames(mxd, "*")[0]
    addLayer=arcpy.mapping.Layer(layer)
    arcpy.mapping.AddLayer(df,addLayer)

def preproc(dem, folder, nomgdb, redop,umbrele):

    #arcpy.env.addOutputsToMap = mostrar
    gdb_ruta=os.path.join(folder, nomgdb+".gdb")


    if os.path.exists(gdb_ruta) == True:
        arcpy.Delete_management(gdb_ruta)


    gdb=arcpy.CreateFileGDB_management(folder, nomgdb+".gdb")
    Textogdb=str(gdb)

    gp.SetProgressor("step", "Iniciando Preproceso ArcHidro...")
    arcpy.ProjectRaster_management(dem, os.path.join(folder,"magna.tif"), 4686,"BILINEAR", "#", "#", "#", "#")
    arcpy.ProjectRaster_management(os.path.join(folder,"magna.tif"), os.path.join(folder,"reproject.tif"), 3116,"BILINEAR", "100", "#", "#", "#") # proyectar raster
    p=os.path.join(folder,"reproject.tif")
    gp.SetProgressorPosition(0)
##    gp.AddMessage(str(mostrar))
    gp.AddMessage("Processing Fill...")
    FillAH=ArcHydroTools.FillSinks(p,os.path.join(Textogdb,r"FillSinksAH"))
    datocel = arcpy.GetRasterProperties_management(p, "CELLSIZEX")
    num=datocel.getOutput(0)

    gp.SetProgressorPosition(15)
    gp.AddMessage("Procesando Red de Drenaje...")
    if redop=="":
        FlowDirAH=ArcHydroTools.FlowDirection(FillAH,os.path.join(Textogdb,r"zFlowDirsAH"))
        FlowAcAH=ArcHydroTools.FlowAccumulation(FlowDirAH, os.path.join(Textogdb,r"FlAcAH"))
        condit = Con(Raster(FlowAcAH)>float(umbrele), 5,0) #codicional raster ERROR
        condit.save(os.path.join(Textogdb,r"Condit"))
    else:
        src=arcpy.SpatialReference(3116)
        fieldInfo=""
        fieldObjList=arcpy.ListFields(redop)
        fieldNameList = []
        for field in fieldObjList:
            fieldNameList.append(field.name)
            fieldInfo = fieldInfo + field.name + " " + field.name + " HIDDEN;"

        arcpy.MakeFeatureLayer_management(redop,"Layer","#",os.path.dirname(Textogdb), fieldInfo[:-1])
        arcpy.CopyFeatures_management("Layer",os.path.join(Textogdb,"Red_Dren_media"))
        redinter=os.path.join(Textogdb,"Red_Dren_media")

        arcpy.AddField_management(redinter, "Valor_New" , "LONG", 5, "#","#","New_Valor","NULLABLE","NON_REQUIRED","#")
        arcpy.CalculateField_management(redinter, "Valor_New", "\"5\"" , "PYTHON_9.3")
        con=arcpy.FeatureToRaster_conversion(redinter, "Valor_New",os.path.join(Textogdb,"Condit"),"#")
        condit=Raster(con)



    gp.SetProgressorPosition(30)
    gp.AddMessage("Procesando AgreeDem...")
    Rest=os.path.join(Textogdb,r"FillSinksAH")-condit
    Rest.save(os.path.join(Textogdb,"AgreeDem"))

    gp.SetProgressorPosition(45)
    gp.AddMessage("Procesando hydroDEM...")
    hidroDem = ArcHydroTools.FillSinks(Rest,os.path.join(Textogdb,"hydroDEM")) #Realizar Fill

    gp.SetProgressorPosition(60)
    gp.AddMessage("Procesando FDR...")
    Fdr = ArcHydroTools.FlowDirection(hidroDem,os.path.join(Textogdb,r"Fdr")) #realizar direccion de flujo

    gp.SetProgressorPosition(75)
    gp.AddMessage("Procesando FAC...")
    Fac = ArcHydroTools.FlowAccumulation(Fdr, os.path.join(Textogdb,r"Fac"))  #flujo de acumulacion por archidro

    gp.SetProgressorPosition(90)
    gp.AddMessage("Procesando STR...")
    Str=ArcHydroTools.StreamDefinition(Fac,1,os.path.join(Textogdb,r"Str"),10)
    SToFeature=StreamToFeature (os.path.join(Textogdb,r"Str"),os.path.join(Textogdb,"Fdr"), os.path.join(Textogdb,"StreamFeature"), "SIMPLIFY")
    addLayer(os.path.join(Textogdb,r"Str"))
    gp.SetProgressorPosition(100)
    gp.AddMessage("Proceso Terminado")


def nodhidro(fturecorr,ras_corriente,dir_fluj,Textogdb):
    arcpy.FeatureVerticesToPoints_management(fturecorr, os.path.join(Textogdb,"nodos_hidro"), "BOTH_ENDS")
    addLayer( os.path.join(Textogdb,"nodos_hidro"))
    ArcHydroTools.StreamSegmentation(ras_corriente,dir_fluj, os.path.join(Textogdb,r"StrLink"),"#","#")#Create a Grid of stream segments with unique valus of identification.


def nodtopo(grid,escala, fdir,stream,fturecorriente,valor_equidis, Textogdb):

    direc=os.path.dirname(Textogdb)
    GridCellSizeX = arcpy.GetRasterProperties_management(grid, "CELLSIZEX","Band_1")
    GridCellSizeY = arcpy.GetRasterProperties_management(grid, "CELLSIZEY","Band_1")
    ConValor = long( int(escala) )/ ( 100 * ( ( ( float(str(GridCellSizeX)) + float(str(GridCellSizeY)) ) / 2 ) / 30 ) )
    arcpy.FeatureVerticesToPoints_management(fturecorriente, os.path.join(Textogdb,"nodos_hidro"), "BOTH_ENDS")
    ArcHydroTools.StreamSegmentation(stream,fdir, os.path.join(Textogdb,r"StrLink"),"#","#")#Create a Grid of stream segments with unique valus of identification.
    sorder= StreamOrder (stream,fdir,"STRAHLER")
    sorder.save(os.path.join(Textogdb,r"StreamOrder"))
    StreamToFeature(sorder,fdir,os.path.join(Textogdb,"DrenagemGDBFC"), "SIMPLIFY")
    DrenGDB=os.path.join(Textogdb,"DrenagemGDBFC")
    gp.AddMessage("Processing Make Feature Layer...")
    gp.AddMessage(str(ConValor))
    NomeDrenLayer = "Drenagem Automatizada Con " + str(ConValor)
    arcpy.MakeFeatureLayer_management(DrenGDB,NomeDrenLayer)

    river_merge(NomeDrenLayer,valor_equidis,grid,ConValor,direc, Textogdb)

def river_merge(NomeDrenLayer,valor_equidis, grid,valor,dirtemp,Textogdb):

    if os.path.exists(dirtemp + "\\Merge"):
        txtfile = open(dirtemp + "\\Merge", 'r')
        readcon = txtfile.readline().replace("\n","")
        readnam = txtfile.readline().replace("\n","")
        txtfile.close()
    else:
        readcon = -1
        readnam = ""

    if readcon != str(valor) or readnam != grid:

        # River Merge
        # Count the highest stream order
        GridCodeList = []
        rows = gp.SearchCursor(NomeDrenLayer)
        row = rows.Next()

        while row:
            GridCodeList.append(row.getValue("GRID_CODE"))
            row = rows.Next()
        GridCodeList.sort()

        MaxGridCode = GridCodeList[-1]
        del row
        del rows
        del GridCodeList

        GridCodeAtual = MaxGridCode

        gp.SetProgressor("default", "Processing River Merge...")
        gp.AddMessage("Merging drainage segments. This might be lengthy...")
        StrErro = "River merging failed."
        # Dissolve by MERGEID
        # Insert new fields in the attribute table
        gp.AddField_management(NomeDrenLayer, "MERGEID", "LONG")

        gp.AddField_management(NomeDrenLayer, "OID_LINK", "LONG")

        gp.AddField_management(NomeDrenLayer, "LINK_OK", "SHORT")

        CursorField = gp.UpdateCursor(NomeDrenLayer)
        LinhaField = CursorField.Next()

        while LinhaField:
            LinhaField.MERGEID = -1
            LinhaField.OID_LINK = -1
            LinhaField.LINK_OK = 0
            CursorField.UpdateRow(LinhaField)
            LinhaField = CursorField.Next()

        del CursorField, LinhaField

        def ComprimentoComposto(PointerLinha):
            ComprimentoTotal = 0
            NumLinhas = 1
            ContinuarSomando = True
            LinhaAtual = PointerLinha
            while ContinuarSomando == True:
                ComprimentoTotal += LinhaAtual.Shape_Length
                if LinhaAtual.OID_LINK == -1:
                    ContinuarSomando = False
                else:
                    CursorProx = gp.SearchCursor(NomeDrenLayer, "OBJECTID = " + str(LinhaAtual.OID_LINK))
                    LinhaProx = CursorProx.Next()
                    while LinhaProx:
                        LinhaAtual = LinhaProx
                        NumLinhas += 1
                        break
                    del CursorProx, LinhaProx

            return ComprimentoTotal

        # Begin River Merge
        GridCodeAtual = 1

        # Number of union (merge) groups ready for Dissolve
        MergeIDCount = 0

        ContinuarRodando = True

        while ContinuarRodando == True:
            CursorFoco = gp.UpdateCursor(NomeDrenLayer)
            LinhaFoco = CursorFoco.Next()

            ContinuarRodando = False

            while LinhaFoco:
                EmEspera = False
                if LinhaFoco.LINK_OK == 0:
                    if LinhaFoco.OID_LINK == -1:
                        CursorSec = gp.SearchCursor(NomeDrenLayer, "TO_NODE = " + str(LinhaFoco.FROM_NODE))
                        LinhaSec = CursorSec.Next()
                        while LinhaSec:
                            ContinuarRodando = True # There are more operations to do after the loop ends 'Keep running'
                            EmEspera = True
                            break
                        del CursorSec, LinhaSec
                    if EmEspera == False:
                        if LinhaFoco.MERGEID == -1:
                            LinhaFoco.MERGEID = MergeIDCount
                            CursorFoco.UpdateRow(LinhaFoco)
                            MergeIDCount += 1

                        # Search if there is a line with Tonode == FocusLine.Tonode
                        ToNodeMaior = True
                        CursorSec = gp.SearchCursor(NomeDrenLayer, "TO_NODE = " + str(LinhaFoco.TO_NODE) + " and OBJECTID <> " + str(LinhaFoco.OBJECTID))
                        LinhaSec = CursorSec.Next()
                        while LinhaSec:
                            if LinhaSec.OID_LINK == -1:
                                CursorTerc = gp.SearchCursor(NomeDrenLayer, "TO_NODE = " + str(LinhaSec.FROM_NODE))
                                LinhaTerc = CursorTerc.Next()
                                while LinhaTerc:
                                    EmEspera = True
                                    ContinuarRodando = True # There are more operations to do after the loop ends 'Keep running'
                                    break
                                del CursorTerc, LinhaTerc
                                if EmEspera == True:
                                    break
                            if ComprimentoComposto(LinhaFoco) < ComprimentoComposto(LinhaSec):
                                ToNodeMaior = False
                                break
                            LinhaSec = CursorSec.Next()
                        del CursorSec, LinhaSec
                        if EmEspera == False:
                            # Find and mark the next line downstream joining it with the FocusLine
                            if ToNodeMaior == True:
                                CursorSec = gp.UpdateCursor(NomeDrenLayer, "FROM_NODE = " + str(LinhaFoco.TO_NODE))
                                LinhaSec = CursorSec.Next()
                                while LinhaSec:
                                    LinhaSec.MERGEID = LinhaFoco.MERGEID
                                    LinhaSec.OID_LINK = LinhaFoco.OBJECTID
                                    CursorSec.UpdateRow(LinhaSec)
                                    break
                                del CursorSec, LinhaSec
                            LinhaFoco.LINK_OK = 1
                            CursorFoco.UpdateRow(LinhaFoco)
                LinhaFoco = CursorFoco.Next()
            del CursorFoco, LinhaFoco
        DrenDissolve = os.path.join(Textogdb,"DrenDissolve")
        gp.Dissolve_management(NomeDrenLayer,DrenDissolve, "MERGEID")

        # 3D red drenaje drainage network
        gp.SetProgressor("default", "Processing Interpolate Shape...")
        NomeDren3D = os.path.join(Textogdb,"Dren3D")
        gp.interpolateshape_3d( grid, DrenDissolve, NomeDren3D)

        txtfile = open(dirtemp + "\\Merge", 'w')
        txtfile.write(str(valor) + "\n" + grid)
        txtfile.close()

        gp.AddMessage("The 3D drainage network was generated successfully.")
    else:
                # River Merge
        # Count the highest stream order
        GridCodeList = []
        rows = gp.SearchCursor(NomeDrenLayer)
        row = rows.Next()

        while row:
            GridCodeList.append(row.getValue("GRID_CODE"))
            row = rows.Next()
        GridCodeList.sort()

        MaxGridCode = GridCodeList[-1]
        del row
        del rows
        del GridCodeList

        GridCodeAtual = MaxGridCode

        gp.SetProgressor("default", "Processing River Merge...")
        gp.AddMessage("Merging drainage segments. This might be lengthy...")
        StrErro = "River merging failed."
        # Dissolve by MERGEID
        # Insert new fields in the attribute table
        gp.AddField_management(NomeDrenLayer, "MERGEID", "LONG")

        gp.AddField_management(NomeDrenLayer, "OID_LINK", "LONG")

        gp.AddField_management(NomeDrenLayer, "LINK_OK", "SHORT")

        CursorField = gp.UpdateCursor(NomeDrenLayer)
        LinhaField = CursorField.Next()

        while LinhaField:
            LinhaField.MERGEID = -1
            LinhaField.OID_LINK = -1
            LinhaField.LINK_OK = 0
            CursorField.UpdateRow(LinhaField)
            LinhaField = CursorField.Next()

        del CursorField, LinhaField

        def ComprimentoComposto(PointerLinha):
            ComprimentoTotal = 0
            NumLinhas = 1
            ContinuarSomando = True
            LinhaAtual = PointerLinha
            while ContinuarSomando == True:
                ComprimentoTotal += LinhaAtual.Shape_Length
                if LinhaAtual.OID_LINK == -1:
                    ContinuarSomando = False
                else:
                    CursorProx = gp.SearchCursor(NomeDrenLayer, "OBJECTID = " + str(LinhaAtual.OID_LINK))
                    LinhaProx = CursorProx.Next()
                    while LinhaProx:
                        LinhaAtual = LinhaProx
                        NumLinhas += 1
                        break
                    del CursorProx, LinhaProx

            return ComprimentoTotal

        # Begin River Merge
        GridCodeAtual = 1

        # Number of union (merge) groups ready for Dissolve
        MergeIDCount = 0

        ContinuarRodando = True

        while ContinuarRodando == True:
            CursorFoco = gp.UpdateCursor(NomeDrenLayer)
            LinhaFoco = CursorFoco.Next()

            ContinuarRodando = False

            while LinhaFoco:
                EmEspera = False
                if LinhaFoco.LINK_OK == 0:
                    if LinhaFoco.OID_LINK == -1:
                        CursorSec = gp.SearchCursor(NomeDrenLayer, "TO_NODE = " + str(LinhaFoco.FROM_NODE))
                        LinhaSec = CursorSec.Next()
                        while LinhaSec:
                            ContinuarRodando = True # There are more operations to do after the loop ends 'Keep running'
                            EmEspera = True
                            break
                        del CursorSec, LinhaSec
                    if EmEspera == False:
                        if LinhaFoco.MERGEID == -1:
                            LinhaFoco.MERGEID = MergeIDCount
                            CursorFoco.UpdateRow(LinhaFoco)
                            MergeIDCount += 1

                        # Search if there is a line with Tonode == FocusLine.Tonode
                        ToNodeMaior = True
                        CursorSec = gp.SearchCursor(NomeDrenLayer, "TO_NODE = " + str(LinhaFoco.TO_NODE) + " and OBJECTID <> " + str(LinhaFoco.OBJECTID))
                        LinhaSec = CursorSec.Next()
                        while LinhaSec:
                            if LinhaSec.OID_LINK == -1:
                                CursorTerc = gp.SearchCursor(NomeDrenLayer, "TO_NODE = " + str(LinhaSec.FROM_NODE))
                                LinhaTerc = CursorTerc.Next()
                                while LinhaTerc:
                                    EmEspera = True
                                    ContinuarRodando = True # There are more operations to do after the loop ends 'Keep running'
                                    break
                                del CursorTerc, LinhaTerc
                                if EmEspera == True:
                                    break
                            if ComprimentoComposto(LinhaFoco) < ComprimentoComposto(LinhaSec):
                                ToNodeMaior = False
                                break
                            LinhaSec = CursorSec.Next()
                        del CursorSec, LinhaSec
                        if EmEspera == False:
                            # Find and mark the next line downstream joining it with the FocusLine
                            if ToNodeMaior == True:
                                CursorSec = gp.UpdateCursor(NomeDrenLayer, "FROM_NODE = " + str(LinhaFoco.TO_NODE))
                                LinhaSec = CursorSec.Next()
                                while LinhaSec:
                                    LinhaSec.MERGEID = LinhaFoco.MERGEID
                                    LinhaSec.OID_LINK = LinhaFoco.OBJECTID
                                    CursorSec.UpdateRow(LinhaSec)
                                    break
                                del CursorSec, LinhaSec
                            LinhaFoco.LINK_OK = 1
                            CursorFoco.UpdateRow(LinhaFoco)
                LinhaFoco = CursorFoco.Next()
            del CursorFoco, LinhaFoco
        DrenDissolve = os.path.join(Textogdb,"DrenDissolve")
        gp.Dissolve_management(NomeDrenLayer,DrenDissolve, "MERGEID")

        # 3D red drenaje drainage network
        gp.SetProgressor("default", "Processing Interpolate Shape...")
        NomeDren3D = os.path.join(Textogdb,"Dren3D")
        gp.interpolateshape_3d( grid, DrenDissolve, NomeDren3D)

        txtfile = open(dirtemp + "\\Merge", 'w')
        txtfile.write(str(valor) + "\n" + grid)
        txtfile.close()

        gp.AddMessage("The 3D drainage network was generated successfully.")



##        gp.SetProgressor("default", "Loading data...")
##        StrErro = "It wasn't possible to load the existing 3D drainage network."
##        DrenGDB= os.path.join(Textogdb, "DrenagemGDBFC")
##        gp.AddMessage("A 3D drainage network with these parameters already exists and will be used...")
##        NomeDrenLayer = "Drenagem Automatizada Con " + str(valor)
##        NomeDren3D = os.path.join(Textogdb,"Dren3D")
##        gp.MakeFeatureLayer_management(DrenGDB, NomeDrenLayer)

    # Save the 3D drainage network file
    arcpy.FeatureClassToFeatureClass_conversion(NomeDren3D,Textogdb,"drenagem","#","#","#")

    # Identify geometry field
    DescLayer = gp.Describe(NomeDren3D)
    CampoGeometria = DescLayer.ShapeFieldName

    def Comprimento(LinhaPointer):
        Feature = LinhaPointer.GetValue(CampoGeometria)
        return Feature.Length


    gp.SetProgressor("default", "Processing RDE...")
    StrErro = "RDE index measuring failed."

    gp.SetProgressorPosition(0)
    gp.AddMessage("Creating point layer...")
    ReferenciaEspacial = gp.CreateSpatialReference_management("", NomeDren3D, "", "", "", "", "0")
    NomePontos = os.path.join(Textogdb , "Nodos_topograficos")
    gp.CreateFeatureclass_management(Textogdb, "Nodos_topograficos", "POINT", "", "DISABLED", "DISABLED", ReferenciaEspacial)
    gp.AddField_management(NomePontos, "RDEt", "DOUBLE")
    gp.AddField_management(NomePontos, "RDEs", "DOUBLE")
    gp.AddField_management(NomePontos, "RDEsRDEt", "DOUBLE")
    gp.AddField_management(NomePontos, "OrdemAnom", "SHORT")

    def ObterListPont(Linha):
        Feature = Linha.GetValue(CampoGeometria)
        ListaPontos = []
        ParteNum = 0
        ParteTotal = Feature.PartCount
        # Loop for each part of the feature
        while ParteNum < ParteTotal:
            Parte = Feature.GetPart(ParteNum)
            Vertice = Parte.Next()
            while Vertice:
                if Vertice:
                    # Add the coordinates of each vertex to the points list
                    ListaPontos.append([Vertice.X,Vertice.Y,Vertice.Z])
                Vertice = Parte.Next()

            ParteNum += 1
        return ListaPontos

    def Dist(x1,y1,x2,y2):
        return math.sqrt(math.pow(math.fabs(x1-x2),2)+math.pow(math.fabs(y1-y2),2))

    ConstEquidistAltimetrica = int(valor_equidis) # Contour interval
    RDEs = 0
    RDEt = 0
    XAtual = 0
    YAtual = 0
    XAnterior = 0
    YAnterior = 0
    XSegmento = 0
    YSegmento = 0
    CompSegmento = 0

    gp.AddMessage("Calculating RDE indexes...") # Knickpoint Finder

    CursorRDE = gp.SearchCursor(NomeDren3D)
    LinhaRDE = CursorRDE.Next()

    while LinhaRDE:
        import math
        ListVert = ObterListPont(LinhaRDE)

        # Calculate RDEt -> RDEt = altimetric distance between the two ends / ln( river length )
        RDEt = (ListVert[0][2] - ListVert[-1][2]) / max(0.0001, math.log( Comprimento(LinhaRDE) ) )
        XAtual = ListVert[0][0]
        YAtual = ListVert[0][1]
        XAnterior = ListVert[0][0]
        YAnterior = ListVert[0][1]
        XSegmento = ListVert[0][0]
        YSegmento = ListVert[0][1]
        PontoX = -1
        PontoY = -1
        CompSegmento = 0
        ExtNascente = 0

        ValorPixelMontante = ListVert[0][2]

        v = 0
        while v < len(ListVert):
            if RDEt < 1:
                break
            if ValorPixelMontante - ListVert[v][2] >= ConstEquidistAltimetrica/2 and PontoX == -1 and PontoY == -1:
                PontoX = ListVert[v][0]
                PontoY = ListVert[v][1]
            if ValorPixelMontante - ListVert[v][2] >= ConstEquidistAltimetrica:
                # Measure RDEs
                RDEs = ((ValorPixelMontante - ListVert[v][2]) / (CompSegmento)) * (ExtNascente)
                # Check if there is an anomaly
                if RDEs / max(0.0001, RDEt) >= 2:
                    # Create anomaly point
                    CursorPontos = gp.InsertCursor(NomePontos)
                    LinhaPonto = CursorPontos.NewRow()
                    Ponto = gp.CreateObject("Point")
                    Ponto.X = PontoX
                    Ponto.Y = PontoY
                    LinhaPonto.Shape = Ponto
                    LinhaPonto.RDEs = RDEs
                    LinhaPonto.RDEt = RDEt
                    LinhaPonto.RDEsRDEt = RDEs/max(0.0001,RDEt)
                    if RDEs / max(0.0001, RDEt) >= 2:
                        if RDEs / max(0.0001, RDEt) >= 10:
                            LinhaPonto.OrdemAnom = 1
                        else:
                            LinhaPonto.OrdemAnom = 2
                    CursorPontos.InsertRow(LinhaPonto)

                    del CursorPontos, LinhaPonto
                ValorPixelMontante = ListVert[v][2]
                CompSegmento = 0
                PontoX = -1
                PontoY = -1
            v += 1
            if v == len(ListVert) - 1:
                break
            else:
                CompSegmento += Dist(ListVert[v][0],ListVert[v][1],ListVert[v-1][0],ListVert[v-1][1])
                ExtNascente += Dist(ListVert[v][0],ListVert[v][1],ListVert[v-1][0],ListVert[v-1][1])
        LinhaRDE = CursorRDE.Next()

    # OUTPUT
    gp.MakeFeatureLayer_management(os.path.join(Textogdb,"Nodos_topograficos"), "Nodos_topograficos")
    gp.MakeFeatureLayer_management(os.path.join(Textogdb,"drenagem"), "drenagem")

    gp.AddMessage("Knickpoint Finder was successful.")
    addLayer(os.path.join(Textogdb,"Nodos_topograficos"))

def batc_points(topograf,hidrograf,Textogdb):
    arcpy.Merge_management([topograf, hidrograf], os.path.join(Textogdb,"BatchPoints"), "#")
    #capturar campos de batchpoints
    fieldInfo=""
    fieldObjList=arcpy.ListFields(os.path.join(Textogdb,"BatchPoints"))
    fieldNameList = []
    for field in fieldObjList:
        fieldNameList.append(field.name)
        fieldInfo = fieldInfo + field.name + " " + field.name + " HIDDEN;"

    arcpy.MakeFeatureLayer_management(os.path.join(Textogdb,"BatchPoints"),"Layer","#",os.path.dirname(hidrograf), fieldInfo[:-1])
    arcpy.CopyFeatures_management("Layer",os.path.join(Textogdb,"BatchPoints_F"))
    #Agregando campos para el batch points

    arcpy.AddField_management(os.path.join(Textogdb,"BatchPoints_F"), "Name", "TEXT", 9, "", "", "nombre", "NULLABLE", "REQUIRED")
    arcpy.AddField_management(os.path.join(Textogdb,"BatchPoints_F"), "Descript", "TEXT", 9, "", "", "descripcion", "NULLABLE", "REQUIRED")
    arcpy.AddField_management(os.path.join(Textogdb,"BatchPoints_F"), "BatchDone", "SHORT", 9, "", "", "hecho", "NULLABLE", "REQUIRED")
    arcpy.AddField_management(os.path.join(Textogdb,"BatchPoints_F"),"SnapOn", "SHORT", 9, "", "", "roto", "NULLABLE", "REQUIRED")
    arcpy.AddField_management(os.path.join(Textogdb,"BatchPoints_F"),"Type", "TEXT", 9, "", "", "tipo", "NULLABLE", "REQUIRED")

#Calculando los campos
    codeblock='def nom(a):\n return str(a)\n'
    expresion="nom()"

    arcpy.CalculateField_management(os.path.join(Textogdb,"BatchPoints_F"), "Name", "\"Datos Batch Points\"", "PYTHON" )
    arcpy.CalculateField_management(os.path.join(Textogdb,"BatchPoints_F"), "Descript","\"Datos Batch Points\"", "PYTHON")
    arcpy.CalculateField_management(os.path.join(Textogdb,"BatchPoints_F"), "BatchDone","\"0\"", "PYTHON")
    arcpy.CalculateField_management(os.path.join(Textogdb,"BatchPoints_F"), "SnapOn","\"0\"", "PYTHON")
    arcpy.CalculateField_management(os.path.join(Textogdb,"BatchPoints_F"), "Type", "\"Outlet\"", "PYTHON" )
    addLayer(os.path.join(Textogdb,"BatchPoints_F"))

def gen_subwatershed(puntos,dirflujo,stream_ras, Textogdb):
    ArcHydroTools.BatchSubwatershedDelineation(puntos,dirflujo,stream_ras, os.path.join(Textogdb,"SubWatershed"),os.path.join(Textogdb,"SubWatershedPoints"))
    a=os.path.join(Textogdb,"SubWatershed")
    b=os.path.join(Textogdb,"SubWatershedPoints")
    addLayer(a)
    addLayer(b)

