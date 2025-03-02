import os
from fastapi import FastAPI, File, UploadFile
import json
import g4f
from fastapi.middleware.cors import CORSMiddleware
from structurebook import SmartBook
from fastapi.staticfiles import StaticFiles
import google.generativeai as genai

app = FastAPI()
try:
	genai.configure(api_key=os.environ['GEMINI_API_KEY'])
	model = genai.GenerativeModel("gemini-1.5-flash")
except:
	exit('API key not found. Please set the GEMINI_API_KEY environment variable.')

app.mount("/images", StaticFiles(directory="./StructuredBooks/images"), name="images folder")

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
response_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Title": {"type": "string"},
            "Description": {"type": "string"},
            "Category": {"type": "string"},
            "Subcategory": {"type": "string"},
            "EstimatedPrice": {"type": "string"}
        },
        "required": ["Title", "Description", "Category", "EstimatedPrice"]
    }
}
def gptresponseold(query: str):
	return g4f.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": query}])
def gptresponse(query: str):
	return model.generate_content(
		query,
		generation_config={
			'response_mime_type': 'application/json',
			# 'response_schema': response_schema
		}
		).text

@app.post("/query")
def generalquery(text: str):
	try:
		# Get the GPT response
		reply = gptresponse(f"Answer the following question response in the format {{\"text\": <text-response>}}:{text}")
		print(reply)
		parsed_data = json.loads(reply)
		return {"text": parsed_data['text']}
	# except json.JSONDecodeError as e:
	# 	return generalquery(text)
	except Exception as e:
		return {"error": str(e)}
	
@app.post("/getsummary")
def getsummary(text: str, styletokens: str = "simple language", COMPRESSIONRATIO:float =1.2):
	try:
		# Load the smartbook
		numwords = len(text.split())
		gptprompt = f"Rewrite according to the compression of the following text in English by compressing by {int(100/COMPRESSIONRATIO)}% approximately. Write in markdown format and use latex where required. Ensure the text strictly reflects the content of the text without introducing any additional information."
		# if COMPRESSIONRATIO > 4:
		# 	gptprompt = f"Summarize the key takeaways of the following text in English using the {styletokens} style. Present the summary in markdown format and use latex where required with approximately {int(numwords/COMPRESSIONRATIO)} words. Ensure the summary strictly reflects the content of the text without introducing any additional information"
		# 	# gptprompt = f"Summarize key takeaways of the following text in markdown in english in {styletokens} in {int(numwords/COMPRESSIONRATIO)} words. Ensure that no additional information (not present in the context) is added:\n\n{text}"
		# elif COMPRESSIONRATIO > 2:	
		# 	gptprompt = f"Condense the following text in English using the {styletokens} style. Present the shortened version in markdown format and use latex where required with approximately {int(numwords/COMPRESSIONRATIO)} words. Ensure no additional information beyond the original content is included"
		# 	# gptprompt = f"Shorten the following text in markdown in english in {styletokens} in {int(numwords/COMPRESSIONRATIO)} words. Ensure that no additional information (not present in the context) is added:\n\n{text}"
		# else:
		# 	gptprompt = f"Rewrite the following text in English using the {styletokens} style. Format the rewritten content in markdown and use latex where required with approximately {int(numwords/COMPRESSIONRATIO)} words. Ensure no additional information beyond the original context is included"
			# gptprompt = f"Rewrite the following text in markdown in english in {styletokens} in {int(numwords/COMPRESSIONRATIO)} words. Ensure that no additional information (not present in the context) is added:\n\n{text}"
		# Get the GPT response
		betterprompt = gptresponse(f"Re-write prompt better and shorter also reply strictly in the json format {{\"prompt\": <response>}}:\n\n {gptprompt}. Additional requirements: {styletokens}. ")
		# print(betterprompt)
		betterprompt = json.loads(betterprompt)['prompt']

		response = gptresponse(f"{betterprompt} and reply strictly in the json format {{\"reply\": <text-response>}}:\n\n{text}")
		# print(response)
		response = json.loads(response)['reply']
		
		return {"summary": response}
	except Exception as e:
		return {"error": str(e)}
	
@app.get("/listbooks")
def listbooks():
	return {"books": os.listdir('StructuredBooks')}

@app.post("/nextpiece")
def nextpiece(bookname: str, chapno: int, index: int, WORDLIMIT: int = 150):
	# Load the smartbook
	try:
		sbook = SmartBook()
		sbook.load(f'StructuredBooks/{bookname}')
		# Get the next piece
		res = sbook.getpiece(chapno, index, WORDLIMIT)
		return res
	except Exception as e:
		return {"error": str(e)}
@app.post("/prevpiece")
def prevpiece(bookname: str, chapno: int, index: int, WORDLIMIT: int = 150):
	# Load the smartbook
	try:
		sbook = SmartBook()
		sbook.load(f'StructuredBooks/{bookname}')
		# Get the next piece
		res = sbook.previouspiece(chapno, index, WORDLIMIT)
		return res
	except Exception as e:
		return {"error": str(e)}
	
@app.post("/nextpiecegpt")
def nextpiecegpt(bookname: str, chapno: int, index: int, styletokens: str = "simple language", WORDLIMIT: int = 150, COMPRESSIONRATIO:float =1.2):
	try:
		res = nextpiece(bookname, chapno, index, WORDLIMIT)
		if 'error' in res:
			return res
		piecetext = res['text']
		numwords = len(piecetext.split())

		if COMPRESSIONRATIO > 2:
			gptprompt = f"Shorten the following text in english in {styletokens} in {int(numwords/COMPRESSIONRATIO)} words. Ensure that no additional information (not present in the context) is added:\n\n{piecetext}"
		else:
			gptprompt = f"Rewrite the following text in english in {styletokens} in {int(numwords/COMPRESSIONRATIO)} words. Ensure that no additional information (not present in the context) is added:\n\n{piecetext}"
		# Get the GPT response
		reply = gptresponse(gptprompt)
		
		return {"text": reply, 'chap': res['chap'], 'ind': res['ind']}
	except Exception as e:
		return {"error": str(e)}
	
@app.post("/addbook")
def addbook(bookname: str):
	# Save the book json
	try:
		sbook = SmartBook()
		if bookname.endswith('.pdf'):
			sbook.concurrent_read_pdf("./temp/"+bookname)
		elif bookname.endswith('.epub'):
			sbook.concurrent_read_epub("./temp/"+bookname)
		else:
			return {"error": "Invalid file format"}
		sbook.save()
		return {"message": "Book added successfully", "bookname": f"{sbook.title}.json"}
	except Exception as e:
		return {"error": str(e)}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Metadata
    filename = file.filename
    content_type = file.content_type

    # Read file content (optional)
    content = await file.read()

    # Process the file as needed
    # e.g., Save the file locally
    with open(f"temp/{filename}", "wb") as f:
        f.write(content)

    return {
        "filename": filename,
        "content_type": content_type,
        "message": "File uploaded successfully!"
    }
