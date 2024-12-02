# Author: Chandler Ross | Quartic Solutions

# This is a module with miscellaneous python tools for various quartic solution needs

# Imports
from datetime import datetime, date
import time
import arcpy
import pandas as pd
import os
import sys

# ======================================================================================================================
# FUNCTIONS
# ======================================================================================================================


# TODO test this function. I have not tested it all the way through
def clean_data(fc_path, char_to_remove, tmp_path, unique_id_fld='', only_from_field='all', target_index=-1):
    """
    Takes a table and remove a specific value if the column type is a string. If you specify an index, then the
    character is removed from only that index
    :param fc_path: path to a feature class; STRING
    :param char_to_remove: character to remove from the files; STRING
    :param tmp_path: Temporary file path for processing intermediary data; STRING
    :param unique_id_fld: A unique ID field to match the records. Often GlobalID should be used. If 'none' then a
    Truncate and append operation will be performed on the table
    :param only_from_field: Only will remove the character from a single field
    :param target_index: Index where the character should be removed from; STRING
    :return:
    """

    # Make sure for Versioned datasets that a unique ID field is chosen
    is_versioned = arcpy.Describe(fc_path).isVersioned
    if is_versioned:  # If versioned
        if unique_id_fld == '':
            print('Need to choose a unique_id_fld for versioned datases, it cannot be blank. Exiting the program now.')
            sys.exit()

    # 1 Read a feature class and export to csv
    # Check to see if the path exists, if not then make the path
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    csv_name = 'fc_csv.csv'
    csv_path = os.path.join(tmp_path, csv_name)
    # Check if the file exists
    if os.path.exists(csv_path):
        # Check if it's a file (not a directory)
        if os.path.isfile(csv_path):
            os.remove(csv_path)
    # Check the pro version because arc works differently with different tools
    pro_version = arcpy.GetInstallInfo()['Version']

    # Depending on the pro version change the following code
    if int(pro_version[0]) >= 3 and int(pro_version[2]) > 1:  # Make sure 3.2 or later
        # Keep the GlobalIDs in the output data without permanently changing the settings
        with arcpy.EnvManager(preserveGlobalIds=True):
            arcpy.conversion.ExportTable(in_table=fc_path, out_table=csv_path)  # Doesn't work with pro 3.1.1
    # Use the old tool for Old pro
    elif pro_version[0] == '2' or (pro_version[0] == '3' and int(pro_version[2]) < 2):
        if unique_id_fld == 'GlobalID':
            print('GlobalID cannot be preserved with the old version of Pro. Try finding another unique field Ending '
                  'the process now.')
            sys.exit()
        else:
            arcpy.conversion.TableToTable(in_rows=fc_path, out_path=tmp_path, out_name=csv_name)
    else:
        print('The ArcGIS Pro will not allow this tool to work. Ending the process now.')
        sys.exit()

    # 2 Read the csv as a pandas df
    df = pd.read_csv(csv_path)

    # 3 Make the change to the df and note which fields have been changed
    if only_from_field == 'all':
        # Get a list of columns that are string/text type
        columns_to_check = []
        fc_field_list = list_fields(fc_path=fc_path, include_type=True)
        for fld in fc_field_list:
            if fld[1] == 'String':
                columns_to_check.append(fld[0])
    else:
        columns_to_check = [only_from_field]

    # The result of this if else will be a dictionary of which columns changed for the ID field. The difference will be
    # if there is an index or not
    if target_index == -1:  # TODO test if this if works
        # Dictionary to track changes per column
        changed_ids_per_column = {col: [] for col in columns_to_check}

        # Iterate over each column and modify
        for col in columns_to_check:
            # Identify rows where the character exists
            changed_rows = df[col].str.contains(char_to_remove, na=False)

            # Update the column values by removing the character
            df[col] = df[col].str.replace(char_to_remove, '', regex=False)

            # Add IDs of changed rows to the dictionary for this column
            changed_ids_per_column[col] = df.loc[changed_rows, unique_id_fld].tolist()

    else:  # TODO this runs, but not sure if works properly
        # Dictionary to track changes per column
        changed_ids_per_column = {col: [] for col in columns_to_check}  # Format: {'column1': [ID val1, ID val2]}

        # Iterate over each column and modify
        for col in columns_to_check:
            changed_rows = df[col].apply(
                lambda x: isinstance(x, str) and len(x) > target_index and x[target_index] == char_to_remove
                if pd.notna(x) else False
            )
            # Update the column values
            df[col] = df[col].apply(
                lambda x: x[:target_index] + x[target_index + 1:]
                if isinstance(x, str) and len(x) > target_index and x[target_index] == char_to_remove else x
            )
            # Add IDs of changed rows to the dictionary for this column
            changed_ids_per_column[col] = df.loc[changed_rows, unique_id_fld].tolist()

    print(changed_ids_per_column)  # TODO temporary testing line, delete after finished
    df.to_csv('C:\\Users\\rossc\\Downloads\\changed_df_112224.csv', index=False)  # TODO temporary testing line, delete after finished
    '''
    # 4 Apply the change to the feature class
    if unique_id_fld == '':
        # TODO: do a truncate and append since no unique field (does not work for versioned feature classes)
        pass
    else:
        # Use the pointer to change that field
        # loop through the columns
        for col, id_list in changed_ids_per_column.items():
            try:
                with arcpy.da.UpdateCursor(fc_path, [unique_id_fld, col]) as cursor:
                    for row in cursor:  # For each row in table
                        # Check if this rows idfield_update is in the dict that matches to idfield_read
                        if row[0] in id_list:
                            # If so, get the new column value from the df based on the corresponding id value and update
                            # the fc
                            row[1] = df.loc[df[unique_id_fld] == row[0], col].iloc[0]
                            cursor.updateRow(row)  # "Save" the update
            except Exception as e:
                print(e)
                pass
        pass
    '''


