# imports
import arcpy
import pandas as pd
import os


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

    # ===============================================================
    #  Schema Understanding Methods
    # ===============================================================

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

    def generate_schema_report(self, export_report=None, *args):
        """
        Generates a schema report that can be a pandas table or exported to a csv
        :param export_report: Output location and name to print the csv file. If none will make the output a pandas df;
                              STRING
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
        if export_report:  # Checks if it is None
            df.to_csv(export_report, index=False)
        else:
            return df

    #===============================================================
    #  Versioning Methods
    # ===============================================================

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

    # I have yet to test this code, don't think it works
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

    # ===============================================================
    #  Schema Change Methods
    # ===============================================================

    def add_field(self, in_table, field_name, field_type, length, field_alias, field_is_nullable, field_is_required,
                  field_domain=''):
        if field_type == 'STRING':
            arcpy.management.AddField(in_table=in_table, field_name=field_name, field_type=field_type,
                                    field_length=length, field_alias=field_alias, field_is_nullable=field_is_nullable,
                                    field_is_required=field_is_required, field_domain=field_domain)
        elif field_type == 'SHORT':
            arcpy.management.AddField(in_table=in_table, field_name=field_name, field_type=field_type,
                                      field_precision=length, field_alias=field_alias,
                                      field_is_nullable=field_is_nullable, field_is_required=field_is_required,
                                      field_domain=field_domain)

    def remove_field(self, field_list):
        for field in field_list:
            arcpy.management.DeleteField(in_table=self.path, drop_field=field)
        print(f'Fields dropped for {self.path}')

    def alter_fields(self, k, alter_list):
        """
        Expects an input
        :param k: Key to say what will be updated, options are: 'Only Alias', 'Name and Alias', 'Only Name',
                  'Alias and Length', 'Length', ; STRING
        :param alter_list: Input list in the format of: [current name, new name, new alias, new length]
        :return:
        """
        if k == 'Only Alias':
            arcpy.management.AlterField(in_table=self.path, field=alter_list[0], new_field_alias=alter_list[2])
        elif k == 'Name and Alias':
            arcpy.management.AlterField(in_table=self.path, field=alter_list[0], new_field_name=alter_list[1],
                                        new_field_alias=alter_list[2])
        elif k == 'Only Name':
            arcpy.management.AlterField(in_table=self.path, field=alter_list[0], new_field_name=alter_list[1])
        elif k == 'Alias and Length':
            arcpy.management.AlterField(in_table=self.path, field=alter_list[0], new_field_alias=alter_list[2],
                                        field_length=alter_list[3])
        elif k == 'Length':
            arcpy.management.AlterField(in_table=self.path, field=alter_list[0], field_length=alter_list[3])

    def add_domain(self, k, domain_list):
        if k == 'Domain':
            arcpy.management.AssignDomainToField(in_table=self.path, field_name=domain_list[0],
                                                 domain_name=domain_list[1])

    def add_default_value(self, k, default_list):
        if k == 'Default Value':
            arcpy.management.AssignDefaultToField(in_table=self.path, field_name=default_list[0],
                                                  default_value=default_list[1])

    def batch_modify_fields(self, alter_dict):
        """
        Alters fields based on the given dictionary of key as how to update and value as the update list
        :param alter_dict: in the format of key is how to update and value is the update list.
                           Key options: 'Only Alias', 'Name and Alias', 'Only Name', 'Alias and Length', 'Length'
                           Value list format: if to change fields: [current name, new name, new alias, new length]
                           If to add a domain
        :return:
        """
        # Apply the methods
        for key, val in alter_dict:
            alter_fields(key, val)
            add_domain(key, val)
            add_default_value(key, val)

    # ===============================================================
    #  Data Load Methods
    # ===============================================================

    def load_data(self, csv_file, field_to_update, field_to_read, idfield_update, idfield_read):
        """
        Traditionally, how a data load would work is you would join the update table to the feature class on a PK-FK
        connection. Then you would recalculate the target field from the FC to the update field from the update table.
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
        try:
            # Create a dictionary for the field records that will be updated. The key is the id field and the value is
            #  update field
            d = {k: v for k, v in arcpy.da.SearchCursor(csv_file, [idfield_read, field_to_read])}
            # Open the search cursor
            with arcpy.da.UpdateCursor(self.path, [idfield_update, field_to_update]) as cursor:
                for row in cursor:  # For each row in table
                    if row[0] in d:  # Check if this rows idfield_update is in the dict that matches to idfield_read
                        row[1] = d[row[0]]  # If so, update field_to_update to be field_to_read
                        cursor.updateRow(row)  # "Save" the update
                # print('Iterated through the rows')

        except Exception as e:
            print(f"Error: {str(e)}")


    def load_data_versioned(self, csv_file, field_to_update, field_to_read, idfield_update, idfield_read):
        """
        Traditionally, how a data load would work is you would join the update table to the feature class on a PK-FK
        connection. Then you would recalculate the target field from the FC to the update field from the update table.
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
        norm_path = os.path.normpath(self.path)  # Normalize the path
        print(norm_path)
        parts = norm_path.split(os.sep)
        print(parts)
        # Find the index of the .sde file in the path
        for i, part in enumerate(parts):
            if part.endswith(".sde"):
                # Join up to and including the .sde file
                almost_workspace = os.path.join(*parts[:i + 1])
                workspace = f'\\\\{almost_workspace}'

        print(workspace)
        arcpy.env.workspace = workspace
        edit = arcpy.da.Editor(workspace)  # Edit workspace
        edit.startEditing(False, True)  # args: with_undo, multiuser

        try:
            edit.startOperation()  # Start the editing
            # Create a dictionary for the field records that will be updated. The key is the id field and the value is
            #  update field
            d = {k: v for k, v in arcpy.da.SearchCursor(csv_file, [idfield_read, field_to_read])}
            # Open the search cursor
            with arcpy.da.UpdateCursor(self.path, [idfield_update, field_to_update]) as cursor:
                for row in cursor:  # For each row in table
                    if row[0] in d:  # Check if this rows idfield_update is in the dict that matches to idfield_read
                        row[1] = d[row[0]]  # If so, update field_to_update to be field_to_read
                        cursor.updateRow(row)  # "Save" the update
                # print('Iterated through the rows')

        except Exception as e:
            edit.abortOperation()
        else:
            edit.stopOperation()
            edit.stopEditing(save_changes=True)  # True to save edits, False to discard

if __name__ == '__main__':

    pass

