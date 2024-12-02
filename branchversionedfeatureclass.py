import arcpy
import os
import sys
import pandas as pd
from arcgis.gis import GIS
from arcgis.features import FeatureLayer, FeatureLayerCollection
from arcgis.features._version import VersionManager, Version

# ======================================================================================================================
# HELPER FUNCTIONS
# ======================================================================================================================


def connect_to_gis(gis_info=[]):
    """
    Connects to a GIS. Returns the gis object. Best if this code is used like: 'gis = connect_to_gis()'
    :param gis_info: [portal_url, AD\\<account>, <AD Password>]. If none then current pro connection will be used; List
    :return: The GIS object
    """
    # Connect to a GIS
    if len(gis_info) == 0:
        gis = GIS('Pro')
        return gis
    elif len(gis_info) == 3:
        gis = GIS(gis_info[0], gis_info[1], gis_info[2])
        return gis
    else:
        print('issue with logging in')


def create_new_version(flc_id, version_name, gis_con):
    """
    Creates a new version for a feature layer collection
    :param flc_id: The unique identifying string (Service Item Id) for a feature service; STRING
    :param version_name: Name of the version; STRING
    :param gis_con: Connection to a GIS; ESRI GIS Object
    :return: version object, all versions list
    """
    try:
        # Connect to the feature layer connection (feature service)
        feature_layer_item = gis_con.content.get(flc_id)
        flc = FeatureLayerCollection.fromitem(feature_layer_item)

        # Make a version description
        version_description = "Temporary version created by a python tool"
        # Connect to the version manager
        service_url = flc.url.rsplit('/', 1)[0]  # Remove the last bit from the URL, AKA remove the 'FeatureServer' folder
        vm_url = f'{service_url}/VersionManagementServer'
        vm = VersionManager(url=vm_url, gis=gis_con, flc=flc)
        # Make sure the version doesn't already exist
        all_versions = vm.all
        for v in all_versions:
            v_name = v.properties['versionName'].rsplit('.', 1)[1]  # Get the name of the version w/o user information
            if v_name == version_name:
                print(f'{version_name} already exists, creating a new version named {version_name}_tool')
                version_name = version_name + '_tool'
                # Check if the appended name exists
                for v_apd in all_versions:
                    v_nam = v_apd.properties['versionName'].rsplit('.', 1)[1]
                    if v_nam == version_name:
                        version_name = version_name + '_1'  # Here I will assume that nothing is named this
        # The following line does not work for Pro version 2.7.X,
        version_dict = vm.create(name=version_name, permission='public', description=version_description)
        version = vm.get(version_dict['versionInfo']['versionName'])  # Make an instance of the version based on the name
        return version, all_versions
    except Exception as e:
        print('error with create_new_version()')
        print(e)


# ======================================================================================================================
# WORKFLOW FUNCTIONS
# ======================================================================================================================

# Tool to add data to a branch versioned feature class
def data_update_directly_to_default(flc_id, fl_idx, write_field, write_id, read_df, read_field, read_id, gis_info=[]):
    """
    Performs a data load for a branch versioned feature layer in Portal
    :param flc_id: the unique identifying string (Service Item Id) for a feature service; STRING
    :param fl_idx: The index for the featyre layer in the feature service; INT
    :param write_field: The name of the field for the feature layer that will be updated
    :param write_id: The name of the field for the feature layer that will join to the new dataframe
    :param read_df: The dataframe for the data that will update the feature layer. Needs at least two columns, an index
                    to join to the feature layer and an update column that contains the new data
    :param read_field: The name of the field for the dataframe that contains the new update field
    :param read_id: The name of the field for the update dataframe that will join to the feature layer
    :param gis_info: [portal_url, AD\\<account>, <AD Password>]. If none then current pro connection will be used; List
    :return:
    """

    # Connect to a GIS
    if len(gis_info) == 3:
        gis = GIS(gis_info[0], gis_info[1], gis_info[2])
    else:
        gis = GIS('Pro')

    # Connect to the feature layer connection (feature service)
    feature_layer_item = gis.content.get(flc_id)
    flc = FeatureLayerCollection.fromitem(feature_layer_item)

    # Connect to the feature layer
    fl = FeatureLayer(f'{flc.url}/{fl_idx}', gis=gis)

    # Get a feature set of the feature layer by creating an empty query
    fset = fl.query()

    # make a dataframe based on the feature set
    # fl_df = fset.sdf

    # Get the features of the feature set
    features_to_update = fset.features

    # Update the features of the feature layer based on the data load df
    # Note, this doesn't actually update the feature layer in portal, rather a list that is a copy of the features of
    # the feature layer
    for feature in features_to_update:
        for fid in read_df[read_id]:
            if feature.attributes[write_id] == fid:
                specific_value = read_df.loc[read_df[read_id] == fid, read_field].values[0]
                feature.attributes[write_field] = specific_value

    # features_to_update contains all the features, however, likely only a subset will need to be updated. Only take the
    # updated features to update the feature layer
    # Convert the oid column to a list
    records_to_keep_list = read_df[read_id].tolist()
    features_to_update_reduced = []
    for feature in features_to_update:
        if feature.attributes[write_field] in records_to_keep_list:
            features_to_update_reduced.append(feature)

    # Push the edits to the feature layer in Portal
    fl.edit_features(updates=features_to_update_reduced)


