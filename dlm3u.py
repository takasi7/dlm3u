#! /usr/local/bin/python3
import os
import sys
import re
import argparse
import urllib.request
import urllib.error
import subprocess
import datetime
import ssl

DEFAULT_REFERER='https://www.google.com'
SUFFIX='_out.ts'

def createheaders(args):
	headers = {
			 # "Origin":"https://www.google.com",
			 # "Accept-Encoding":"gzip, deflate, br",
			"Accept-Language":"ja,en-US;q=0.9,en;q=0.8",
			"Accept":"*/*",
			"Connection":"keep-alive"
		}
	
	if args.headers != None:
		for header in args.headers:
			r = header.split(":")
			if len(r) == 2:
				headers[r[0].strip()] = r[1].strip()
	
	if args.noreferer == False:
		if args.referer != None:
			headers['Referer'] = args.referer
		elif ('Referer' not in headers) and ('referer' not in headers):
			headers['Referer'] = DEFAULT_REFERER
	elif args.noreferer == True:
		if 'Referer' in headers:
			del headers['Referer']	
	
	return headers


def http_download(url,headers,outputpath):
	req = urllib.request.Request(url, headers=headers)
	try:
		with urllib.request.urlopen(req) as res:
			body = res.read()
			f = open(outputpath,"wb")
			f.write(body)
			f.close()
	except urllib.error.HTTPError as e:
		if e.code >= 400:
			print (e.reason)
			return -1
		else:
			raise e
	
	return 0

def downloadfile(urls,headers,outputdir,stcount=0,suffix=SUFFIX):
	results = []
	for url in urls:
		filename = "{:0=10}".format(stcount)
		filename = filename + suffix
		outputpath = os.path.join(outputdir,filename)
		print(outputpath+" "+url)
		res = http_download(url,headers,outputpath)
		results.append(res)
		if res < 0:
			print("ERROR!\n")
		
		stcount+=1
	return results

def createoutputdir(args):
	directory = ''
	if args.directory != None:
		if not os.path.isdir(args.directory):
			os.makedirs(args.directory)
		directory = args.directory
	else:
		basename = os.path.basename(args.m3u8file)
		root,ext = os.path.splitext(basename)
		if not os.path.isdir(root):
			os.makedirs(root)
		directory = root
	return directory

def catproc(args,outdir,suffix=SUFFIX):
	filename = ''
	if args.output == None:
		basename = os.path.basename(args.m3u8file)
		root,ext = os.path.splitext(basename)
		filename = root
		root,ext = os.path.splitext(suffix)
		filename = filename + ext
	else:
		filename = args.output
	filepath = os.path.join(outdir,filename)
	outfiles = os.path.join(outdir,"*"+suffix)
	cmd = "cat "+outfiles+" >"+filepath
	subprocess.call(cmd,shell=True)
	
	cmd = "rm " + outfiles
	subprocess.call(cmd, shell=True)

	return filepath

def printresult(urls,results,stcount=0,suffix=SUFFIX):
	errct = 0
	print("failure download urls----------")
	for ct in range(0,len(urls)):
		if results[ct] < 0:
			filename = "{:0=10}".format(stcount) + suffix
			print("[" + str(stcount)+ "]\t" + filename + "\t" + urls[ct])
			errct += 1
		stcount += 1
	print("end----------------------------")
	if errct != 0:
		print("can't download some of the files.please retry failed file to download.")
		exit(-1)
	return 0

def loadm3u8(path,urls=[]):
	f = open(path,'r')
	line = f.readline()
	while line:
		line = line.rstrip()
		if re.match('http',line):
			urls.append(line)
		line = f.readline()
	f.close()
	return urls


def stendurls(urls,args):
	if args.start == 0 and args.end == -1:
		return urls
	
	if args.end == -1:
		return urls[args.start:]
		
	return urls[args.start:args.end]


def getm3u8file(args,headers):
	if re.match('https?://',args.m3u8file) == None:
		return 0
	dt = datetime.datetime.now()
	s = str(dt)
	s = re.sub('\.(\d\d)\d*$',r'\1',s)
	s = re.sub('[ \-:]', '', s)
	filepath = 'hls' + s + '.m3u8'
	print('downloading m3u8 file...')
	print('from ' + args.m3u8file)
	print('to ' + filepath)
	res = http_download(args.m3u8file, headers, filepath)
	if res < 0:
		print("can't download m3u8 file")
		exit(-1)
	print('ok')
	args.m3u8file = filepath
	return 0
	
def getfilename(ref):
	if ref == None:
		return ''
	
	m = re.search('/([^/]+)$',ref)
	if m == None:
		return ''
	s = m.group(1)
	s = re.sub('%[0-9a-fA-F][0-9a-fA-F]','',s)
	m = re.search('([a-zA-Z][a-zA-Z0-9]+-[a-zA-Z0-9]+)',s)
	if m == None:
		return ''
	
	return m.group(1)

def ffmpegproc(filepath,outdir,args):
	cmd = "ffmpeg -i __INPUT__ -vcodec copy -acodec copy -f mp4 __OUTPUT__.mp4"
	
	fn = args.output
	if fn == None:
		fn = getfilename(args.referer)
		if len(fn) == 0:
			fn,ext = os.path.splitext(filepath)
		else:
			fn = os.path.join(outdir,fn)
	else:
		fn,ext = os.path.splitext(args.output)
		if ext == ".mp4":
			fn = args.output
		fn = os.path.join(outdir,fn)
	
	cmd = cmd.replace('__INPUT__', filepath)
	cmd = cmd.replace('__OUTPUT__', fn)
	subprocess.call(cmd,shell=True)
	return 0

def getarg():
	parser = argparse.ArgumentParser()
	parser.add_argument("-H","--headers",   help="set http headers",          action="append"     )
	parser.add_argument("-u","--unverified",help="no verify certificate",     action="store_true" )
	parser.add_argument("-n","--noreferer", help="no referer header",         action="store_true" )
	parser.add_argument("-r","--referer",   help="set referer header"                             )
	parser.add_argument("-d","--directory", help="specify output directory"                       )
	parser.add_argument("-o","--output",    help="specify output filename"                        )
	parser.add_argument("-s","--start",     help="specify start url line",     type=int,default=0 )
	parser.add_argument("-e","--end",       help="specify end url line",       type=int,default=-1)
	parser.add_argument("m3u8file",         help="m3u8 file must be specified."                   )
	args = parser.parse_args()
	return args

if __name__=='__main__':
	args = getarg()
	if args.unverified == True:
		ssl._create_default_https_context = ssl._create_unverified_context
	headers = createheaders(args)
	getm3u8file(args,headers)
	outdir = createoutputdir(args)
	urls = loadm3u8(args.m3u8file)
	urls = stendurls(urls,args)
	res = downloadfile(urls,headers,outdir,args.start)
	printresult(urls,res)
	filepath = catproc(args,outdir)
	ffmpegproc(filepath,outdir,args)


