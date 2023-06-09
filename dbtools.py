# Author: Chandler Ross | Quartic Solutions
# Description: A set of tools for working with the spatial database


# Imports


# Functions


########################################################################################################################
# Oracle Database Connection Start Function
########################################################################################################################
def db_start(oracle_instance, oracle_pwd):
    print("Connecting to Oracle")
    # oracle_instance = "dsd"
    # oracle_pwd = "SITE"
    # tableMapLayerSecurityGroup = "DSBC.MAPLAYER_SECURITYGROUP"
    # tableMapLayerMapLayerMetadata = "DSBC.MAPLAYER_MAPLAYER_METADATA"
    # tableJobLocTransaction = "P2K.JOB_LOC_TRANSACTION"
    # tableJobLocation = "P2K.JOB_LOCATION"
    db = cx_Oracle.connect("site/" + oracle_pwd + "@" + oracle_instance)
    o_cursor = db.cursor()
    print("Success")
    t.sleep(2)
    return db, o_cursor


########################################################################################################################
# Run Oracle Query Function
########################################################################################################################
def run_oracle_query(query, o_cursor, print_statement=False, commit=False, db=None):
    '''
    This function runs a SQL query
    :param query: The query to be run; String
    :param o_cursor: The oracle cursor; Cursor Class?
    :param print_statement: If ture, it will print ift the function ran; Bool
    :param commit: 
    :param db: The database to run on; Class?
    :return:
    '''
    o_cursor.execute(query)
    if commit:
        db.commit()
        if(print_statement):
            print(query, ' Has successfully run')
    else:
        return o_cursor.fetchall()


########################################################################################################################
# Join two tables (WIP)
########################################################################################################################
def table_join(tbl1, col1, tbl2, col2, join_type):
    '''
    Joins two tables
    :param tbl1: The name of table 1; String
    :param col1: The name of table 1 column to join on; String
    :param tbl2: The name of table 2; String
    :param col2: The name of table 2 column to join with; String
    :param join_type: The type of join. Either 'inner', 'right outer', 'left outer', 'cross', or 'natural'; String
    :return: A joined table
    '''
    pass


########################################################################################################################
# ASCII to Oracle Function from custom script in toolbox
########################################################################################################################
def ASCIIToOracle(fileAscii, dbInstance="prod"):
    # Script Name: load_ascii_to_oracle.py
    #
    # Description: Replaces load_dbf_to_oracle.aml.  Input to this script tool is
    #              an ASCII file produced by the Export Feature Attribute to ASCII
    #              script tool.  This script finalizes the file, sorts it, and runs
    #              a .bat script which loads the data into Oracle using SQL*Loader.
    #
    #              The arcgisscripting module is not needed in this Python script,
    #              because all the tasks performed here are non-GIS tasks.
    #
    #   IMPORTANT: To view the execution of this script while it is running, make
    #   sure this has been done: Drill down to ArcToolbox > PTS Tools > Parcel
    #   Refresh; right-click on load_ascii_to_oracle.py; click Properties > Source
    #   tab; turn off the checkbox for Run Python script in process, and turn on
    #   the checkbox for Show command window when executing script.
    #
    # Created By: Dave Snyder
    # Date: December 2010

    try:

        pathPTS = os.environ.get('PTS')

        fileIn = fileAscii

        print("fileAscii:  " + fileAscii)
        print("dbInstance:  " + dbInstance)
        print("fileIn:  " + fileIn)

        # Remove the .___ extension, if present, from the file name

        if fileAscii[-4] == '.':
            fileAsciiNoExt = fileAscii[:len(fileAscii) - 4]

        print("fileAsciiNoExt:  " + fileAsciiNoExt)

        # Get the basename of the file (with no path and no extension)

        fileAsciiBasename = os.path.basename(fileAsciiNoExt)


        print("fileAsciiBasename:  " + fileAsciiBasename)

        fileUnq = fileAsciiNoExt + ".unq"
        fileOut = fileAsciiNoExt + ".txt"

        # Remove the floating point X and Y values that are forcibly written into
        # the left-most 34 bytes of each line by the Export Feature Attribute to
        # ASCII script (in that script tool, there is no option NOT to include the
        # X and Y values)

        for line in fileinput.input(fileIn, inplace=True):
            string = line
            line = line.replace(string, string[34:])
            sys.stdout.write(line)
        fileinput.close()

        print("Just removed the X and Y values...now removing the decimal places...")

        # Remove the decimal places that are appended to integer values
        # by the Export Feature Attribute to ASCII script (in that script tool,
        # there is no option to say "please don't add decimal places to my
        # integers")

        for line in fileinput.input(fileIn, inplace=True):
            line = line.replace(".000000", "")
            sys.stdout.write(line)
        fileinput.close()

        print("Just removed the decimal places...now removing duplicates...")

        # Remove duplicate rows from the file

        rows = open(fileIn).read().split("\n")
        newrows = []
        for row in rows:
            if row not in newrows:
                newrows.append(row)

        f = open(fileUnq, "w")
        f.write("\n".join(newrows))
        f.close()

        print("Just removed duplicate rows...starting the sort...")

        # Sort the file

        outfile = open(fileOut, "w")
        # Code origionally used file() which is the python 2 version of open()
        outfile.writelines(sorted(open(fileUnq, "r").readlines()))
        outfile.close()

        print("Just completed the sort...calling the SQL*Loader script...")

        # Run the .bat file which runs the SQL*Loader command

        shutil.copyfile(fileOut, os.path.join(Processing_Tool_dir_path, os.path.basename(fileOut)))
        shutil.copyfile(fileUnq, os.path.join(Processing_Tool_dir_path, os.path.basename(fileUnq)))

        # Run the .bat file which runs the SQL*Loader command (Does not use the newly generated files)
        ####################################################################
        # NOTE: '.ctl' files located in 'C:\\MyData\\City\\DSD\\PTS\\parcels\\scripts' have been updated to point to new Parcel Processing Folder.
        ####################################################################
        os.system(pathPTS + "/load_ascii_to_oracle.bat prod " + fileAsciiBasename + " > " + Work_Tool_data_dir_path + "/load_ascii_to_oracle_" + fileAsciiBasename + ".log")

        #os.system(pathPTS + "/load_ascii_to_oracle.bat " + dbInstance + " " + fileAsciiBasename + " > " + pathPTS + "/load_ascii_to_oracle_" + fileAsciiBasename + ".log")

        timeNow = datetime.time(datetime.now())
        print("SQL*Loader script completed at " + str(timeNow) + "...you are done")
        print(Work_Tool_data_dir_path + "/load_ascii_to_oracle_" + fileAsciiBasename + ".log")
        # Uncomment this line to see the execution in the command window
        input("Press ENTER to continue...")
    except Exception as e:
        print("I am in the except section...an error occurred")
        print(e)
        input("Press ENTER to continue...")






