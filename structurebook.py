import json 
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub

def gettextfromhtml(html):
	soup = BeautifulSoup(html, 'html.parser')
	text = soup.get_text()
	return text

def read_epub(epub_path):
	# Load the EPUB file
	book = epub.read_epub(epub_path)

	text = ""
	# Print metadata (title, author, etc.)
	title = book.get_metadata('DC', 'title')
	author = book.get_metadata('DC', 'creator')
	print(f"Title: {title[0] if title else 'Unknown'}")
	print(f"Author: {author[0] if author else 'Unknown'}")

	# Extract and print the text content from each chapter
	for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
		# if item.get_type() == ebooklib.ITEM_DOCUMENT:
			# Get the HTML content
			content = item.get_body_content()
			text += '\n'+gettextfromhtml(content)  # You can also process the content as needed
		# else:
		# 	print(f"Skipping item: {item.get_type()}")
	return text

if __name__=="__main__":
	with open('StructuredBooks/bluecastle.json', 'w') as j:
		with open('BlueCastle.txt') as f:
			text = f.read()
		
		splittext = text.split('-----------------------------')
		sdict = {}
		sdict['contents'] = {}

		for i in range(len(splittext)):
			sdict['contents'][i] = [txt.strip() for txt in splittext[i].strip().split('\n\n')]
		
		json.dump(sdict, j)