def drop_users(ws):
    arcpy.DisconnectUser(ws, 'ALL')
    print('Users have been disconnected')


def db_connect(envt, db_path, db_base, db_name, feature_class, feature_dataset=False):
    """
    Connects to a file to the Atlas or Atlas Edit DB
    :param db_path: path to the file;STRING
    :param db_base: the db path name, EX: "TSW@ATLAS-EDITDEV@";STRING
    :param db_name: The name of the DB, EX: TSWEDITDEV.sde"; STRING
    :param feature_class: The feature class name; STRING
    :param feature_dataset: FD name; STRING
    :return: the feature class of the database
    """
    # Connect the files
    env = envt.upper()
    db_info = db_base + db_name
    new_path = os.path.join(db_path, env)
    db = os.path.join(new_path, db_info)
    db_split = db_base.split("@")
    if feature_dataset:
        folder = '\\' + db_name[:-4] + "." + db_split[0] + "." + feature_dataset
    else:
        folder = ""
    out_name = '\\' + db_name[:-4] + "." + db_split[0] + "." + feature_class
    out_path = db + folder + out_name
    return out_path


def list_fields(fc_path, include_type=False):
        """
        Returns a list of field names and types in the feature class.
        :param fc_path: path to a feature class; STRING
        :param include_type: True gives name and type, False is just name; Bool
        :return: list of columns
        """
        fields = arcpy.ListFields(fc_path)
        if include_type:
            ret_list = []
            for field in fields:
                name_list = [field.name, field.type]
                ret_list.append(name_list)
            return ret_list
        else:
            return [field.name for field in fields]


