# This is a script that is made to replace arcpy functions with GDAL ones so it works

'''
List of arcpy functions to be replaced
Y arcpy.Exists()
    - Can be replaced by the non OGR function os.path.isfile()
Y arcpy.management.Delete()
Y arcpy.management.Copy()
N arcpy.management.MakeFeatureLayer()
    - This is not necessary, I may drop this aspect at the risk of performance
arcpy.management.SelectLayerByAttribute()
    - I can think of a way to do this with pandas
Y arcpy.management.CopyFeatures()
    - Would be easy with geopandas
    - Did a simple version with fiona
arcpy.in_workspace #I think this can be replaced with a set environ
arcpy.management.AddSpatialIndex()
arcpy.management.AddIndex()
arcpy.ListFeatureClasses()
    - I can replace this by looking at the names
Y arcpy.management.GetCount()
M arcpy.da.UpdateCursor()
arcpy.management.CalculateField()
    - Geopandas can do this
arcpy.management.Append()
'''

#=======================================================================================================================
# Imports
#=======================================================================================================================
from osgeo import ogr
import os
import pandas as pd
import shutil
import sys
import fiona
import geopandas as gpd
#=======================================================================================================================
# FUNCTIONS
#=======================================================================================================================
def read_shp(shp_path):
    """
    Takes a shapefile and outputs a layer that can be manipulated
    :param shp_path: Shapefile file path; STRING
    :return:
    """
    pass


def get_layer(in_shp, write, driver_name="ESRI Shapefile"):
    """
    Gets the layer in GDAL, this will help with
    :param in_shp: Shapefile file path; STRING
    :param write: True if you want to write the shp; BOOL
    :param driver_name: driver name; STRING
    :return: OGR layer object
    """
    driver = ogr.GetDriverByName(driver_name)
    if(write):
        data_source = driver.Open(in_shp, 1)
    else:
        data_source = driver.Open(in_shp, 0)
    layer = data_source.GetLayer()
    return layer


def delete_shp(in_shp, driver_name="ESRI Shapefile"):
    """
    Delete a shapefile
    :param in_shp: Shapefile to delete; STRING
    :param driver: Driver to register the data; STRING
    :return:
    """
    driver = ogr.GetDriverByName(driver_name)
    if os.path.exists(in_shp):
        driver.DeleteDataSource(in_shp)


def iterate_rows(in_shp, col_name, write, driver_name="ESRI Shapefile"):
    """
    WIP, just goes through the rows rn
    :param in_shp: Shapefile file path; STRING
    :param col_name: name of the column; STRING
    :param write: True if you want to write the shp; BOOL
    :param driver_name: driver name; STRING
    :return:
    """
    layer = get_layer(in_shp, write, driver_name)
    for feature in layer:
        print(feature.GetField(col_name))
    layer.ResetReading()


def get_count(in_shp, driver_name="ESRI Shapefile"):
    """
    Gets the count of # of rows in a file
    :param in_shp: Shapefile file path; STRING
    :param driver_name: driver name; STRING
    :return: number of rows in the shapefile
    """
    layer = get_layer(in_shp, False, driver_name)
    num_features = layer.GetFeatureCount()
    return num_features


def copy(in_path, in_file_name, out_path, out_file_name):
    """
    Copies a shapefile from one location to another
    :param in_path: path where the file lives
    :param in_file_name: file name without an extenstion
    :param out_path: out file path folder
    :param out_file_name: out file name without an extension
    :return:
    """
    print(os.listdir(in_path))
    for file in os.listdir(in_path):
        file_list = file.split(".")
        # Get the file extensions
        tmp_copy_value = out_file_name
        in_file_name_ext = in_file_name
        for val in file_list[1:]:
            tmp_copy_value = tmp_copy_value + "." + val
            in_file_name_ext = in_file_name_ext + "." + val
        if (in_file_name==file_list[0]):
            shutil.copy(os.path.join(in_path, in_file_name_ext), os.path.join(out_path, tmp_copy_value))


def copy_features(in_shp, out_shp, col, value):
    """
    Copies selected features to a new shapefile. However, it only allows for a single feature to be selected
    :param in_shp:
    :param out_shp:
    :param col:
    :param value:
    :return:
    """
    '''
    This only works when there are selections from a single col. If multiple columns want to be added, then I will 
    need to add the or/and keywords and make multiple for loops with different criteria. 
    '''
    with fiona.open(in_shp) as source:
        source_schema = source.schema
        source_driver = source.driver
        source_crs = source.crs
        # print(source_schema)  # attribute fields & geometry def as dict
        # print(source_driver)  # "ESRI Shapefile"
        # print(source_crs)  # coordinate system
        with fiona.open(out_shp, 'w',
                        driver=source_driver,
                        crs=source_crs,
                        schema=source_schema) as shp_out:
            for feature in source:
                for val in value:
                    if(feature["properties"][col] == val):
                        shp_out.write(feature)
    # if(os.path.isfile(os.path.splitext(in_shp)[0] + ".prj")):
    #     shutil.copy(os.path.splitext(in_shp)[0] + ".prj", os.path.splitext(out_shp)[0] + ".prj")


def calculate_field(in_shp, out_shp, expression):
    pass


def custom_geoscopes_function(in_shp, out_shp):
    pass


"""
I want to replace these lines with a custom function

arcpy.management.SelectLayerByAttribute(fl_parcels_layer, "NEW_SELECTION",
                                                ' "PARCEL_POL" = ' + str(parcel_polygon_id))

        result = arcpy.management.GetCount(fl_parcels_layer)
        count_selected = int(result[0])

        # print("\n")
        # print("Number of parcels selected:  " + str(count_selected))

        if (count_selected > 0):
            arcpy.management.CalculateField(fl_parcels_layer, "JOB_LOC_ID", job_location_id, "PYTHON")

            # ----------------------------------------------------------------
            # Append the selected parcel polygon to the storm water locations
            # layer
            # ----------------------------------------------------------------

            arcpy.management.Append(fl_parcels_layer, fl_job_locations_layer, "TEST")

"""


if __name__ == "__main__":
    pass
