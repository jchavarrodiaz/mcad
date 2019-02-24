import os
import arcpy
from itertools import combinations, chain
import pandas as pd


def save_mxd():
    mapdoc = arcpy.mapping.MapDocument('CURRENT')
    mapdoc.save()


def calculate_grouped_field(layer, fields):
    """ This function calculate grouped field of designed fields"""
    arcpy.AddField_management(layer, "new_class", "TEXT")
    new_class_field = "new_class"
    fields.append(new_class_field)
    with arcpy.da.UpdateCursor(layer, fields) as class_field_rows:
        for s_row in class_field_rows:
            s_row[-1] = "_".join(s_row[0:-1])
            class_field_rows.updateRow(s_row)
        del s_row
    fields = fields[:-1]
    print fields


def unique_values(layer, fields, f_types, id):
    """ This function extract list of list with unique values by field """
    gdb_path = os.path.dirname(os.path.abspath(layer))
    arcpy.env.workspace = '{}'.format(os.path.dirname(os.path.abspath(gdb_path)))
    arcpy.env.overwriteOutput = True
    arcpy.env.qualifiedFieldNames = False
    temp_folder = r'{}\temp'.format(os.path.dirname(os.path.abspath(gdb_path)))

    unique_value_fields = list()
    numeric_fields = []

    for field in fields:
        if any(f_types[field] in s for s in [u'Double', u'Float', u'Long', u'Short']):
            numeric_fields.append(field)

    if len(numeric_fields) != 0:
        arcpy.TableToExcel_conversion(layer, os.path.join(temp_folder, 'UTTL_Cluster.xls'))
        df_num_table = pd.ExcelFile(os.path.join(temp_folder, 'UTTL_Cluster.xls')).parse('UTTL_Cluster', index_col=id)[numeric_fields]
        reclass_table = df_num_table.quantile([0.05, 0.25, 0.40, 0.60, 0.95], axis=0)
        ls_re_name = []
        for num_field in numeric_fields:
            re_name = 'r_{}'.format(num_field)[:10]
            df_num_table[re_name] = None
            df_num_table.ix[df_num_table[df_num_table[num_field] <= reclass_table.ix[0.05, num_field]].index, re_name] = 'Muy Bajo'
            df_num_table.ix[df_num_table[(df_num_table[num_field] > reclass_table.ix[0.05, num_field]) & (df_num_table[num_field] <= reclass_table.ix[0.25, num_field])].index, re_name] = 'Bajo'
            df_num_table.ix[df_num_table[(df_num_table[num_field] > reclass_table.ix[0.25, num_field]) & (df_num_table[num_field] <= reclass_table.ix[0.40, num_field])].index, re_name] = 'Medio Bajo'
            df_num_table.ix[df_num_table[(df_num_table[num_field] > reclass_table.ix[0.40, num_field]) & (df_num_table[num_field] <= reclass_table.ix[0.60, num_field])].index, re_name] = 'Medio'
            df_num_table.ix[df_num_table[(df_num_table[num_field] > reclass_table.ix[0.60, num_field]) & (df_num_table[num_field] <= reclass_table.ix[0.95, num_field])].index, re_name] = 'Alto'
            df_num_table.ix[df_num_table[df_num_table[num_field] > reclass_table.ix[0.95, num_field]].index, re_name] = 'Muy Alto'
            ls_re_name.append(re_name)

        df_num_table.index = df_num_table.index.map(str)
        df_num_table.index.name = id
        df_num_table[ls_re_name].to_excel(os.path.join(temp_folder, 'UTTL_Cluster_Reclass.xls'), 'UTTL_Cluster_Reclass')
        arcpy.ExcelToTable_conversion(os.path.join(temp_folder, 'UTTL_Cluster_Reclass.xls'), os.path.join(temp_folder, 'numericfieldsreclass'), 'UTTL_Cluster_Reclass')
        arcpy.MakeFeatureLayer_management(layer, 'Layer')
        arcpy.AddJoin_management('Layer', id, os.path.join(temp_folder, 'numericfieldsreclass'), id)

        arcpy.CopyFeatures_management('Layer', os.path.join(temp_folder, 'UTTL_Basins_Reclas_NumericFields.shp'))
        arcpy.DeleteField_management(os.path.join(temp_folder, 'UTTL_Basins_Reclas_NumericFields.shp'), ['Shape_Leng', 'Shape_Area', 'Rowid_', '{}_1'.format(id)])
        arcpy.DeleteFeatures_management(layer)
        arcpy.CopyFeatures_management(os.path.join(temp_folder, 'UTTL_Basins_Reclas_NumericFields.shp'), layer)

        [fields.remove(i) for i in numeric_fields]
        [fields.append(str.upper(i)) for i in ls_re_name]

    for field in fields:
        with arcpy.da.SearchCursor(layer, [field]) as cursor:
            a = sorted({row[0] for row in cursor})
            my_set = set(a)  # For real unique values
            my_new_list = list(my_set)

        unique_value_fields.append(my_new_list)

    return unique_value_fields, fields