def data_update_old(flc_id, fl_idx, write_field, write_id, read_df, read_field, read_id, gis_info=[],
              version_name='tool_version'):
    """
    Performs a data load for a branch versioned feature layer in Portal
    :param flc_id: the unique identifying string (Service Item Id) for a feature service; STRING
    :param fl_idx: The index for the featyre layer in the feature service; INT
    :param write_field: The name of the field for the feature layer that will be updated
    :param write_id: The name of the field for the feature layer that will join to the new dataframe
    :param read_df: The dataframe for the data that will update the feature layer. Needs at least two columns, an index
                    to join to the feature layer and an update column that contains the new data
    :param read_field: The name of the field for the dataframe that contains the new update field
    :param read_id: The name of the field for the update dataframe that will join to the feature layer
    :param gis_info: [portal_url, AD\\<account>, <AD Password>]. If none then current pro connection will be used; List
    :param version_name: Name for the version where the editing will take place
    :return:
    """

    # Connect to a GIS
    if gis_info == None:
        gis = GIS('Pro')
    elif len(gis_info) == 3:
        gis = GIS(gis_info[0], gis_info[1], gis_info[2])
    else:
        print('issue with logging in')

    # Connect to the feature layer connection (feature service)
    feature_layer_item = gis.content.get(flc_id)
    flc = FeatureLayerCollection.fromitem(feature_layer_item)

    # Make a new version to make the edits in
    version_description = "Data update using the branch versioning data update tool"
    # Connect to the version manager
    service_url = flc.url.rsplit('/', 1)[0]  # Remove the last bit from the URL, AKA remove the 'FeatureServer' folder
    vm_url = f'{service_url}/VersionManagementServer'
    vm = VersionManager(url=vm_url, gis=gis, flc=flc)
    # Make sure the version doesn't already exist
    all_versions = vm.all
    for v in all_versions:
        v_name = v.properties['versionName'].rsplit('.', 1)[1]  # Get the name of the version w/o user information
        if v_name == version_name:
            print(f'{version_name} already exists, creating a new version named {version_name}_tool')
            version_name = version_name + '_tool'
            # Check if the appended name exists
            for v_apd in all_versions:
                v_nam = v_apd.properties['versionName'].rsplit('.', 1)[1]
                if v_nam == version_name:
                    version_name = version_name + '_1'  # Here I will assume that nothing is named this
    version_dict = vm.create(name=version_name, permission='public', description=version_description)
    version = vm.get(version_dict['versionInfo']['versionName'])  # Make an instance of the version based on the name

    try:
        # Get the feature layer in the version
        versioned_fl = version.layers[int(fl_idx)]

        # Get a feature set of the feature layer by creating an empty query
        fset = versioned_fl.query()

        # Get all the features of the feature set
        all_features = fset.features

        # Update the features of the feature layer based on the data load df
        # Note, this doesn't actually update the feature layer in portal, rather a list that is a copy of the features
        # of the feature layer
        for feature in all_features:
            for fid in read_df[read_id]:
                if feature.attributes[write_id] == fid:
                    specific_value = read_df.loc[read_df[read_id] == fid, read_field].values[0]
                    feature.attributes[write_field] = specific_value

        # all_features contains all the features, however, likely only a subset will need to be updated. Only take the
        # updated features to update the feature layer
        # Convert the oid column to a list
        records_to_keep_list = read_df[read_id].tolist()
        features_to_update = []
        for feature in all_features:
            if feature.attributes[write_id] in records_to_keep_list:
                features_to_update.append(feature)

        # Start an edit session
        version.start_editing()
        # Apply the edit to a version of the feature layer
        update_result = version.edit(versioned_fl, updates=features_to_update, rollback_on_failure=True)
        # Check the result
        if update_result == None:
            print('No update happened, something went wrong')
        elif update_result['updateResults'][0]['success'] == True:
            print('Data updated successfully')
        elif update_result['updateResults'][0]['success'] == False:
            print('Data failed to update')
        # Push the edit from the version to Default
        rec_result = version.reconcile(end_with_conflict=False, with_post=True, conflict_detection='byObject',
                                       future=False)
        # Check the result
        if rec_result['didPost'] == True:
            print('Result Posted')
        elif rec_result['didPost'] == False:
            print('Result did not post')
        # Save the edit
        version.stop_editing(save=True)
    except Exception as e:
        print(e)
        print('Deleting the version')
        # Delete the version
        version.delete()

    # Delete the version if it exists
    for v in all_versions:
        v_name = v.properties['versionName'].rsplit('.', 1)[1]  # Get the name of the version w/o user information
        if v_name == version_name:  # Finds if it exists
            v.delete()  # Deletes the version


