from concurrent.futures import ThreadPoolExecutor
import json 
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
from nltk.tokenize import TextTilingTokenizer
import pdfplumber
from pypdf import PdfReader
import g4f

def gettextfromhtml(html):
	soup = BeautifulSoup(html, 'html.parser')
	text = soup.get_text()
	return text

class SmartBook:
	def __init__(self):
		self.bookjson = {"contents": {}}
		self.title = ""
	def load(self, filename):
		with open(filename) as f:
			self.bookjson = json.load(f)
			self.title = filename.split('/')[-1].split('.')[0]
	def save(self):
		with open(f'StructuredBooks/{self.title}.json', 'w') as f:
			json.dump(self.bookjson, f, indent=4)
	def concurrent_read_epub(self, epub_path):
		def process_chapter(args):
			pageno, chapter = args
			content = chapter.get_body_content()
			text = gettextfromhtml(content)  # Process the content as needed
			try:
				return str(pageno), list(map(lambda i: i.strip(), tokenizer.tokenize(text)))
			except Exception as e:
				return str(pageno), [text.strip(),]
		# Load the EPUB file
		book = epub.read_epub(epub_path)
		tokenizer = TextTilingTokenizer()

		# Print metadata (title, author, etc.)
		title = book.get_metadata('DC', 'title')
		author = book.get_metadata('DC', 'creator')

		self.title = epub_path.split('/')[-1].split('.')[0].replace(' ', '_')
		chapters = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
		# Extract and print the text content from each chapter
		
		with ThreadPoolExecutor() as executor:
			results = executor.map(process_chapter, enumerate(chapters))

		for pageno, tokens in results:
			self.bookjson['contents'][pageno] = tokens

	def read_epub(self, epub_path):
		# Load the EPUB file
		book = epub.read_epub(epub_path)
		tokenizer = TextTilingTokenizer()

		# Print metadata (title, author, etc.)
		title = book.get_metadata('DC', 'title')
		author = book.get_metadata('DC', 'creator')

		self.title = title[0] if title else 'Unknown'

		chapters = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
		# Extract and print the text content from each chapter
		for pageno, chapter in enumerate(chapters):
			# if item.get_type() == ebooklib.ITEM_DOCUMENT:
				# Get the HTML content
				content = chapter.get_body_content()
				text = gettextfromhtml(content)  # You can also process the content as needed
				try:
					self.bookjson['contents'][str(pageno)] = list(map(lambda i: i.strip(), tokenizer.tokenize(text)))
				except Exception as e:
					self.bookjson['contents'][str(pageno)] = [text.strip(),]
	def concurrent_read_pdf(self, pdf_path):
		def process_page(page):
			text = page.extract_text()
			try:
				return list(map(lambda i: i.strip(), tokenizer.tokenize(text)))
			except Exception as e:
				return [text.strip(),]
		tokenizer = TextTilingTokenizer()

		# Extract book name
		self.title = pdf_path.split('/')[-1].split('.')[0].replace(' ', '_')

		self.bookjson['contents']["0"] = []
		# with pdfplumber.open(pdf_path) as pdf:
		reader = PdfReader(pdf_path)
		with ThreadPoolExecutor() as executor:
			results = executor.map(process_page, reader.pages)
		for splitpage in results:
			self.bookjson['contents']["0"].extend(splitpage)
	def read_pdf(self, pdf_path: str):

		tokenizer = TextTilingTokenizer()
		self.bookjson['contents']["0"] = []
		reader = PdfReader(pdf_path)

		# getting a specific page from the pdf file
		# page = reader.pages[0]

		# extracting text from page
		# text = page.extract_text()
		# with pdfplumber.open(pdf_path) as pdf:
		for page in reader.pages:
			text = page.extract_text()
			try:
				textsections = tokenizer.tokenize(text)
				self.bookjson['contents']["0"].extend(textsections)
			except Exception as e:
				self.bookjson['contents']["0"].append(text)
	
	def getpiece(self, chapterno, index, WORDLIMIT=200, splittext='\n'):
		chapnext = chapterno
		inext = index
		piecetext = self.bookjson['contents'][str(chapnext)][inext]
		if (inext+1 < len(self.bookjson['contents'][str(chapnext)])):
			inext = inext+1
		elif (chapnext+1 < len(self.bookjson['contents'])):
			inext = 0
			chapnext = chapnext+1
		else:
			inext = -1
			chapnext = -1

		while (len(piecetext.split())+len(self.bookjson['contents'][str(chapnext)][inext].split()) < WORDLIMIT and inext != -1 and chapnext != -1):
			piecetext += splittext+self.bookjson['contents'][str(chapnext)][inext]
			if (inext+1 < len(self.bookjson['contents'][str(chapnext)])):
				inext = inext+1
			elif (chapnext+1 < len(self.bookjson['contents'])):
				inext = 0
				chapnext = chapnext+1
				break
			else:
				inext = -1
				chapnext = -1
				break
		return {"text": piecetext, 'chap': chapnext, 'ind': inext}
		
	


if __name__=="__main__":
	# pdf_path = 'temp/llmpaper.pdf'
	book = SmartBook()
	book.load('StructuredBooks/llmpaper.json')
	# book.concurrent_read_pdf(pdf_path)
	# book.save()
	# print(book.bookjson)
	text = book.getpiece(0, 0, WORDLIMIT=1000)['text']
	print(text)
	print('------------------------')
	query = f"Shorten the following in simple language in english with little bit of excitement within {len(text.split())/3} words: \n\n{text}"

	reply = g4f.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": query}])
	print(f"Original size: {len(text.split())}, New: {len(reply.split())}")
	print(reply)