def combine(t_class, prefix):
    """ This function generate all combinations between unique values in all fields """
    unique_class = chain.from_iterable(t_class)
    combined_list = list(combinations(unique_class, len(t_class)))
    final_clases = dict()
    conunt = 0
    combined_list = [elem for elem in combined_list if len(elem) == len(t_class)]
    for i, j in zip(combined_list, range(len(combined_list))):
        if len(i) == len(t_class):
            final_clases['{}-{}'.format(prefix, j)] = "_".join(i)
    return final_clases


def assign_class(layer, t_class, prefix):
    """ assign the classes consecutively """
    arcpy.AddField_management(layer, "classified", "TEXT")
    fields = ["new_class", "classified"]
    class_accept = list()
    with arcpy.da.UpdateCursor(layer, fields) as class_field_rows:
        for s_row in class_field_rows:
            if s_row[0] in t_class.values():
                s_row[-1] = t_class.keys()[t_class.values().index(str(s_row[0]))]
                class_accept.append(t_class.keys()[t_class.values().index(str(s_row[0]))])
            class_field_rows.updateRow(s_row)
        del s_row
    class_accept = set(class_accept)
    arcpy.AddMessage("Clases Potenciales: " + str(len(t_class)))
    arcpy.AddMessage("Clases Encontradas: " + str(len(class_accept)))

    arcpy.AddField_management(layer, "TIPOLOGIA", "TEXT")
    fields = ["classified", "TIPOLOGIA"]
    with arcpy.da.UpdateCursor(layer, fields) as class_field_rows:
        for s_row in class_field_rows:
            for c, j in zip(class_accept, range(len(class_accept))):
                if s_row[0] == c:
                    s_row[-1] = '{}-{}'.format(prefix, j)
            class_field_rows.updateRow(s_row)
        del s_row
    arcpy.DeleteField_management(layer, "new_class;classified")


def main(env):
    if env:
        uttl = arcpy.GetParameterAsText(0)
        cluster_fields = arcpy.GetParameterAsText(1)
        id_uttl = arcpy.GetParameterAsText(2)
        prefix = arcpy.GetParameterAsText(3)

        save_mxd()

        ls_cluster_fields = cluster_fields.split(";")
        ls_dict = [{i.name: i.type} for i in arcpy.ListFields(uttl)]
        field_types = {}
        for d in ls_dict:
            field_types.update(d)

        unival, update_field_list = unique_values(uttl, ls_cluster_fields, field_types, id_uttl)
        calculate_grouped_field(uttl, update_field_list)
        combine_values = combine(unival, prefix)
        assign_class(uttl, combine_values, prefix)

    else:
        uttl = r'C:\Users\jchav\AH_01\CATATUMBO\results\UTTL.gdb\UTTL_Basins'  # UTTL Polygons
        cluster_fields = 'FloresNew;Qmax_Class;BeechieNew;Lang_Class;regimen'
        id_uttl = u'Name'
        prefix = u'CT'

        ls_cluster_fields = cluster_fields.split(";")
        ls_dict = [{i.name: i.type} for i in arcpy.ListFields(uttl)]
        field_types = {}
        for d in ls_dict:
            field_types.update(d)

        unival, update_field_list = unique_values(uttl, ls_cluster_fields, field_types, id_uttl)
        calculate_grouped_field(uttl, update_field_list)
        combine_values = combine(unival, prefix)
        assign_class(uttl, combine_values, prefix)


if __name__ == '__main__':
    main(env=True)
