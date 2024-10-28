# Author: Chandler Ross | Quartic Solutions

# This is a module with miscellaneous python tools for various quartic solution needs

# Imports
from datetime import datetime, date
import time
import arcpy
import pandas as pd
import os


#=======================================================================================================================
# CLASSES
#=======================================================================================================================


# Create a class that represents a feature class
class FC:
    def __init__(self, path):
        self.path = path
        self.describe = arcpy.Describe(path)
        self.name = self.describe.name
        self.spatial_reference = self.describe.spatialReference
        self.shape_type = self.describe.shapeType

        # See if the path is valid
        if not arcpy.Exists(self.path):
            raise ValueError(f"The feature class at {self.path} does not exist.")

    def get_feature_count(self):
        """Returns the number of features in the feature class."""
        return arcpy.management.GetCount(self.path)[0]

    def list_fields(self, include_type=False):
        """Returns a list of field names and types in the feature class.
        param include_type: True gives name and type, False is just name; Bool
        """
        fields = arcpy.ListFields(self.path)
        if include_type == True:
            return [f'Name: {field.name}, Type: {field.type}' for field in fields]
        else:
            return [field.name for field in fields]

    def generate_schema_report(self, print_report=None, *args):
        """
        Generates a schema report that can be a pandas table or exported to a csv
        :param print_report: Output location and name to print the csv file. If none will make the output a pandas df
                             ; STRING
        :param args: Which fields to be chosen for the report and in the order. Options include: name, aliasName,
                     defaultValue, domain, editable, isNullable, length, precision, required, type; STRING
        :return: report DF if no output location is chosen
        """
        fields = arcpy.ListFields(self.path)
        field_list = []
        cols = []
        for arg in args:
            cols.append(arg)
            mini_list = []
            for field in fields:
                value = getattr(field, arg, "N/A")
                mini_list.append(value)
            field_list.append(mini_list)
        #make a dict to make the df
        data_dict = {}
        for i in range(len(cols)):
            data_dict[cols[i]] = field_list[i]
        # Make the data frame with the information
        df = pd.DataFrame(data_dict)
        if print_report:  # Checks if it is None
            df.to_csv(print_report, index=False)
        else:
            return df


# Make a child class that supports versioning
class VersionedFC(FC):
    def __init__(self, path):
        """
        Initializes a connection to the specified geodatabase with versioning support.
        :param path: Path to the geodatabase.
        """
        super().__init__(path)  # Initialize the parent class
        self.current_version = 'sde.DEFAULT'  # Default version

    # private function to return the path of the sde
    def _get_sde(self):
        """
        Extracts the path to the SDE file from a full feature class path.
        :return: The path to the SDE file.
        """
        # Find the index of the '.sde' and extract everything before and including it
        sde_index = self.path.lower().find('.sde')

        if sde_index != -1:
            # Include up to and including the '.sde'
            sde_path = self.path[:sde_index + 4]
            return sde_path
        else:
            raise ValueError("The provided path does not contain an .sde file.")

    def get_current_version(self):
        """Returns the current version."""
        return self.current_version

    def list_versions(self):
        """
        Lists all available versions in the geodatabase.
        :return: A list of version names.
        """
        sde_path = self._get_sde()
        versions = arcpy.da.ListVersions(sde_path)
        return [v.name for v in versions]

    def list_permitted_versions(self):
        """
        Lists all versions the user is permitted to use in the geodatabase.
        :return: A list of version names.
        """
        sde_path = self._get_sde()
        versions = arcpy.ListVersions(sde_path)
        return [v for v in versions]

    # I have yet to test this code
    def reconcile_and_post(self, target_version):
        """
        Reconciles and posts changes from the current version to the target version.
        :param target_version: The version to post changes to (e.g., 'sde.DEFAULT').
        """
        try:
            # Reconcile versions
            arcpy.management.ReconcileVersions(
                self.path,  # Geodatabase path
                'ALL_VERSIONS',  # Reconcile with all versions
                self.current_version,  # Current version
                target_version,  # Target version to reconcile with
                'BY_OBJECT',  # Conflict resolution: by object
                'FAVOR_EDIT_VERSION',  # Favor the edit version for conflicts
                'LOCK_ACQUIRED',  # Acquire locks during the operation
                'NO_ABORT',  # Do not abort if conflicts found
                'NO_POST',  # Do not automatically post after reconciliation
                'KEEP_VERSION',  # Keep the version after reconcile
            )

            print(f"Reconcile of {self.current_version} with {target_version} completed successfully.")

            # Post the changes to the target version
            arcpy.management.PostVersion(self.path, self.current_version, target_version)
            print(f"Changes from {self.current_version} posted to {target_version}.")

        except Exception as e:
            print(f"Error during reconcile and post: {e}")


