import re
# Tab Delimited txt file exported as an excel from Jira
# Export all columns, must delete the description and audit columns (AC, AU - AY)
#   Save file as 'jira.txt'

# Export GDS - Reporting - All ICs (CSV) from iRIS
#   Save file as 'iris.txt'

# Edit paths below to match the locations of your jira and iris files
JiraFile = "/Users/manlovelj/Desktop/jira.txt"
iRISFile = "/Users/manlovelj/Desktop/iris.txt"

def read_jira(JiraFile):
    ''' Takes a tab delimited text file exported from jira
        returns three list containing:
            (1) the header from the jira file,
            (2) a list of Jira study ID's, and
            (3) a list of lists of Jira study data'''
    # Creates two empty lists to contain the study IDs and the Study data recieved from Jira
    JiraID = []
    JiraData = []

    # Reads in the Jira file. First pulls the header row.
    with open(JiraFile, "r", encoding = "ISO-8859-1") as file:
        JiraHeader = file.readline()
        JiraHeader = JiraHeader.strip('\n').split('\t')

    # Steps through the rest of the file row by row.
        for line in file.readlines():
            line = line.strip('\n').split('\t')

    # Checks to see if there is an empty line in the protocol. This should not happen. If its not empty it attempts to add the protocol number to the list.
            if line[0] == "":
                JiraID.append("No Protocol")
            else:

    # Failure in writing the protocol number to the list should be rare and has very little impact so it just skips on failure
                try:
                    JiraID.append(line[182])
                except:
                    print('failed to add protocol {} to list'.format(line[182]))

    # Writes the rest of the data to the 'data' list
            JiraData.append(line)


    return JiraID, JiraData, JiraHeader

def read_iris(iRISFile, JiraID, JiraData):
    ''' Takes a tab delimited text file exported from iris, a list of jira IDs and the matching jira data
        returns three list containing:
            (1) the header from the iris file,
            (2) a list of study IDs that match Jira studies
            (3) a list of lists of iris study data

    Data in the excel file are in columns as follows:
    (0) Protocol Number
    (1) Protocol Short Title
    (2) PI Name
    (3) Branch
    (4) Study Status
    (5) IRB Initial Approval Date
    (6) IRB Closure to Accrual Date
    (7) Category (Interventional or Clinical Trial;  Observational Study)
    (8) Does the GDS Policy Apply
    (9) Z Number
    (10) IC'''

    # Creates a dictionary for problematic studies. The keys in the dicitonary will be the discrepancy codes as follows:
    #   - 'to_fix': these are studys that have duplicate Protocols
    #   - 'to_add': these are studies that were not found in the jiraID list
    #   - 'to_update': these are studies where one or more of the fields in Jira does not match the field in iRIS
    iRIS_items = {}

    # A list of 0's the length of the JiraID list to use as booleans later.
    matchedJiraIDs = [0] * len(JiraID)

    # Reads in the iRIS file. First saves the header row.
    with open(iRISFile, "r", encoding = "ISO-8859-1") as file:
        header = file.readline().strip().split('\t')

    # Steps through the rest of the file row by row
        for line in file.readlines():
            line = line.strip('\n').split('\t')

    # Removes the spaces at the end of the protocol ID number. I think this has stopped
    #   happening since they went to the new IRB and new numbers
            line[0] = clean_id(line[0])

    # Checks the IC column to see if it is from NCI, Do not check if the GDS Policy applies at this point
    #   because we are trying to update data on all studies that are in jira.
            if line[10] == 'NCI':
                iris_protocol_number = line[0]

        # check if the protocol number is in the jira ID list. clean_string removes amp;, trailing spaces and extra spaces in the string.
                if clean_string(iris_protocol_number) in JiraID:

        # check off Jira Protocols that are found
                    matchedJiraIDs[JiraID.index(iris_protocol_number)] = 1

        # Checks the rest of the list for the protocol number to identify duplicate protocols
        #   Searches the rest of the JiraID list from the index of the first instance + 1.
        #   If it succeeds, it calls add_item to add the protocol and data to the "to_fix" dictionary entry
                    try:
                        JiraID[JiraID.index(iris_protocol_number) + 1:].index(iris_protocol_number)
                        print("Duplicate Protocol in JIRA for: {}".format(iris_protocol_number))
                        add_item(iRIS_items, 'to_fix', line + ["Duplicate Protocol Found"])

        # If it fails to find a duplicate protocol, it checks the following fields:
        #   - Study status
        #   - which pi is listed
        #   - the zia number
        #   - the title of the study
        # I didn't compare the Jira and iRIS data for these studies because I dont know which is
        # the actual entry. It will have to be fixed and the script re-run.
                    except:

        # pulls the index of the protocl number in the JiraID list
                        protocol_index = JiraID.index(iris_protocol_number)

        # Starts a change list to track which of the Jira fields need to be updated.
                        change_list = [0, 0, 0, 0]

        # For each of the fields, it checks the entry in the iRIS table (line) against the entry in the Jira file (JiraData)
                        for i, (label, iris_value, jira_value) in enumerate(zip(['study_status', 'pi_update', 'z1a_number', 'title'],    [line[4], line[2], line[9], line[1]],  [JiraData[protocol_index][208], JiraData[protocol_index][175], JiraData[protocol_index][217], JiraData[protocol_index][2]])):

        # The study status's are not the same between the two systems so the following tree is needed to evaluate some of the edge agreement issues.
                            if i == 0:
                                if clean_string(jira_value) == 'APPROVED' and clean_string(iris_value) == 'SCIENTIFIC REVIEW - APPROVED':
                                    pass
                                elif clean_string(jira_value) == 'SUBMITTED- NOT YET APPROVED' and clean_string(iris_value) in ['PENDING', 'PENDING - PI RESPONSE TO REVIEW', 'PENDING - SUBMITTED FOR INITIAL REVIEW', 'SCIENTIFIC REVIEW SUBMITTED']:
                                    pass
                                elif clean_string(iris_value) == 'SUSPENDED' and clean_string(jira_value) in ['SUSPENDED', 'SUSPENDED BY PI']:
                                    pass
                                elif clean_string(iris_value) == jira_value.upper():
                                    pass
                                else:
                                    change_list[i] = 1

        # If the values do not match it is noted in the change list.
        #   clean_string removes amp;, trailing spaces and extra spaces in the string.
        #   add_item add the protocol and data to the dictionary under the entry labeled with the "discrepancy code"
                            else:
                                if clean_string(iris_value) != jira_value.upper():
                                    change_list[i] = 1

        # Studies that need a change are added to the 'to_update' list in the dictionary
                        if 1 in change_list:
                            add_item(iRIS_items, 'to_update', line, change_list)

        # Finally, if the study is not found in the list of JiraID's it adds the study to the dictionary under the
        #   'discrepancy code' of 'to_add'
                else:
                    if line[8] != "No":
                        add_item(iRIS_items, 'to_add', line)

    # Returns the iRIS header, the dictionary of items that need to be fixed or changed and the boolean list of JiraIDs
    return header, iRIS_items, matchedJiraIDs