def load_data(fc_path, csv_file, field_to_update, field_to_read, idfield_update, idfield_read):
    """
    Traditionally, how a data load would work is you would join the update table to the feature class on a PK-FK
    connection. Then you would reclaculate the target field from the FC to the update field from the update table.
    How this works is it uses the update cursor to write fields from the csv to the fc. It is much faster than
    joining the fields, calculating, and removing the join. Also avoids the pitfalls from dealing with versioned
    data that cannot deal with schema changes easily.
    :param fc_path: Path of the Feature Class to update; STRING
    :param csv_file: csv file path for the new data to be updated; STRING
    :param field_to_update: Name of the field that will be updated in the feature class; STRING
    :param field_to_read: Name of the field that contains the new data from the csv; STRING
    :param idfield_update: Name of the Primary Key that will connect the proper records of the fc to the csv; STRING
    :param idfield_read: Name of the Foreign Key that will connect the proper records of the csv to the fc; STRING
    :return:
    """
    # Set the workspace for where the edit will take place
    workspace = os.path.dirname(fc_path)
    edit = arcpy.da.Editor(workspace)  # Edit workspace
    edit.startEditing(False, True)  # args: with_undo, multiuser
    edit.startOperation()  # Start the editing
    try:
        # Create a dictionary for the field records that will be updated. The key is the id field and the value is
        #  update field
        d = {k: v for k, v in arcpy.da.SearchCursor(csv_file, [idfield_read, field_to_read])}
        # Method 1
        with arcpy.da.UpdateCursor(fc_path, [idfield_update, field_to_update]) as cursor:
            # Method 2
            # with uc_wrapper.UpdateCursor(shape_to_update, [idfield_update, field_to_update]) as cursor:
            # Opened the cursor

            for row in cursor:  # For each row in table
                if row[0] in d:  # Check if this rows idfield_update is in the dict that matches to idfield_read
                    row[1] = d[row[0]]  # If so, update field_to_update to be field_to_read
                    cursor.updateRow(row)  # "Save" the update
    except Exception as e:
        edit.abortOperation()
        print(f"Error: {str(e)}")
    else:
        print('Stopping the Operation')
        edit.stopOperation()
        print('Stop the Editing')
        edit.stopEditing(save_changes=True)  # True to save edits, False to discard


def new_coded_domain(sde_connection, domain_name, code_values, field_type='TEXT', new_dom_desc=''):
    """
    Makes a new coded domain and adds values to it
    :param sde_connection: file path to the sde; STRING
    :param domain_name: Name of the new domain; STRING
    :param code_values: dictionary of the coded values; STRING
    :param field_type: field type for the domain to be used on, default is TEXT; STRING
    :param new_dom_desc: description for the domain, if none is given none will be added; STRING
    :return:
    """
    # Make the domain
    if new_dom_desc == '':
        arcpy.management.CreateDomain(in_workspace=sde_connection, domain_name=domain_name,
                                      domain_description=domain_name, field_type=field_type, domain_type='CODED')
    else:
        arcpy.management.CreateDomain(in_workspace=sde_connection, domain_name=domain_name,
                                      domain_description=new_dom_desc, field_type=field_type, domain_type='CODED')

    # Add values to the domain
    for code in code_values:
        arcpy.management.AddCodedValueToDomain(sde_connection, domain_name, code, code_values[code])


def set_domain_to(sde_connection, domain_name, code_values, temp_table_path='./out.csv'):
    """
    Changes the domain to be in the order of the code_values
    :param sde_connection: SDE  connection of where the domain lives; STRING
    :param domain_name: Name of the domain to change; STRING
    :param code_values: dictionary of codes and values for the domain; DICTIONARY
    :param temp_table_path: Temporary path in order to be able to read the table
    :return:
    """
    # Get a list of the domain codes by turning the domain into a table then read the table into a list
    # make a table
    arcpy.management.DomainToTable(in_workspace=sde_connection, domain_name=domain_name, out_table=temp_table_path,
                                   code_field='code', description_field='desc')

    # read the table as a pandas df
    df = pd.read_csv(out_table)

    # make the value into a list
    codes = df[code_field].tolist()

    # delete the codes from the domain
    arcpy.management.DeleteCodedValueFromDomain(in_workspace=sde_connection, domain_name=domain_name, code=codes)

    # Delete the temporary table
    if os.path.exists(temp_table_path):
        os.remove(temp_table_path)
        print(f"{temp_table_path} has been deleted.")
    else:
        print(f"{temp_table_path} does not exist.")

    # Add the desired coded values to the domain
    for code in code_values:
        arcpy.management.AddCodedValueToDomain(in_workspace=sde_connection, domain_name=domain_namedomain_name,
                                               code=code, code_description=code_values[code])


