# Author: Chandler Ross | Quartic Solutions
# DSD Tools is made to be a module to help automate the DSD workflows

#----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------
# Imports
#----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------

import arcpy
import os

#----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------
# Functions
#----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------


# Atlas Refresh
def altas_refresh(in_shp, new_field_1, new_field_2, nf1_value, nf2_value, txt_path, nf1_type='TEXT', nf2_type='TEXT',
                  nf1_precision=60, nf2_precision=254, add_txt=False):
    """
    This function adds two new fields (Work In Progress)
    :param in_shp: Input shapefile to be modified for the refresh
    :param new_field_1: New field to be created; String
    :param new_field_2: New field to be created; String
    :param nf1_value: The value for new_field_1 to be equal to; String
    :param nf2_value: The value for new_field_2 to be equal to; String
    :param txt_path: the path to a text file to add the message; String
    :param nf1_type: The type of field for new_field_1; String
    :param nf2_type: The type of field for new_field_2; String
    :param nf1_precision: The precision for new_field_1; String
    :param nf2_precision: The precision for new_field_2; String
    :param add_txt: Determins if you want to add a message to the readme; Bool
    :return: A ...
    """
    # try statement that uses pandas since it is faster than arcpy
    # If pandas is not available then arcpy will be used
    try:
        import geopandas as gpd
        # Read in the shapefile
        gdf = gpd.read_file(in_shp)

        # Add the new fields and set it equal to another field
        gdf = gdf.assign(new_field_1=gdf[nf1_value])
        gdf = gdf.assign(new_field_2=gdf[nf2_value])

        # Change the type and percision for the new columns
        convert_dict = {new_field_1: str, new_field_2: str} # make a change dictionary so both are strings
        gdf = gdf.astype(convert_dict)

        # Write the geodataframe to an output shapefile
        gdf.to_file(in_shp) # TODO Check to see if it properly overwrites the file with the new data
        
    except:
        # Use arcpy to add the new fields if geopandas is unavailable
        arcpy.management.AddField(in_shp, new_field_1, nf1_type, nf1_precision)
        arcpy.management.AddField(in_shp, new_field_2, nf2_type, nf2_precision)

        # add the values for the fields
        # Make the expression for nf1
        expression1 = "!" + nf1_value + "!"
        # Calculate nf1
        arcpy.management.CalculateField(in_shp, new_field_1, expression1, expression_type="PYTHON3")
        # Make the expression for nf2
        expression2 = "!" + nf2_value + "!"
        # Calculate nf2
        arcpy.management.CalculateField(in_shp, new_field_2, expression2, expression_type="PYTHON3")


def add_field(in_shp, new_field, nf_value, nf_type, nf_precision):
    """

    :param in_shp: Input shapefile to get a new field
    :param new_field:
    :param nf_value:
    :param nf_type:
    :param nf_precision:
    :return:
    """
    pass

def calc_field():
    pass

def dsd_data_check(envt, layer):
    """
    This function checks for if the DSD data exists anywhere else
    :parameter envt: The Atlas environment to check; String
    :parameter layer: The layer to look for; String
    :return: Prints location of duplicates
    """
    arcpy.env.workspace = envt
    print("Searching for duplicates, may take awhile")
    for dirpath, dirnames, filenames in arcpy.da.Walk():
        if layer.lower() in [z.lower() for z in filenames]:
            if(dirpath == os.path.join(envt, 'SDW.CITY.DSD')):
                print('Found in DSD, looking for other locations')
            else:
                print(dirpath)
                break
    print('No duplicates!')


if __name__ == '__main__':

    # EXAMPLES
    dsd_data_check(envt=r'\\kdc-nas1\GIS-HOME$\Workspace\rossc\Temp\database_lookup\CITY@ALTAS@SDW.sde',
                   layer='SDW.CITY.parking_standards_transit_priority_areas')