def add_item(dictionary, label, item, change_list = []):
    ''' Takes a dictionary with discrepancy codes as the keys and lists of study data as the values,
        a discrepancy code, a list of study data, and a boolean list of fields requiring update.  This dictionary could be empty.

        Discrepancy codes are as follows:
        - 'to_fix': these are studys that have duplicate Protocols
        - 'to_add': these are studies that were not found in the jiraID list
        - 'to_update: these are studies where one or more of the fields in Jira does not match the field in iRIS

        Updates the dictionary to include the study and data under the correct code'''

    # Checks to see if the discrepancy code is in the dictionary already. If it is, it adds the study data to the values.
    #   The list of fields to update is added to the start of the list.
    if label in dictionary:
        dictionary[label].append(change_list + item)

    # If it is not there it adds the discrepancy code to the dicitonary with the study data in a list as the value
    else:
        dictionary[label] = [change_list + item]

def clean_id(string):
    '''takes in a string and returns the string without any spaces'''

    return re.sub(' +', '', string)

def clean_string(string):
    '''Takes a string and removes amp; or trailing spaces before removing any redundant spaces and returning the string'''

    # Removes amp; in the string or any number of trailing spaces at the end
    string = re.sub('amp;| +$', '', string)

    # Replaces instances of multiple spaces with a single space and then returns the string
    return re.sub(' +', ' ', string).upper()

def output_changes(iRIS_items, header, matchedJiraIDs, JiraData, JiraHeader):
    ''' Takes the discrepancy code dictionary generated with the read_iris function,
        the iRIS header, the boolean list of JiraIDs, the Jira Data, and the Jira Header.

        Works through the discrepancy code dictionary and the missed jira IDs, and writes
        the studys to seperate .csv files. '''

    # Steps through the discrepancy codes in the dictionary and checks if the length of the list for the
    # code is greter than zero
    for key in iRIS_items:
        if len(iRIS_items[key]) > 0:

    # Opens a new .csv file for each discrepancy code
            with open("/users/manlovelj/Desktop/iRIS_{}.csv".format(key), 'w') as file:

    # Update sheet headers
                change_list = ['study status', 'pi', 'z1a number', 'title']

    # writes the iRIS header to the sheet, adds the change list to the header if the key is to_update
                file.write(",".join(str(i) for i in (change_list + header if key == 'to_update' else header)) + "\n")

    # steps through each study in the list and writes the line to the sheet
                for line in iRIS_items[key]:
                    file.write(",".join(str(i) for i in line) + "\n")


    # Opens a .csv file for the JiraIDs that were not matched from iRIS.
    with open("/users/manlovelj/Desktop/missed_JiraIDs.csv".format(key), 'w') as file:

    # From the JiraHeader, grabs the Protocol Id (182), the study status (208), the PI (175), and the summary title (2). Writes these fields to the sheet.
        file.write("{},{},{},{}\n".format(JiraHeader[182], JiraHeader[208], JiraHeader[175], JiraHeader[2]))

    # Steps through the lists of matched jira ID booleans and the jira data.
        for i, data in zip(matchedJiraIDs, JiraData):
            try:

    # If the boolean value for the ID is not 1; the study status is not Closed, NA, or Exempt write the study data to the list.
                if not i and data[208] not in ["Closed", "N/A", "OHSR Exempt"]:
                    file.write("{},{},{},{}\n".format(data[182], data[208], data[175], data[2]))

    # If the writing of the study fails, print the data and go to the next study.
            except:
                print(data)
                pass

if __name__ == "__main__":
    JiraID, JiraData, JiraHeader = read_jira(JiraFile)
    header, iRIS_items, matchedJiraIDs = read_iris(iRISFile, JiraID, JiraData)
    output_changes(iRIS_items, header, matchedJiraIDs, JiraData, JiraHeader)