def data_update(flc_id, fl_idx, write_field, write_id, read_df, read_field, read_id, gis_info=[],
              version_name='tool_version', post_to_default=True):
    """
    Performs a data load for a branch versioned feature layer in Portal
    :param flc_id: the unique identifying string (Service Item Id) for a feature service; STRING
    :param fl_idx: The index for the featyre layer in the feature service; INT
    :param write_field: The name of the field for the feature layer that will be updated
    :param write_id: The name of the field for the feature layer that will join to the new dataframe
    :param read_df: The dataframe for the data that will update the feature layer. Needs at least two columns, an index
                    to join to the feature layer and an update column that contains the new data
    :param read_field: The name of the field for the dataframe that contains the new update field
    :param read_id: The name of the field for the update dataframe that will join to the feature layer
    :param gis_info: [portal_url, AD\\<account>, <AD Password>]. If none then current pro connection will be used; List
    :param version_name: Name for the version where the editing will take place
    :param post_to_default: If True, posts the change from the envt to default version, if False change remain in the
    version. If this tool is False, best practice is to change the version name from the default 'tool_version' to a
    user named version; BOOL
    :return:
    """

    # Connect to a GIS
    gis = connect_to_gis(gis_info)

    version, all_versions = create_new_version(flc_id=flc_id, version_name=version_name, gis_con=gis)

    try:
        # Get the feature layer in the version
        versioned_fl = version.layers[int(fl_idx)]
        # Get a feature set of the feature layer by creating an empty query
        fset = versioned_fl.query()
        # Get all the features of the feature set
        all_features = fset.features
        # Update the features of the feature layer based on the data load df
        # Note, this doesn't actually update the feature layer in portal, rather a list that is a copy of the features
        # of the feature layer
        for feature in all_features:
            for fid in read_df[read_id]:
                if feature.attributes[write_id] == fid:
                    specific_value = read_df.loc[read_df[read_id] == fid, read_field].values[0]
                    feature.attributes[write_field] = specific_value

        # all_features contains all the features, however, likely only a subset will need to be updated. Only take the
        # updated features to update the feature layer
        # Convert the oid column to a list
        records_to_keep_list = read_df[read_id].tolist()
        features_to_update = []
        for feature in all_features:
            if feature.attributes[write_id] in records_to_keep_list:
                features_to_update.append(feature)

        # Start an edit session
        version.start_editing()
        # Apply the edit to a version of the feature layer
        update_result = version.edit(versioned_fl, updates=features_to_update, rollback_on_failure=True)
        # Check the result
        if update_result == None:
            print('No update happened, something went wrong')
        elif update_result['updateResults'][0]['success'] == True:
            print('Data updated successfully')
        elif update_result['updateResults'][0]['success'] == False:
            print('Data failed to update')
        # Push the edit from the version to Default
        if post_to_default:
            rec_result = version.reconcile(end_with_conflict=False, with_post=True, conflict_detection='byObject',
                                           future=False)
            # Check the result
            if rec_result['didPost'] == True:
                print('Result Posted')
            elif rec_result['didPost'] == False:
                print('Result did not post')
        # Save the edit
        version.stop_editing(save=True)
    except Exception as e:
        print(e)
        print('Deleting the version')
        # Delete the version
        version.delete()

    # Delete the version if it exists
    if post_to_default:
        for v in all_versions:
            v_name = v.properties['versionName'].rsplit('.', 1)[1]  # Get the name of the version w/o user information
            if v_name == version_name:  # Finds if it exists
                v.delete()  # Deletes the version


