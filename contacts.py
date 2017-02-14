import argparse





parser = argparse.ArgumentParser()
parser.add_argument("in_file", help="contacts file name")
parser.add_argument("out_file", help="contacts file name")
args = parser.parse_args()


contacts_file = open(args.in_file, 'rb')


email_list = []
for line in contacts_file:
    email_list.append(line.split())
    print email_list

contacts_file.close()

contacts_file_out = open(args.out_file, 'wb')

contacts_file_out.write("Name,Given Name,Additional Name,Family Name,Yomi Name,Given Name Yomi,Additional Name Yomi,Family Name Yomi,Name Prefix,Name Suffix,Initials,Nickname,Short Name,Maiden Name,Birthday,Gender,Location,Billing Information,Directory Server,Mileage,Occupation,Hobby,Sensitivity,Priority,Subject,Notes,Group Membership,E-mail 1 - Type,E-mail 1 - Value,E-mail 2 - Type,E-mail 2 - Value,E-mail 3 - Type,E-mail 3 - Value,Phone 1 - Type,Phone 1 - Value,Phone 2 - Type,Phone 2 - Value,Phone 3 - Type,Phone 3 - Value,Address 1 - Type,Address 1 - Formatted,Address 1 - Street,Address 1 - City,Address 1 - PO Box,Address 1 - Region,Address 1 - Postal Code,Address 1 - Country,Address 1 - Extended Address,Organization 1 - Type,Organization 1 - Name,Organization 1 - Yomi Name,Organization 1 - Title,Organization 1 - Department,Organization 1 - Symbol,Organization 1 - Location,Organization 1 - Job Description,Website 1 - Type,Website 1 - Value    ")
contacts_file_out.write("\n")

for elem in email_list:
    print elem
    name = ""
    for t in elem[:-1]:
        name = name + t
        name = name + " "

    contacts_file_out.write(name)
    contacts_file_out.write(",")
    contacts_file_out.write(name)
    contacts_file_out.write(",,,,,,,,,,,,,,,,,,,,,,,,,,* ,")
    contacts_file_out.write(elem[-1])
    contacts_file_out.write(",,,,,,,,,,,,,,,,,,,,,,,,,,,,,")
    contacts_file_out.write("\n")

contacts_file_out.close()
