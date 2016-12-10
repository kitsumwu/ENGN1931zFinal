import requests
import re
import sys

#########################################
#get request
#########################################
RequestHandler = 'https://script.google.com/macros/s/AKfycbzKd21q-iio_d0EZPva1Dr84wGOXwayr0GDmlM8U7UQ0GEs9vqS/exec'
Request = requests.get(RequestHandler).content
#print Request
#Use regex to find request and email from webapp
inputText = re.findall('<request>(.+?)</request>',Request)
toAddress = re.findall('<email>(.+?)</email>',Request)
#If there is no input text, there are no requests waiting to be filled
if inputText == []:
	print 'No currently unfulfilled requests'
	sys.exit()
inputText = inputText[0]
#########################################
#search and get poem url from page via beautiful soup parsing
#########################################
from urllib import quote
from bs4 import BeautifulSoup
import random
#convert request to percent encoding
search = quote(inputText, safe= '')
end = 0
n = 1 
results =[]
try:
	#go through all pages of the search result for the input
	while end < 1:
		siteUrl = 'https://www.poetryfoundation.org/search?' + 'q=' + search + '&' + 'page=' + str(n)
		searchhtml=requests.get(siteUrl).content
		#when the end is reached, the following text appears on the website
		endIfFound = re.findall('Try changing the filter or searching for a new term.', searchhtml)
		end = len(endIfFound)
		searchhtml= BeautifulSoup(searchhtml, "html.parser")
		results += searchhtml.find_all("div","feature") 
		#go to next page, end after going through all results
		n += 1

	#if the first result is an author, randomly select from the following poems
	#if not, return the first result
	firstresult = re.findall('<span class="hdg hdg_utility hdg_utility_sm">(.+?)</span>',str(results[0]))[0]
	if firstresult == 'poem':
		poemUrl = 'http:' + results[0].find_all('a')[0].get('href')
		author = re.findall('<span class="hdg hdg_utility">By (.+?)</span>',str(results[0]))[0]
		print poemUrl
	if firstresult == 'author':
		poemURLs = []
		author = results[0].find_all('a')[0]
		author = re.findall('>(.*?)</a>',str(author))[0]
	#print author
	#if the input is an author, return a random poem by that author
		for entry in results:
			classification = re.findall('<span class="hdg hdg_utility hdg_utility_sm">(.*?)</span>',str(entry))[0]
			#make a list of all poem entries written by that author
			if classification =='poem':
				byline = re.findall('<span class="hdg hdg_utility">(.*?)</span>',str(entry))[0]

				if byline == 'By ' + author:
					poemURLs.append(str(entry.find_all('a')[0].get('href')))

		poemUrl = 'http:' + random.choice(poemURLs)

	#########################################
	#get html source code for page
	#########################################
	#there is a 5 digit poem id for every poem, which appears in the URL
	poemid = re.findall('[0-9]{5}',poemUrl)
	#print poemid[0]
	#get html for the poem
	html=requests.get(poemUrl).content
	#########################################
	#get text and formatting
	#########################################
	import unicodedata
	soup = BeautifulSoup(html, "html.parser")
	title = soup.find_all("span", "hdg hdg_1")
	title = re.findall('>(.+?)</span>',str(title[0]))[0]

	byline = soup.find_all("span","hdg hdg_utility")
	byline = 'By ' + re.findall('>(.+?)</a>',str(byline[0]))[0]
	#epigraph appears sometimes; if it isn't there, this is designed so latex won't print anything
	epigraph = ['%empty']
	epigraph.append(re.findall('<div style="font-style:italic;">(.+?)</div>', html))
	if len(epigraph[1]) > 0:
		epigraph = epigraph[1][0]
		epigraph = str(BeautifulSoup(epigraph, "html.parser"))
		epigraph = epigraph.replace('<br/>','\\\\ ')
		epigraph += '\par'
	else:
		epigraph = epigraph[0]
	epigraph = re.sub("<.+?>","",epigraph)
	epigraph = '\\begin{quote} {\itshape ' + epigraph + '\r } \\end{quote}'
	#all lines of text are accompanied by these tags
	text = re.findall('<div style="text-indent: -1em; padding-left: 1em;">(.+?)</div>', html)

	poem = ''
	i = 1
	#j = 1
	for line in text:
		# if i > 30*j and line == '<br>':
		# 	line = line.replace('<br>','\\columnbreak \\newline  ')
		# 	j += 1
		# else:
		line = line.replace('<br>','\r \\\\ ')
		#\xc2 instead of space or tab?  Very frustrating to deal with; useful for catching indents, though
		if line[0] == '\xc2':
		 	line = '\\indent' + line
		line = unicodedata.normalize('NFKD', line.decode('utf-8'))
		line = line.encode('utf-8')
		poem += line
		i += 1
	#eliminate any remaining tags
	poem = re.sub("<.+>","",poem)
	title = re.sub("<.+?>","",title)
	#########################################
	#print to pdf with LaTeX
	#########################################
	import os

	c = ''
	c =r'''\documentclass[12pt]{article}
	\usepackage[margin = .75in]{geometry}
	\usepackage{multicol}
	\setlength\columnsep{5pt}
	\pagenumbering{gobble}
	\title{''' + title + r'''}
	\author{''' + byline + r'''}
	\date{}
	\begin{document}

	\maketitle

	%\begin{multicols}{2}
	''' +  epigraph + r'''
	\noindent ''' + poem + r'''
	%\end{multicols}
	\bigskip
	Retrieved from the Poetry Foundation website

	\end{document}'''

	#print c
	file(poemid[0] +'.tex', 'w').write(c)
	pdfname = poemid[0]+'.pdf'
	os.system('pdflatex ' + poemid[0] + '.tex')

	os.unlink( poemid[0] + '.tex')
	os.unlink( poemid[0] + '.log')
	os.unlink(poemid[0] + '.aux')
	os.system('gdrive upload ' + poemid[0] + '.pdf')
	print 'finished with latex'

	#########################################
	#send an email with the pdf
	#########################################
	if toAddress == []:
		print 'no email address found'
		sys.exit()
	import time
	#give time for the file to sync to drive
	time.sleep(7)
	#web app to retrieve a file from drive and send it
	Emailer = 'https://script.google.com/macros/s/AKfycbyA2pZQla_EatWqL8COtecXQJEEu2QD8oiZs1v1ecEdt_ihN9g/exec?'
	parameters = {'fileName':pdfname, 'title':title, 'toAddress':toAddress}
	confirmation = requests.get(Emailer,params=parameters).content
	os.unlink(poemid[0] + '.pdf')
	print confirmation
#error handling:
except:
	print 'Sorry, we could not fulfill your request.  Try something different?'
	os.system('taskkill /f /im pdflatex.exe')
#########################################
#cleaning up
#########################################
#os.system('taskkill /f /im pdflatex.exe')

#useful websites:
#http://stackoverflow.com/questions/8085520/generating-pdf-latex-with-python-script
#https://docs.python.org/2/library/unicodedata.html