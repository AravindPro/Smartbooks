import os
from fastapi import FastAPI
import json
import g4f
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # Replace "*" with a list of specific origins in production
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
"""
Endpoints:
- Listbooks()
- Nextpiece(bookname, chapno, i)
- Nextpiecegpt(bookname, chapno, i, styletokens)
"""

def gptresponse(query: str):
	return g4f.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": query}])
	

@app.get("/listbooks")
def listbooks():
	return {"books": os.listdir('StructuredBooks')}

@app.post("/nextpiece")
def nextpiece(bookname: str, chapno: int, index: int, WORDLIMIT: int = 150):
	# Load the book json
	try:
		with open(f'StructuredBooks/{bookname}') as f:
			bookjson = json.load(f)
	except FileNotFoundError:
		# Make it return error response 404
		return {"error": "Book not found"}
	
	# Get the next piece
	inext = index
	chapnext = chapno
	try:
		piecetext = ""
		while(len(piecetext.split()) < WORDLIMIT and inext != -1 and chapnext != -1):
			piecetext += '\n'+bookjson['contents'][str(chapnext)][inext]
			if(inext+1 < len(bookjson['contents'][str(chapnext)])):
				inext = inext+1
			elif(chapnext+1 < len(bookjson['contents'])):
				inext = 0
				chapnext = chapnext+1
				break
			else:
				inext = -1
				chapnext = -1
				break
	
		return {"text": piecetext, 'chap': chapnext, 'ind': inext}
	except Exception as e:
		return {"error": str(e)}
	
@app.post("/nextpiecegpt")
def nextpiecegpt(bookname: str, chapno: int, index: int, styletokens: str, WORDLIMIT: int = 150):
	# Load the book json
	
	# try:
	# 	with open(f'StructuredBooks/{bookname}') as f:
	# 		bookjson = json.load(f)
	# except FileNotFoundError:
	# 	# Make it return error response 404
	# 	return {"error": "Book not found"}
	
	# # Get the next piece
	# inext = i
	# chapnext = chapno
	try:	
	# 	piecetext = ""
	# 	while(len(piecetext.split()) < WORDLIMIT and inext != -1 and chapnext != -1):
	# 		piecetext += '\n'+bookjson['contents'][str(chapnext)][inext]
	# 		if(inext+1 < len(bookjson['contents'][str(chapnext)])):
	# 			inext = inext+1
	# 		elif(chapnext+1 < len(bookjson['contents'])):
	# 			inext = 0
	# 			chapnext = chapnext+1
	# 			break
	# 		else:
	# 			inext = -1
	# 			chapnext = -1
	# 			break
		res = nextpiece(bookname, chapno, index, WORDLIMIT)
		if 'error' in res:
			return res
		piecetext = res['text']
		gptprompt = f"Rewrite the following text in the style of {styletokens}. Ensure that no additional information not present in the context isn't added:\n\n{piecetext}"
		# Get the GPT response
		reply = gptresponse(gptprompt)
		
		return {"text": reply, 'chap': res['chap'], 'ind': res['ind']}
	except Exception as e:
		return {"error": str(e)}