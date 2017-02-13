import argparse
import os
import locale
import cgi
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from datetime import datetime
from urlparse import urlparse
import urllib2
import sys

# index.html --> folders available
# folders/foldername.html?order=[sender|subject|date]&page=number
# emails/foldername/mid.html

folders = []
emails_in_folder = []
current_folder = ""
email_list = []
root_folder = ""
pageNumBefore = -1
reverse_list = 0
current_order = "datetime"

EMAILS_IN_PAGE = 20
PORT_NUMBER = 8080

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
<TABLE WIDTH = 100%>
<TR>
<TD><div align=right><A HREF="$$folder_name$$.html?page=$$page_number_prev$$"><-- Prev Page</a></div></TD><TD><div align=center>Page $$current_page_number$$ of $$number_of_pages$$</div></TD><TD><div align=left><A HREF="$$folder_name$$.html?page=$$page_number_next$$">Next Page --></A></div></TD>
</TR>
</TABLE>
<BR>
<TABLE WIDTH = 100%>
<TR>
<TD><H2><A HREF="$$folder_name$$.html?page=$$page_number$$&order=$$sender$$">Sender</a></H2></TD><TD><H2><A HREF="$$folder_name$$.html?page=$$page_number$$&order=subject">Subject</a></H2></TD><TD><H2><A HREF="$$folder_name$$.html?page=$$page_number$$&order=datetime">Date</a></H2></TD>
</TR>"""
FOLDER_EMAIL_DESC = """<TR>
<TD>$$sender$$</TD><TD><A HREF="../emails/$$folder_name$$/$$mid$$.html">$$subject$$</a></TD><TD>$$date$$</TD>
</TR>"""
FOLDER_FOOTER = """</TABLE>
<BR>
<A HREF="../index.html">back to folders</a>
</BODY>
</HTML>"""


EMAIL_HEADER = """<HTML>
<HEAD>
<TITLE>$$subject$$</TITLE>
</HEAD>
<BODY>"""

EMAIL_DETAILS = """<pre>$$details$$</pre><br><hr><br>"""

EMAIL_ATTACHEMENT_LIST = """<A HREF="$$attachement_url$$" target="_blank">$$attachement_name$$</a> $$attachement_type$$<BR>"""

EMAIL_TXT_ATTACHEMENT = """<HR><BR>$$txt_attachement$$"""

EMAIL_FOOTER = """</BODY>
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
            if next_line == "date":
                #Fri 10/02/2017 10:07 PM
                if sys.platform.startswith("win") or sys.platform.startswith("Win"):
                    locale.setlocale(locale.LC_TIME, "English_United States.1252")
                else:
                    locale.setlocale(locale.LC_TIME, "en_US.utf8")
                
                read_email["datetime"] = datetime.strptime(line, '%a %m/%d/%y %I:%M %p\n')

            next_line = ""

            if line.startswith("--------------------------------------------------") :      
                if read_email != {}:
                    email_list.append(read_email)
                read_email = {}
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

        summary_file.close()

    #Handler for the GET requests
    def do_GET(self):
        global current_folder
        global folders
        global emails_in_folder
        global email_list
        global pageNumBefore
        global reverse_list
        global current_order

        print self.path
        if self.path == "/index.html" or self.path == "/":
            self.send_ok_header()
            # Send the html message
            self.wfile.write(INDEX_HEADER)
            i = 0
            for folder in folders:
                text = FOLDER_DESC
                text = text.replace("$$folder_path$$", "folders/" + folder + ".html?order=datetime&page=0")
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

            order_type = ""
            try: 
                query = urlparse(self.path).query
                query_components = dict(qc.split("=") for qc in query.split("&"))
                order_type = query_components["order"]
            except KeyError:
                print "order type not found"

            same_order = False
            if order_type == "":
                order_type = current_order
            else:
                if current_order == order_type:
                    same_order = True
                current_order = order_type

            print order_type

            # order_type: date, to, from, subject
            email_list = sorted(email_list, key=lambda k: k[order_type]) 

            query = urlparse(self.path).query
            query_components = dict(qc.split("=") for qc in query.split("&"))
            pageNum = query_components["page"]

            if pageNumBefore == pageNum and same_order:
                reverse_list = reverse_list ^ 1
            
            if reverse_list == 1 : 
                email_list.reverse()

            pageNumBefore = pageNum

            prevPageNum = int(pageNum) - 1
            nextPageNum = int(pageNum) + 1
            if prevPageNum <= 0:
                prevPageNum = 0
            if nextPageNum > (num_of_emails/EMAILS_IN_PAGE):
                nextPageNum = num_of_emails/EMAILS_IN_PAGE

            self.send_ok_header()
            text = FOLDER_HEADER
            text = text.replace("$$folder_name$$", folder)
            text = text.replace("$$page_number_prev$$", str(prevPageNum))
            text = text.replace("$$page_number_next$$", str(nextPageNum))
            text = text.replace("$$page_number$$", pageNum)
            text = text.replace("$$current_page_number$$", str(int(pageNum)+1))
            text = text.replace("$$number_of_pages$$", str((num_of_emails/EMAILS_IN_PAGE)+1))

            if folder == "Sent":
                text = text.replace("$$sender$$", "to")
            else:
                text = text.replace("$$sender$$", "from")

            self.wfile.write(text)

            for email in email_list[int(pageNum)*EMAILS_IN_PAGE:int(pageNum)*EMAILS_IN_PAGE+EMAILS_IN_PAGE]:
                text = FOLDER_EMAIL_DESC
                text = text.replace("$$folder_name$$", folder)
                if folder != "Sent":
                    text = text.replace("$$sender$$", cgi.escape(email["from"]))
                else:
                    text = text.replace("$$sender$$", cgi.escape(email["to"]))
                text = text.replace("$$mid$$", cgi.escape(email["mid"]))
                text = text.replace("$$subject$$", cgi.escape(email["subject"]))
                text = text.replace("$$date$$", cgi.escape(email["date"]))
                self.wfile.write(text)

            self.wfile.write(FOLDER_FOOTER)

        elif self.path.startswith("/emails/"):
            self.send_ok_header()
            email_path = root_folder + "/" + self.path.replace("/emails", "")
            email_path = email_path.replace(".html", "")

            path_list = self.path.split("/")
            print path_list
            folder = path_list[2]
            for elem in path_list:
                if elem.endswith(".html"):
                    mid = elem.replace(".html", "")
                    break
            if folder != current_folder:
                # regenerate email list
                email_list = []
                self.getEmailList(folder)
                current_folder = folder

            text = EMAIL_HEADER
            for email in email_list:
                print email
                if int(email["mid"]) == int(mid):
                    text = text.replace("$$subject$$", email["subject"])
            
            self.wfile.write(text)

            print email_path
            content =""
            with open(email_path+"/emailHeader", 'r') as content_file:
                content = content_file.read()

            print content
            text = EMAIL_DETAILS
            text = text.replace("$$details$$", cgi.escape(content))

            self.wfile.write(text)
 
            attachement_file = open(email_path+"/emailAttachements", 'rb')


            # <A HREF="$$attachement_url$$" target="_blank">$$attachement_name$$</a> $$attachement_type$$<BR>
            attachement_list = []
            attachement_desc = {}
            line_num = 0
            for line in attachement_file:
                if line_num == 2 and not line.isspace():
                    line_num = 0

                if line_num == 0:
                    attachement_desc["name"] = line
                elif line_num == 1:
                    attachement_desc["type"] = line
                    print attachement_desc
                    attachement_list.append(attachement_desc)
                    attachement_desc = {}
                elif line_num == 2:
                    line_num = -1

                line_num = line_num + 1

            print attachement_list
            for attachement in attachement_list:
                text = EMAIL_ATTACHEMENT_LIST
                text = text.replace("$$attachement_url$$", "../../attachements" + email_path.replace(root_folder, "") + "/" + attachement["name"])
                text = text.replace("$$attachement_name$$", attachement["name"])
                text = text.replace("$$attachement_type$$", attachement["type"])
                self.wfile.write(text)


            
            for attachement in attachement_list:

