# Author: Chandler Ross | Quartic Solutions
# DSD Tools is made to be a module to help automate the DSD workflows

#----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------
# Imports
#----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------

import arcpy

#----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------
# Functions
#----------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------



# Atlas Refresh
def altas_refresh(in_shp, new_field_1, new_field_2, nf1_value, nf2_value, txt_path, nf1_type='TEXT', nf2_type='TEXT',
                  nf1_precision=60, nf2_precision=254, add_txt=False):
    """
    This function adds two new fields 
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
        
    except:
        # Use arcpy to add the new fields
        arcpy.management.AddField(in_shp, new_field_1, nf1_type, nf1_precision)
        arcpy.management.AddField(in_shp, new_field_2, nf2_type, nf2_precision)

        # add the values for the fields
        # Make the expression for nf1
        expression1 = "!" + nf1_value + "!"
        # Calculate nf1
        arcpy.management.CalculateField(in_shp, new_field_1, expression1, expression_type="PYTHON3")
        # Make the expression for nf2
        expression1 = "!" + nf2_value + "!"
        # Calculate nf2
        arcpy.management.CalculateField(in_shp, new_field_2, expression1, expression_type="PYTHON3")


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


