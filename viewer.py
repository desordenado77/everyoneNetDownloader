import argparse
import os
import locale
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from datetime import datetime
from urlparse import urlparse


# index.html --> folders available
# folders/foldername.html?order=[sender|subject|date]&page=number
# emails/foldername/mid.html

folders = []
emails_in_folder = []
current_folder = ""
email_list = []
root_folder = ""

EMAILS_IN_PAGE = 20

INDEX_HEADER = """<HTML>
<HEAD>
<TITLE>Folders</TITLE>
</HEAD>
<BODY>
<H1>Folders:<BR></H1>
<BR>
<TABLE WIDTH = 50%>"""

INDEX_FOOTER = """</TABLE>
</BODY>
</HTML>"""

FOLDER_DESC = """<TR>
<TD><A HREF="$$folder_path$$">$$folder_name$$</a></TD>
<TD>$$folder_emails$$ emails</TD>
</TR>"""


FOLDER_HEADER = """<HTML>
<HEAD>
<TITLE>$$folder_name$$</TITLE>
</HEAD>
<BODY>
<H1>$$folder_name$$:<BR></H1>
<BR>
<TABLE WIDTH = 50%>
<TR>
<TD><A HREF="$$folder_name$$.html?page=$$page_number_prev$$"><-- Prev Page</a></TD><TD><A HREF="$$folder_name$$.html?page=$$page_number_next$$">Next Page --></A></TD>
</TR>
</TABLE>
<BR>
<TABLE WIDTH = 50%>
<TR>
<TD><H2>Sender</H2></TD><TD><H2>Subject</H2></TD><TD><H2>Date</H2></TD>
</TR>"""
FOLDER_EMAIL_DESC = """<TR>
<TD>$$sender$$</TD><TD><A HREF="emails/$$folder_name$$/$$mid$$" target="_blank">$$subject$$</a></TD><TD>$$date$$</TD>
</TR>"""
FOLDER_FOOTER = """</TABLE>
<BR>
<A HREF="../index.html">back to folders</a>
</BODY>
</HTML>"""


#This class will handles any incoming request from
#the browser 
class myHandler(BaseHTTPRequestHandler):
    def send_ok_header(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()

    def getEmailList(self, folder):
        global email_list
        summary_file = open("./" + root_folder + "/" + folder + "/summary", 'rb')

        read_email = {}

        next_line = ""
        for line in summary_file:
            if next_line != "":
                read_email[next_line] = line
#            if next_line == "date":
#                #Fri 10/02/2017 10:07 PM
#                locale.setlocale(locale.LC_TIME, "en_US.utf8")
#                read_email["datetime"] = datetime.strptime(line, '%a %d/%m/%y %I:%M %p\n')

            next_line = ""

            if line == "--------------------------------------------------" :
                if read_email != []:
                    email_list.append(read_email)
            elif line.startswith("Message ID: "):
                read_email["mid"] = line.replace("Message ID: ", "")
            elif line.startswith("From:"):
                next_line = "from"
            elif line.startswith("To:"):                
                next_line = "to"
            elif line.startswith("Subject:"):                
                next_line = "subject"
            elif line.startswith("Date:"):                
                next_line = "date"

    #Handler for the GET requests
    def do_GET(self):
        global current_folder
        global folders
        global emails_in_folder
        global email_list

        print self.path
        if self.path == "/index.html" or self.path == "/":
            self.send_ok_header()
            # Send the html message
            self.wfile.write(INDEX_HEADER)
            i = 0
            for folder in folders:
                text = FOLDER_DESC
                text = text.replace("$$folder_path$$", "folders/" + folder + ".html?order=date&page=0")
                text = text.replace("$$folder_name$$", folder)
                text = text.replace("$$folder_emails$$", str(emails_in_folder[i]))
                self.wfile.write(text)
                i = i + 1
            self.wfile.write(INDEX_FOOTER)
            return
        elif self.path.startswith("/folders/"):
            #handle folders
            folderName = self.path.replace("/folders/", "")
            folder = ""
            for folder_iter in folders:
                if folderName.startswith(folder_iter):
                    folder = folder_iter
                    break

            if folder != current_folder:
                # regenerate email list
                email_list = []
                self.getEmailList(folder)
                current_folder = folder

            num_of_emails = len(email_list)

            print email_list

            query = urlparse(self.path).query
            query_components = dict(qc.split("=") for qc in query.split("&"))
            pageNum = query_components["page"]

            prevPageNum = int(pageNum) - 1
            nextPageNum = int(pageNum) + 1
            if pageNum <= 0:
                prevPageNum = 0
            if nextPageNum > (num_of_emails/EMAILS_IN_PAGE):
                nextPageNum = num_of_emails/EMAILS_IN_PAGE
# query_components = { "imsi" : "Hello" }
            self.send_ok_header()
            text = FOLDER_HEADER
            text = text.replace("$$folder_name$$", folder)
            text = text.replace("$$page_number_prev$$", str(prevPageNum))
            text = text.replace("$$page_number_next$$", str(nextPageNum))
            self.wfile.write(text)

            for email in email_list[int(pageNum)*EMAILS_IN_PAGE:int(pageNum)*EMAILS_IN_PAGE+EMAILS_IN_PAGE]:
                text = FOLDER_EMAIL_DESC
                text = text.replace("$$folder_name$$", folder)
                text = text.replace("$$mid$$", email["mid"])
                text = text.replace("$$subject$$", email["subject"])
                text = text.replace("$$date$$", email["date"])
                self.wfile.write(text)

            self.wfile.write(FOLDER_FOOTER)

        elif self.path.startswith("/emails/"):    
            #handle emails
            print "email here"



parser = argparse.ArgumentParser()
parser.add_argument("folder", help="Folder name")
args = parser.parse_args()

for file in os.listdir(args.folder):
    if os.path.isdir(args.folder + "/" + file):
        folders.append(file)

root_folder = args.folder

for folder in folders:
    emails = 0
    for file in os.listdir(args.folder+ "/" + folder):
        if os.path.isdir(args.folder+ "/" + folder + "/" + file):
            emails = emails + 1
    emails_in_folder.append(emails)

print folders
print emails_in_folder


PORT_NUMBER = 8080

#Create a web server and define the handler to manage the
#incoming request
server = HTTPServer(('', PORT_NUMBER), myHandler)
print 'Started httpserver on port ' , PORT_NUMBER

#Wait forever for incoming htto requests
server.serve_forever()