def workspace_connect(envt, db_path, db_base, db_name):
    """
    Connects to a file to the Atlas or Atlas Edit DB
    :param envt: "DEV", "QA", or "PROD" environment being used; STRING
    :param db_path: path to the file; STRING
    :param db_base: the db path name, EX: "TSW@ATLAS-EDITDEV@"; STRING
    :param db_name: The name of the DB, EX: TSWEDITDEV.sde"; STRING
    :return: the workspace path
    """
    db_info = db_base + db_name
    new_path = os.path.join(db_path, envt)
    db = os.path.join(new_path, db_info)
    return db


def delay_until(start_time):
    '''
    This functions waits until the time and date called in order to resume the script. Assumes that the time set is in the future.
    :param start_time: The time and date you want to delay until in mm/dd/yy hh:mm format, example: '09/19/22 13:55'; String
    :return:
    '''

    # Get the current time
    now = datetime.now()

    # Convert the start time to a time object
    datetime_object = datetime.strptime(start_time, '%m/%d/%y %H:%M')

    # Get the date of now
    now_date = date(now.year, now.month, now.day)

    # Get the date of the start time
    start_date = date(datetime_object.year, datetime_object.month, datetime_object.day)

    # Get the difference between the start_date and the now_date
    date_delta = start_date - now_date

    if(date_delta.days > 1):
        #Calculate th amount of time until the end of the day
        # Get the time of day for the start time
        now_hour = now.hour
        now_minute = now.minute

        # time until end of day
        hours_left = (23 - now_hour) * 60
        minutes_left = 59 - now_minute
        minutes_of_day = hours_left + minutes_left

        #Get the amount of time for the start_time
        start_hour = datetime_object.hour * 60
        start_minute = datetime_object.minute
        start_sum = start_minute + start_hour

        # Get the number of days
        day_minutes = (date_delta.days - 1) * 24 * 60

        wait_time = minutes_of_day + start_sum + day_minutes
        print(f"Waiting for {wait_time} minutes")
        time.sleep(wait_time * 60)

    elif(date_delta.days > 0):
        # Calculate th amount of time until the end of the day
        # Get the time of day for the start time
        now_hour = now.hour
        now_minute = now.minute

        # time until end of day
        hours_left = (23 - now_hour) * 60
        minutes_left = 59 - now_minute
        minutes_of_day = hours_left + minutes_left

        # Get the amount of time for the start_time
        start_hour = datetime_object.hour * 60
        start_minute = datetime_object.minute
        start_sum = start_minute + start_hour

        # Get the wait time
        wait_time = minutes_of_day + start_sum
        print(f"Waiting for {wait_time} minutes")
        time.sleep(wait_time * 60)

    else:
        # Get the time of day for the now
        now_hour = now.hour
        now_minute = now.minute

        # Get the time of day for the start time
        start_hour = datetime_object.hour
        start_minute = datetime_object.minute

        delta_hour = start_hour - now_hour
        delta_minute = start_minute - now_minute

        wait_time = (delta_hour * 60) + delta_minute
        print(f"Waiting for {wait_time} minutes")
        time.sleep(wait_time * 60)


if __name__ == '__main__':
    fcp = "Z:\\Development\\db_connections\\DEV\\TSW@ATLAS-EDITDEV@TSWEDITDEV.sde\\TSWEDITDEV.TSW.UUP_PTE"
    clean_data(fc_path=fcp, char_to_remove='"', tmp_path='C:\\temp\\tmp_tools', unique_id_fld='GlobalIDTemp',
               only_from_field='PTE_NOTES', target_index=0)
    # First Run: unique_id_fld='' so should fail  # Successfuly exited the script
    # Second Run: only_from_field='PTE_NOTES', target_index=0  #
    # Third Run: only_from_field='PTE_NOTES', target_index=-1  #
    # Fourth Run: only_from_field='all', target_index=0  #
    # Fifth Run: only_from_field='all', target_index=-1  #
    pass
