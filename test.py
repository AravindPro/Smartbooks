import json
import requests


URL = "http://127.0.0.1:8000"
ind = 0
chapno = 0
bookname = 'bluecastle.json'
styletokens = "fastpaced,simple language"
while ind != -1 and chapno != -1:
	response = requests.get(f"{URL}/nextpiecegpt?bookname={bookname}&chapno={chapno}&i={ind}&styletokens={styletokens}")
	data = response.json()

	if ((response.status_code==200) and ('error' not in data)):
		print(data['text'])

		inp = input("Retry (r), next piece (n), or quit (q): ")
		if inp == 'q':
			break
		elif inp == 'r':
			continue
		elif inp == 'n':			
			ind = data['ind']
			chapno = data['chap']
		else:
			print("Invalid input")
			break
	else:
		print("Error: ", data)
		break