# Child class that can make Schema changes
# Use a Dynamic Composition method to use either the FC or VersionedFC classes as the parent
class SchemaChangeFC:
    def __init__(self, dynamic_parent):
        self.parent_instance = dynamic_parent

    def delegate_method(self):
        # Delegate to the parent or grandparent method based on the dynamic instance
        if hasattr(self.parent_instance, "parent_method"):
            return self.parent_instance.parent_method()  # VersionedFC
        elif hasattr(self.parent_instance, "grandparent_method"):
            return self.parent_instance.grandparent_method()  # FC

    def add_field(self, in_table, field_name, field_type, length, field_alias, field_is_nullable, field_is_required,
                  field_domain=''):
        if field_type == 'STRING':
            arcpy.management.AddField(in_table=in_table, field_name=field_name, field_type=field_type,
                                    field_length=length, field_alias=field_alias, field_is_nullable=field_is_nullable,
                                    field_is_required=field_is_required, field_domain=field_domain)
        elif field_type == 'SHORT':
            arcpy.management.AddField(in_table=in_table, field_name=field_name, field_type=field_type,
                                    field_precision=length, field_alias=field_alias, field_is_nullable=field_is_nullable,
                                    field_is_required=field_is_required, field_domain=field_domain)

    def remove_field(self, field_list):
        for field in field_list:
            arcpy.management.DeleteField(in_table=self.path, drop_field=field)
        print(f'Fields dropped for {self.path}')

    def __alter_fields(self, k, alter_list):
        if k == 'Only Alias':
            arcpy.management.AlterField(in_table=self.path, field=alter_list[0], new_field_alias=alter_list[1])
        elif k == 'Name and Alias':
            arcpy.management.AlterField(in_table=self.path, field=alter_list[0], new_field_name=alter_list[1],
                                        new_field_alias=alter_list[2])
        elif k == 'Only Name':
            arcpy.management.AlterField(in_table, field=alter_list[0], new_field_name=alter_list[1])
        elif k == 'Alias and Length':
            arcpy.management.AlterField(in_table, field=alter_list[0], new_field_alias=alter_list[1],
                                        field_length=alter_list[2])

    def __add_domain(self, k, domain_list):
        if k == 'domain':
            arcpy.management.AssignDomainToField(in_table=self.path, field_name=domain_list[0],
                                                 domain_name=domain_list[1])

    def __add_default_value(self, k, default_list):
        if k == 'Default Value':
            arcpy.management.AssignDefaultToField(in_table=self.path, field_name=default_list[0],
                                                  default_value=default_list[1])

    def modify_fields(self, alter_dict):
        # Apply the methods
        for key, val in alter_dict:
            __alter_fields(key, val)
            __add_domain(key, val)
            __add_default_value(key, val)