# Still under construction
def add_new_records(flc_id, fl_idx, write_field, write_id, read_df, read_field, read_id, gis_info=[],
                    version_name='tool_version', envt='DEV'):
    # Connect to a GIS
    gis = connect_to_gis(gis_info)

    version, all_versions = create_new_version(flc_id=flc_id, version_name=version_name, gis_con=gis)

    try:
        # Get the feature layer in the version
        versioned_fl = version.layers[int(fl_idx)]

        # Get a feature set of the feature layer by creating an empty query
        fset = versioned_fl.query()

        # Get all the features of the feature set
        all_features = fset.features

        # Todo something to add features


        # Start an edit session
        version.start_editing()
        # Apply the edit to a version of the feature layer
        update_result = version.edit(versioned_fl, adds=features_to_update, rollback_on_failure=True)
        # Check the result
        if update_result == None:
            print('No update happened, something went wrong')
        elif update_result['updateResults'][0]['success'] == True:
            print('Data updated successfully')
        elif update_result['updateResults'][0]['success'] == False:
            print('Data failed to update')
        # Push the edit from the version to Default
        rec_result = version.reconcile(end_with_conflict=False, with_post=True, conflict_detection='byObject',
                                       future=False)
        # Check the result
        if rec_result['didPost'] == True:
            print('Result Posted')
        elif rec_result['didPost'] == False:
            print('Result did not post')
        # Save the edit
        version.stop_editing(save=True)
    except Exception as e:
        print(e)
        print('Deleting the version')
        # Delete the version
        version.delete()

    # Delete the version if it exists
    for v in all_versions:
        v_name = v.properties['versionName'].rsplit('.', 1)[1]  # Get the name of the version w/o user information
        if v_name == version_name:  # Finds if it exists
            v.delete()  # Deletes the version


# Mostly works, the delete part works on VM06 but not VM07
def delete_records(flc_id, fl_idx, oid_del_list, gis_info=[], version_name='tool_version',
                   post_to_default=True):
    """
    Deletes records from a branch versioned feature layer. Deletes from a version, defaults to pushing the change to
    default
    :param flc_id: the unique identifying string (Service Item Id) for a feature service; STRING
    :param fl_idx: The index for the featyre layer in the feature service; INT
    :param oid_del_list: list of OIDs in a string format to remove
    :param gis_info: [portal_url, AD\\<account>, <AD Password>]. If none then current pro connection will be used; List
    :param version_name: Name for the version where the editing will take place
    :param post_to_default: If True, posts the change from the envt to default version, if False change remain in the
    version. If this tool is False, best practice is to change the version name from the default 'tool_version' to a
    user named version; BOOL
    :return:
    """
    # Connect to a GIS
    gis = connect_to_gis(gis_info)
   
    # Create the version and all_version list
    version, all_versions = create_new_version(flc_id=flc_id, version_name=version_name, gis_con=gis)

    try:
        # Get the feature layer in the version
        versioned_fl = version.layers[int(fl_idx)]
        # Start an edit session
        version.start_editing()
        # Apply the edit to a version of the feature layer
        update_result = version.edit(versioned_fl, deletes=oid_del_list, rollback_on_failure=True)
        # Check the result
        if update_result == None:
            print('No update happened, something went wrong')
        elif update_result['deleteResults'][0]['success'] == True:
            print('Data updated successfully')
        elif update_result['deleteResults'][0]['success'] == False:
            print('Data failed to update')
            print(update_result.get('deleteResults', [{}])[0].get('error', 'Unknown error'))
        # Push the edit from the version to Default
        if post_to_default:
            rec_result = version.reconcile(end_with_conflict=False, with_post=True, conflict_detection='byObject',
                                           future=False)
            # Check the result
            if rec_result['didPost'] == True:
                print('Result Posted')
            elif rec_result['didPost'] == False:
                print('Result did not post')
        # Save the edit
        version.stop_editing(save=True)
    except Exception as e:
        print(e)
        print('End the editing session')
        version.stop_editing(save=False)
        print('Deleting the version')
        # Delete the version if post to default
        if post_to_default:
            version.delete()

    # Delete the version if it exists is I post to default since the version is no longer needed
    not_del_flag = True
    if post_to_default:
        for v in all_versions:
            v_name = v.properties['versionName'].rsplit('.', 1)[1]  # Get the name of the version w/o user information
            if v_name == version_name:  # Finds if it exists
                print(f'Deleting version: {v_name}')
                v.delete()  # Deletes the version
                not_del_flag = False
    if not_del_flag:
        try:
            version.delete()
        except Exception as e:
            print(e)
            print('Trouble deleting the version')


def schema_change(flc_id, sde_con):
    """
    Changes the schema for a feature class/feature layer. Ensures that schema changes can be made, then makes the schema
    change on the actual sde connection.
    :param flc_id:
    :param sde_con:
    :return:
    """

    # Change the lock to be able to see
    # Seem to have issues with the manager so I will skip this one for now
    pass


if __name__ == '__main__':

    pass


