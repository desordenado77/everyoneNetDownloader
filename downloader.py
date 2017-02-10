# Everyone.net email downloader tool. Tested with http://www.demadrid.com
# based on the work done here: http://www.perlmonks.org/bare/?node_id=529064 
# How To install all the required components:
#   install python
#   install npm
#   install pip
#   install selenium: sudo pip install selenium
#   install chrome web driver: sudo npm install chromedriver
#   set path to chromedriver binary: export PATH=$PATH:$PWD/node_modules/chromedriver/bin/ #assuming you did not change to a different folder from when you did the npm

import csv
import os
import argparse
import sys
import shutil
import time
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


parser = argparse.ArgumentParser()
parser.add_argument("user", help="Username")
parser.add_argument("password", help="Password")
parser.add_argument("folder", help="email folder")
parser.add_argument("--midFile", help="Message ID list file. You can use the midFailed.csv file to reattempt failed messages")
args = parser.parse_args()

base = "http://demadrid.mail.everyone.net/email/scripts"
basefw = "http://demadrid.mail.everyone.net/eonapps/ft/wm/page/compose"
loginuser = base + "/loginuser.pl"
folder = args.folder
tempFolder = "./temp"

# generate mid sequence array if it was provided
midSeqArray = []
if args.midFile:
    print "Mid File provided "+args.midFile + ". Reading file contents"
    with open(args.midFile, 'rb') as csvfile:
        midreader = csv.reader(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for row in midreader:
            midSeqArray.extend(row)

# create download folder
if os.path.exists(tempFolder):
	shutil.rmtree(tempFolder)
os.makedirs(tempFolder)

# start web driver
chromeOptions = webdriver.ChromeOptions()    
prefs = {"download.default_directory" : tempFolder}
chromeOptions.add_experimental_option("prefs",prefs)
browser = webdriver.Chrome(chrome_options=chromeOptions)      

# log in
browser.get(loginuser)
loginName = browser.find_element_by_name("loginName")
loginName.send_keys(args.user)
password = browser.find_element_by_name("user_pwd")
password.send_keys(args.password)

browser.find_element_by_name("login").click()

# go to inbox
main = base + "/main.pl?folder=" + folder
browser.get(main)

# find magic
print "Finding Magic"
html = browser.page_source
magicStr = "document.myForm.action = 'main.pl?EV1="
start = html.find( magicStr )
end = html.find("'", start+len(magicStr))
magicId = html[start+len(magicStr):end]
print "Found " + magicId

#create results folder
if not os.path.exists("./" + folder):
    os.makedirs("./" + folder)

if not args.midFile:
    print "Finding Mid Sequence"
    #find midSeq
    midSeqStr = "<input type=\"hidden\" name=\"midseq\" value=\""
    start = html.find( midSeqStr )
    end = html.find("\"", start+len(midSeqStr))
    midSeq = html[start+len(midSeqStr):end]
    print "Found"
    midSeqArray = midSeq.split(".")
    print "Writing Mid Sequence"
    with open("./" + folder + "/midAll.csv", 'wb') as csvfile:
        midwriter = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
        midwriter.writerow(midSeqArray)
else:
    print "Using Sequence " + str(midSeqArray)

success_mids = 0
fail_mids = 0
attachements_downloaded = 0

# go through all emails in mid sequence array
for mid in midSeqArray:
    try: 
        print "Mid: " + mid
        print "Done: " + str(success_mids + fail_mids) + " from " + str(len(midSeqArray))
        browser.execute_script("View('" + mid + "');")

        midFolderName = "./" + folder + "/" + mid
        if not os.path.exists(midFolderName):
            os.makedirs(midFolderName)        

        # generate email header
        header_file = open(midFolderName + "/emailHeader", 'w')
        summary_file = open("./" + folder + "/summary", 'a')
        summary_file.write("--------------------------------------------------\n")
        summary_file.write("Message ID: " + mid +"\n")
        table =  browser.find_element_by_xpath("/html/body/table/tbody/tr[2]/td[1]/table[3]/tbody/tr[3]/td/table[3]/tbody/tr[2]/td/table/tbody/tr/td[1]")
        for row in table.find_elements_by_xpath(".//tr"):
            for td in row.find_elements_by_xpath(".//td[text()]"):
                header_file.write(td.text.encode('utf-8') + "\n")
                summary_file.write(td.text.encode('utf-8') + "\n")
        header_file.close()
        summary_file.close()        
        
        # find attachements, including email parts
        elems = browser.find_elements_by_link_text("Save")

        print "elements:"
        for elem in elems:
            print elem.get_attribute("href")
        print "done"
        
        # remove duplicates        
        # this is not working, because the duplicate is on the href not on the element itself
        # elems = list(set(elems))
        for elem in elems:
            href_txt = elem.get_attribute("href")
            for other_elem in elems:
                if other_elem != elem:
                    other_href_txt = other_elem.get_attribute("href")
                    if href_txt == other_href_txt:
                        elems.remove(other_elem)
                        print "Removing duplicate file: " + other_href_txt    
        
        files_to_download = 0
        for elem in elems:
            # download attachements, including email parts
            elem.click()
            files_to_download = files_to_download + 1
	        # print elem.get_attribute("href")
        
        if files_to_download != 0:
            counter = 0
            while len(os.listdir(tempFolder)) != files_to_download:
                time.sleep(2)
                counter = counter + 1
                if counter >= 300: # sleeping 2 seconds this is 10 minutes
                    #exception handler will catch it and write to the list of failed mids for later retry if desired
                    raise Exception('Waiting for too long to get all files in folder') 
            
            crdownload_not_found = 1
            counter = 0
            while crdownload_not_found:
                time.sleep(2)
                crdownload_not_found = 0
                for file in os.listdir(tempFolder):
                    if file.endswith(".crdownload"):
                        crdownload_not_found = 1
                        if (counter % 10) == 0:
                            print "partial file found... sleeping"
                        break

                counter = counter + 1
                if counter >= 3600: # sleeping 2 hours for full download of everything. It is a huge amount of time, but better safe than sorry in case speed goes down eventually.
                    #exception handler will catch it and write to the list of failed mids for later retry if desired
                    raise Exception('Waiting for too long to have files downloaded') 
        
            for filename in os.listdir(tempFolder):
                origin = tempFolder + "/" + filename.decode('utf-8')
                destination = midFolderName + "/" + filename.decode('utf-8')
                shutil.move(origin, destination)            
                attachements_downloaded = attachements_downloaded + 1

            # find attachements names, including email parts       
            attachement_file = open(midFolderName + "/emailAttachements", 'w')
            table =  browser.find_element_by_xpath("/html/body/table/tbody/tr[2]/td[1]/table[3]/tbody/tr[3]/td/table[3]/tbody/tr[2]/td/table/tbody/tr/td[2]/table/tbody/tr[2]/td/table/tbody/tr/td")      
            counter = 0
            for row in table.find_elements_by_xpath(".//tr"):
                for td in row.find_elements_by_xpath(".//td[text()]"):
                    if counter > 3: 
                        attachement_file.write(td.text.encode('utf-8') + "\n")
                    counter = counter + 1
            attachement_file.close()  # you can omit in most cases as the destructor will call it

        # Get the actual displayed webpage source with full headers.
        # Having all the other content this is really unnecesary, but just in case I missed something on the other steps. Better safe than sorry
        # Since it is kind of redundant, I am ignoring errors here. There could be errors from the encoding to utf-8 (most likely), so I ignore those.
        try:
            browser.execute_script("ToggleHeaders();")
            html = browser.page_source
            browser.execute_script("ToggleHeaders();")
            webpage_file = open(midFolderName + "/emailSource.html", 'w')
            webpage_file.write(html.encode('utf-8'))
            webpage_file.close()
        except Exception as e: 
            print "Error Occurred while full header file download of MID " + mid + ": " + str(e)
            
        with open("./" + folder + "/midSuccess.csv", 'ab') as csvfile:
            midwriter = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
            midwriter.writerow([mid])  
            
        success_mids = success_mids + 1
    except Exception as e: 
        fail_mids = fail_mids + 1
        print "Error Occurred while doing MID " + mid + ": " + str(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)        
        
        with open("./" + folder + "/midFailed.csv", 'ab') as csvfile:
            midwriter = csv.writer(csvfile, delimiter=',',quotechar='|', quoting=csv.QUOTE_MINIMAL)
            midwriter.writerow([mid])                    

	# remove and create again download folder
        if os.path.exists(tempFolder):
            shutil.rmtree(tempFolder)
        os.makedirs(tempFolder)            
            
browser.quit()        
print "-----------------------------------------------------"            
print "Ammount of emails: " + str(len(midSeqArray))
print "Processed successfuly: " + str(success_mids)
print "Processed with failures: " + str(fail_mids)
print "Attachements Downloaded: " + str(attachements_downloaded)
print "-----------------------------------------------------"