# Child class that can perform data loads on the feature class
class DataLoadFC:
    def __init__(self, path):
        """
        Initializes a connection to the specified geodatabase with versioning support.
        :param path: Path to the geodatabase.
        """
        super().__init__(path)  # Initialize the parent class


    def load_data(self, csv_file, field_to_update, field_to_read, idfield_update, idfield_read):
        """
        Traditionally, how a data load woul work is you would join the update table to the feature class on a PK-FK
        connection. Then you would reclaculate the target field from the FC to the update field from the update table.
        How this works is it uses the update cursor to write fields from the csv to the fc. It is much faster than
        joining the fields, calculating, and removing the join. Also avoids the pitfalls from dealing with versioned
        data that cannot deal with schema changes easily.
        :param csv_file: csv file path for the new data to be updated; STRING
        :param field_to_update: Name of the field that will be updated in the feature class; STRING
        :param field_to_read: Name of the field that contains the new data from the csv; STRING
        :param idfield_update: Name of the Primary Key that will connect the proper records of the fc to the csv; STRING
        :param idfield_read: Name of the Foreign Key that will connect the proper records of the csv to the fc; STRING
        :return:
        """
        # Set the workspace for where the edit will take place
        workspace = os.path.dirname(self.path)
        edit = arcpy.da.Editor(workspace)  # Edit workspace
        edit.startEditing(False, True)  # args: with_undo, multiuser
        edit.startOperation()  # Start the editing
        try:
            # Create a dictionary for the field records that will be updated. The key is the id field and the value is
            #  update field
            d = {k: v for k, v in arcpy.da.SearchCursor(csv_file, [idfield_read, field_to_read])}
            # Method 1
            with arcpy.da.UpdateCursor(self.path, [idfield_update, field_to_update]) as cursor:
                # Method 2
                # with uc_wrapper.UpdateCursor(shape_to_update, [idfield_update, field_to_update]) as cursor:
                # Opened the cursor

                for row in cursor:  # For each row in table
                    if row[0] in d:  # Check if this rows idfield_update is in the dict that matches to idfield_read
                        row[1] = d[row[0]]  # If so, update field_to_update to be field_to_read
                        cursor.updateRow(row)  # "Save" the update
                logger.log('Iterated through the rows')

                for row in cursor:  # For each row in table
                    if row[0] in d:  # Check if this rows OBJECTID is in the dict
                        row[1] = d[row[0]]  # If so, update row[1]/'value' read in field
                        cursor.updateRow(row)  # "Save"
                logger.log('Iterated through the rows')
        except Exception as e:
            edit.abortOperation()
            print(f"Error: {str(e)}")
        else:
            print('Stopping the Operation')
            edit.stopOperation()
            print('Stop the Editing')
            edit.stopEditing(save_changes=True)  # True to save edits, False to discard


#=======================================================================================================================
# FUNCTIONS
#=======================================================================================================================


def drop_users(ws):
    arcpy.DisconnectUser(ws, 'ALL')
    print('Users have been disconnected')


def db_connect(envt, db_path, db_base, db_name, feature_class, fd=False, feature_dataset="UUP"):
    """
    Connects to a file to the Atlas or Atlas Edit DB
    :param db_path: path to the file;STRING
    :param db_base: the db path name, EX: "TSW@ATLAS-EDITDEV@";STRING
    :param db_name: The name of the DB, EX: TSWEDITDEV.sde"; STRING
    :param feature_class: The feature class name; STRING
    :param fd: Existance of a feature dataset
    :param feature_dataset: FD name; STRING
    :return: the feature class of the database
    """
    # Connect the files
    db_info = db_base + db_name
    new_path = os.path.join(db_path, envt)
    db = os.path.join(new_path, db_info)
    db_split = db_base.split("@")
    if fd == True:
        folder = '\\' + db_name[:-4] + "." + db_split[0] + "." + feature_dataset
    else:
        folder = ""
    out_name = '\\' + db_name[:-4] + "." + db_split[0] + "." + feature_class
    out_path = db + folder + out_name
    return out_path


def load_data(fc_path, csv_file, field_to_update, field_to_read, idfield_update, idfield_read):
    """
    Traditionally, how a data load woul work is you would join the update table to the feature class on a PK-FK
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
            logger.log('Iterated through the rows')

            for row in cursor:  # For each row in table
                if row[0] in d:  # Check if this rows OBJECTID is in the dict
                    row[1] = d[row[0]]  # If so, update row[1]/'value' read in field
                    cursor.updateRow(row)  # "Save"
            logger.log('Iterated through the rows')
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
    pass