#EMAIL_TXT_ATTACHEMENT = """<HR><BR>$$txt_attachement$$"""

                print attachement["type"]
                if attachement["type"].startswith("text/plain"):
                    text = EMAIL_TXT_ATTACHEMENT
                    path = email_path + "/" + attachement["name"]
                    path = urllib2.unquote(path).strip()
                    print path
                    if os.path.exists(path):
                        file = open(path, "rb")
                        text = text.replace("$$txt_attachement$$", "<pre>" + file.read() + "</pre>")
                        file.close()
                    self.wfile.write(text)
                elif attachement["type"].startswith("text/html"):
                    text = EMAIL_TXT_ATTACHEMENT
                    text = text.replace("$$txt_attachement$$", "<iframe width=100%% height=600 src=" + "\"../../embeddedhtml" + email_path.replace(root_folder, "") + "/" + attachement["name"] + "\"><p>Your browser does not support iframes.</p></iframe>")
                    self.wfile.write(text)
                elif attachement["type"].startswith("image"):
                    text = EMAIL_TXT_ATTACHEMENT
                    text = text.replace("$$txt_attachement$$", "<img width=50%% src=" + "\"../../embeddedhtml" + email_path.replace(root_folder, "") + "/" + attachement["name"] + "\"></img>")
                    self.wfile.write(text)


            self.wfile.write(EMAIL_FOOTER)

        elif self.path.startswith("/attachements") or self.path.startswith("/embeddedhtml"):
            path = self.path.replace("/attachements", root_folder)
            path = path.replace("/embeddedhtml", root_folder)
            path = urllib2.unquote(path)
            path = path.split("@", 1)[0]
            
            if os.path.exists(path):
                file = open(path, "rb")
    #note that this potentially makes every file on your computer readable by the internet
                self.send_response(200)
                
                file_contents = file.read()
                
                if self.path.startswith("/embeddedhtml"):
                    print "html embedded"
                    self.send_header('Content-type','text/html')
                    file_contents = file_contents.replace("src=\"cid:", "src=\"")
                    file_contents = file_contents.replace("src='cid:", "src='")
                else:
                    self.send_header('Content-type',    'application/octet-stream')
                    self.send_header('Content-Disposition',    'attachment')
                self.end_headers()
                self.wfile.write(file_contents)
                file.close()
        else:
            print "Unhandled request: " +self.path

parser = argparse.ArgumentParser()
parser.add_argument("--folder", help="Folder name")
args = parser.parse_args()

if args.folder:
    arg_folder = args.folder
else:
    arg_folder = "."
    
for file in os.listdir(arg_folder):
    if os.path.isdir(arg_folder + "/" + file):
        folders.append(file)

root_folder = arg_folder

for folder in folders:
    emails = 0
    for file in os.listdir(arg_folder+ "/" + folder):
        if os.path.isdir(arg_folder+ "/" + folder + "/" + file):
            emails = emails + 1
    emails_in_folder.append(emails)

print folders
print emails_in_folder



#Create a web server and define the handler to manage the
#incoming request
server = HTTPServer(('127.0.0.1', PORT_NUMBER), myHandler)
print 'Started httpserver on port ' , PORT_NUMBER

#Wait forever for incoming htto requests
server.serve_forever()


