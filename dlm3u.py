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
import base64
import codecs

DEFAULT_REFERER='https://www.google.com'
SUFFIX='_out.ts'
ssl._create_default_https_context = ssl._create_unverified_context

def decbase64(string):
	obj = re.match('^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{4}|[A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}==)$',string)
	if obj != None:
		dec = base64.b64decode(string)
		return dec
	
	obj = re.match('^([A-Za-z0-9_\-]{4})*([A-Za-z0-9+/]{4}|[A-Za-z0-9\-_]{3}=|[A-Za-z0-9_\-]{2}==)$',string)
	if obj != None:
		dec = base64.urlsafe_b64decode(string)
		return dec
	
	return None

def decode_file_base64(filepath):
	f = codecs.open(filepath, "r")
	s = f.read()
	f.close()
	
	b = decbase64(s)
	if b == None:
		return
	
	f = open(filepath, "wb")
	f.write(b)
	f.close()
	
	return


def createheaders(args):
	headers = {
			 # "Origin":"https://www.google.com",
			 # "Accept-Encoding":"gzip, deflate, br",
			"Accept-Language":"ja,en-US;q=0.9,en;q=0.8",
			"Accept":"*/*",
			"Connection":"keep-alive",
			"User-Agent":"Mozilla/5.0 Gecko/20100101 Firefox/70.0.0",
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
		#if e.code >= 400:
		print (e.reason)
		for key in headers.keys():
			val = headers[key]
			print(key + '=' + val)
		return e.code
	except urllib.error.URLError as e:
		print('We failed to reach a server.')
		print('Reason: ', e.reason)
		return -1
		#else:
			#raise e
	
	return 0

#def downloadfile(urls,headers,outputdir,stcount=0,suffix=SUFFIX):
#	results = []
#	total = len(urls)
#	ct = 0
#	for url in urls:
#		filename = "{:0=10}".format(stcount)
#		filename = filename + suffix
#		outputpath = os.path.join(outputdir,filename)
#		ct += 1
#		ratestr = "[" + str(int((ct / total)*100)) + "%]"
#		print(ratestr + outputpath+" "+url)
#		
#		res = 0
#		for i in range(5):
#			print("TRY-" + str(i+1))
#			res = http_download(url,headers,outputpath)
#			if res != 0:
#				print("ERROR!\n")
#				continue
#			break
#		
#		results.append(res)
#		stcount+=1
#	return results

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

def printresult(urls,results,stcount=0,suffix=SUFFIX, ignoreerr=False):
	errct = 0
	print("failure download urls----------")
	for ct in range(0,len(urls)):
		if results[ct] != 0:
			filename = "{:0=10}".format(stcount) + suffix
			print("[" + str(stcount)+ "]\t" + filename + "\t" + urls[ct])
			errct += 1
		stcount += 1
	print("end----------------------------")
	if errct != 0 and ignoreerr == False:
		print("can't download some of the files.please retry failed file to download.")
		exit(-1)
	return 0

def createpath(dir,file):
	m = re.sub('/[^/]*$','/',dir)
	url = m + file
	return url

def loadm3u8(path,args,urls=[]):
	f = codecs.open(path,'r')
	line = f.readline()
	while line:
		line = line.rstrip()
		if re.match('#',line) == None:
			urls.append(line)
		line = f.readline()
	f.close()
	return urls

BYTERANGE=0x1
def parse_ext(ext,headers):
	r = ext.split(':')
	if len(r) < 2:
		return 0
	res = 0
	if r[0] == '#EXT-X-BYTERANGE':
		s = r[1].split('@')
		s0 = s1 = 0
		
		res = res | BYTERANGE
		#Range: bytes=21336496-21879439
		if len(s) < 2:
			if "X-BYTERANGE" in headers:
				s.append(headers["X-BYTERANGE"])
			else:
				s.append('0')
		
		try:
			s0 = int(s[0])
		except:
			s0 = 0
		
		try:
			s1 = int(s[1])
		except:
			s1 = 0
			
		val = "bytes="+str(s1)+"-"+str(s0+s1)
		headers["Range"] = val
		headers["X-BYTERANGE"] = str(s0 + s1)
		#print(val)
	return res

def downloadfile2(args,urls,headers,outputdir,stcount=0,suffix=SUFFIX):
	results = []
	total = len(urls)
	ct = 0
	url = ""
	dlheaders=headers.copy()
	f = codecs.open(args.m3u8file,'r')
	line = f.readline()
	
	while line:
		line = line.rstrip()
		
		if re.match('#',line):
			res = parse_ext(line,dlheaders)
			if res & BYTERANGE:
				headers["X-BYTERANGE"] = dlheaders["X-BYTERANGE"]
			line = f.readline()
			continue
		elif re.match('http',line):
			url = line
		else:
			url = createpath(args.m3u8url,line)
		
		if ct < args.start:
			ct+=1
			line = f.readline()
			continue
		
		
		filename = "{:0=10}".format(stcount)
		filename = filename + suffix
		outputpath = os.path.join(outputdir,filename)
		
		ratestr = "[" + str(int((ct / total)*100)) + "%]"
		print(ratestr + outputpath+" "+url)
		
		res = 0 
		for i in range(5):
			print("TRY-"+str(i+1)+' ',end='')
			res = http_download(url,dlheaders,outputpath)
			if res != 0:
				#print("ERROR!\n")
				continue
			print("200 OK\n")
			break
		
		results.append(res)
		stcount+=1
		ct += 1
		dlheaders = headers.copy()
		
		if (args.end != -1) and (args.end >= ct):
			break
		
		line = f.readline()
	f.close()
	return results
	

def stendurls(urls,args):
	if args.start == 0 and args.end == -1:
		return urls
	
	if args.end == -1:
		return urls[args.start:]
		
	return urls[args.start:args.end]

def genm3u8file(args,filepath):
	f = open(filepath, "w")
	for x in range(args.first, args.last):
		line = args.m3u8file.replace('seg-1','seg-'+str(x))
	#	line = args.m3u8file.replace('segment-1','segment-'+str(x))
		f.write(line + '\n')
	f.close()
	return 0

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

	if args.pattern == False:
		res = http_download(args.m3u8file, headers, filepath)
	else:
		res = genm3u8file(args,filepath)
	
	if res != 0:
		print("can't download m3u8 file")
		exit(-1)
	print('ok')
	decode_file_base64(filepath)
	args.m3u8url = args.m3u8file
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
	parser.add_argument("-p","--pattern",   help="m3u8 file url is direct link",action="store_true")
	parser.add_argument("-f","--first",      help="specify first number",       type=int,default=1 )
	parser.add_argument("-l","--last",       help="specify last number",       type=int,default=721)
	parser.add_argument("-i","--timetosplit",help="specify reference time to split(seconds)",type=int,default=10)
	parser.add_argument("-t","--time",       help="specify time"                                   )
	parser.add_argument("-m","--m3u8url",	 help="m3u8 file for save"                             )
	parser.add_argument("m3u8file",         help="m3u8 file must be specified."                   )
	args = parser.parse_args()

	if args.time != None:
		m = re.match(r'(\d\d):(\d\d):(\d\d)',args.time)
		if m != None:
			last =int((int(m.group(1))*60*60+int(m.group(2))*60+int(m.group(3)))/args.timetosplit)+1
			args.last = last + 1
			args.first = 1

	return args

if __name__=='__main__':
	args = getarg()
	if args.unverified == True:
		ssl._create_default_https_context = ssl._create_unverified_context
	headers = createheaders(args)
	getm3u8file(args,headers)
	outdir = createoutputdir(args)
	urls = loadm3u8(args.m3u8file,args)
	urls = stendurls(urls,args)
	#res = downloadfile(urls,headers,outdir,args.start)
	res = downloadfile2(args,urls,headers,outdir,args.start)
	printresult(urls,res,ignoreerr=args.pattern)
	filepath = catproc(args,outdir)
	ffmpegproc(filepath,outdir,args)


