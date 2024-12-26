from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
from pathlib import Path
import re
import threading 
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
from nltk.tokenize import TextTilingTokenizer
import nltk 
import pdfplumber
from pypdf import PdfReader
import g4f
from PIL import Image
import markdownify

nltk.download('stopwords')

def gettextfromhtml(html):
	soup = BeautifulSoup(html, 'html.parser')
	text = soup.get_text()
	return text

def getmdfromxml(xml):
	soup = BeautifulSoup(xml, 'html.parser')
	try:
		text = markdownify.markdownify(str(soup.html))
		
	except Exception as e:
		text = soup.get_text()

	return text


def getimagespathsfromhtml(html):
	soup = BeautifulSoup(html, 'html.parser')
	images = soup.find_all('img')
	return list(map(lambda i: i['src'], images))

def clean_text(text):
	cleaned_text = re.sub(r'[^\x20-\x7E]', '', text)
	return cleaned_text


def smart_markdownify(text):
    lines = text.split('\n')
    markdown = []
    for line in lines:
        if line.strip().endswith(":"):  # Treat as heading
            markdown.append(f"## {line.strip()}")
        elif line.strip().startswith("-"):  # Treat as list
            markdown.append(f"- {line.strip()[2:]}")
        else:  # Treat as paragraph
            markdown.append(line.strip())
    return "\n\n".join(markdown)

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
			content = chapter.content
			text = getmdfromxml(content)  # Process the content as needed

			def replacer(match):
				original_alt = match.group(1)
				original_link = match.group(2)
				# print(original_alt, original_link)
				basename = os.path.basename(original_link)
				newlink = f'./images/{self.title}/{basename}'
				return f"![{original_alt}]({newlink})"

			# Replace the text image paths with actual image paths
			image_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
			text = re.sub(image_pattern, replacer, text)


			imagepaths = getimagespathsfromhtml(content)
			basenames = []
			# Open and save the images
			for imgpath in imagepaths:
				normpath = os.path.normpath(imgpath)
				cleanpath = os.path.relpath(normpath, os.pardir).replace('\\', '/')
				basename = os.path.basename(imgpath)
				# print(cleanpath, basename)
				epubimage = book.get_item_with_href(cleanpath)
				if epubimage is not None:
					img = Image.open(io.BytesIO(epubimage.content))
					img.save(f'{Path(__file__).parent}/StructuredBooks/images/{self.title}/{basename}')
					basenames.append(basename)
				else:
					print("Image not found: ", imgpath)

			try:
				return str(pageno), list(map(lambda i: i.strip(), tokenizer.tokenize(text)))
			except Exception as e:
				return str(pageno), [text.strip(),]+basenames
		# Load the EPUB file
		book = epub.read_epub(epub_path)
		tokenizer = TextTilingTokenizer()

		# Print metadata (title, author, etc.)
		title = book.get_metadata('DC', 'title')
		author = book.get_metadata('DC', 'creator')

		self.title = epub_path.split('/')[-1].split('.')[0].replace(' ', '_')
		os.makedirs(f'{Path(__file__).parent}/StructuredBooks/images/{self.title}', exist_ok=True)
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
		imagecounter = 0
		imagecounter_lock = threading.Lock()
		tokenizer = TextTilingTokenizer()
		
		def process_page(page):
			text = page.extract_text()
			images = page.images
			nonlocal imagecounter
			lstimages=[]
			with imagecounter_lock:  # Ensure only one thread modifies imagecounter at a time
				for img in images:
					imagecounter += 1
					lstimages.append(f'![](./images/{self.title}/image_{imagecounter}.png)')
					try:
						img.image.save(f'{Path(__file__).parent}/StructuredBooks/images/{self.title}/image_{imagecounter}.png', 'PNG')
					except Exception as e:
						print(f"Error saving image {imagecounter}: ", e)
			
			try:
				return list(map(lambda i: smart_markdownify(clean_text(i.strip())), tokenizer.tokenize(text)))+lstimages
			except Exception as e:
				return [smart_markdownify(clean_text(text.strip())),]+lstimages
		
		# Extract book name
		self.title = pdf_path.split('/')[-1].split('.')[0].replace(' ', '_')
		print(self.title)
		# os.makedirs(f'{Path(__file__).parent}/StructuredBooks/{self.title}', exist_ok=True)
		os.makedirs(f'{Path(__file__).parent}/StructuredBooks/images/{self.title}', exist_ok=True)
		print(self.title)
		self.bookjson['contents']["0"] = []
		# with pdfplumber.open(pdf_path) as pdf:
		reader = PdfReader(pdf_path)

		with ThreadPoolExecutor() as executor:
			results = executor.map(process_page, reader.pages)
		# print(results)
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
	
	def getpiece(self, chapterno, index, WORDLIMIT=200, splittext='\n\n'):
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

		while ((len(piecetext.split())+len(self.bookjson['contents'][str(chapnext)][inext].split()) < WORDLIMIT) and inext != -1 and chapnext != -1):
			piecetext += splittext+self.bookjson['contents'][str(chapnext)][inext]
			if (inext+1 < len(self.bookjson['contents'][str(chapnext)])):
				inext = inext+1
			elif (chapnext+1 < len(self.bookjson['contents'])):
				inext = 0
				chapnext = chapnext+1
			else:
				inext = -1
				chapnext = -1
				break
		return {"text": piecetext, 'chap': chapnext, 'ind': inext}
		
	def previouspiece(self, chapterno, index, WORDLIMIT=200, splittext='\n'):
		chapprev = chapterno
		iprev = index
		if iprev > 0:
			iprev -= 1
		elif chapprev > 0:
			chapprev -= 1
			iprev = len(self.bookjson['contents'][str(chapprev)]) - 1
		else:
			iprev = -1
			chapprev = -1
			return {"text": "", 'chap': chapprev, 'ind': iprev}
		
		piecetext = self.bookjson['contents'][str(chapprev)][iprev]

		if iprev > 0:
			iprev -= 1
		elif chapprev > 0:
			chapprev -= 1
			iprev = len(self.bookjson['contents'][str(chapprev)]) - 1
		else:
			iprev = -1
			chapprev = -1
			return {"text": piecetext, 'chap': chapprev, 'ind': iprev}

		while (len(piecetext.split()) + len(self.bookjson['contents'][str(chapprev)][iprev].split()) < WORDLIMIT 
			and iprev != -1 and chapprev != -1):
			piecetext = self.bookjson['contents'][str(chapprev)][iprev] + splittext + piecetext
			if iprev > 0:
				iprev -= 1
			elif chapprev > 0:
				chapprev -= 1
				iprev = len(self.bookjson['contents'][str(chapprev)]) - 1
				break
			else:
				iprev = -1
				chapprev = -1
				break
		return {"text": piecetext, 'chap': chapprev, 'ind': iprev}


if __name__=="__main__":
	pdf_path = './temp/CPH.pdf'
	book = SmartBook()
	# book.load('StructuredBooks/aibook.json')
	book.concurrent_read_pdf(pdf_path)
	book.save()
	# print(book.bookjson)
	# text = book.getpiece(0, 0, WORDLIMIT=1000)['text']
	# print(text)
	# print('------------------------')
	# query = f"Shorten the following in simple language in english with little bit of excitement within {len(text.split())/3} words: \n\n{text}"

	# reply = g4f.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": query}])
	# print(f"Original size: {len(text.split())}, New: {len(reply.split())}")
	# print(reply)
