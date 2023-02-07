
#	      ___    __                          __         
#	     /   |  / /___ __________  _________/ /__  _____
#	    / /| | / / __ `/ ___/ __ \/ ___/ __  / _ \/ ___/
#	   / ___ |/ / /_/ / /__/ /_/ / /  / /_/ /  __/ /    
#	  /_/  |_/_/\__,_/\___/\____/_/   \__,_/\___/_/     
#
#		ALACORDER beta 6.6.4 (pure-python)
#		Does not require cython or c compiler
#
#		by Sam Robson
#

import os
import sys
import glob
import re
import math
import numpy as np
import pandas as pd
import xlrd
import openpyxl
import datetime
import time
import warnings
import PyPDF2 as pypdf
from io import StringIO

# CONFIG

def config(in_path: str, out_path: str, flags="", print_log=True, warn=False): 

	# Get extensions
	out_ext: str = out_path.split(".")[-1].strip()
	in_ext: str = in_path.split(".")[-1].strip() if len(in_path.split(".")[-1])<5 else "directory" 

	# Check if input path is valid
	if in_ext != "directory" and in_ext != "pkl" and in_ext != "csv" and in_ext != "xls" and in_ext != "json":
		raise Exception("Input path must be to/pdf/directory/, (archive).csv, (archive).xls, (archive).json, or (archive).pkl!")
	if os.path.exists(in_path) == False:
		raise Exception("Input path does not exist!")

	# Check if output path is valid
	if out_ext != "pkl" and out_ext != "txt" and out_ext != "csv" and out_ext != "xls" and out_ext != "json" and out_ext != "dta":
		raise Exception("Output path must be .csv, .xls, .json, or .pkl! (.pkl only for full text archives)")

	# Set read, write modes, contents
	if in_ext == "directory" and out_ext == "pkl": # from dir to pkl = make archive
		make = "archive"
		origin = "directory"
		contents = glob.glob(in_path + '**/*.pdf', recursive=True)
	elif in_ext == "directory" and bool(out_ext == "xls" or out_ext == "json" or out_ext == "csv" or out_ext == "txt" or out_ext == "dta"):
		make = "table"
		origin = "directory"
		contents = glob.glob(in_path + '**/*.pdf', recursive=True)
	elif in_ext == "pkl":
		make = "table"
		origin = "archive"
		contents = pd.read_pickle(in_path)['Path']
	elif in_ext == "csv":
		make = "table"
		origin = "archive"
		contents = pd.read_csv(in_path).tolist()
	elif in_ext == "xls":
		make = "table"
		origin = "archive"
		contents = pd.read_excel(in_path,sheet_name="text_from_pdf")
	elif in_ext == "json": 
		make = "table"
		origin = "archive"
		contents = pd.read_pickle(in_path)
	else:
		raise Exception("Not supported. Refer to alacorder documentation at https://github.com/sbrobson959/alacorder for supported input and outputs.")

	# verify directory input has content
	if len(contents)==0:
		raise Exception("No cases found in input path! (" + in_path + ")")

	if origin == "archive":
		batchsize = 250
	if origin == "directory":
		batchsize = 100

	case_max = len(contents)
	tot_batches = math.ceil(case_max / batchsize)

	batches = np.array_split(contents, tot_batches)

	if print_log == True:
		print(f"Initial configuration succeeded!\n\n{in_path} ----> {out_path}\n\n{case_max} cases in {tot_batches} batches")

	conf = pd.Series({
		'in_path': in_path,
		'out_path': out_path,
		'in_ext': in_ext,
		'out_ext': out_ext,
		'origin': origin,
		'make': make,
		'contents': contents,
		'batches': batches,
		'case_max': case_max,
		'tot_batches': tot_batches,
		'batchsize': batchsize,
		'print_log': print_log,
		'warnings': warn
	})
	
	return conf

# BATCH METHODS

def writeArchiveThenTables(conf):
	path_in = conf['in_path']
	start_time = time.time()
	path_out = conf['in_path'] + "alac_temp_" + str(start_time) + ".pkl"
	case_max = conf['case_max']
	tot_batches = conf['tot_batches']
	batchsize = conf['batchsize']
	batches = conf['batches']
	contents = conf['contents']
	in_ext = conf['in_ext']
	out_ext = conf['out_ext']
	print_log = conf['print_log']
	warn = conf['warnings']

	if warn == False:
		warnings.filterwarnings("ignore")

	
	outputs = pd.DataFrame()
	on_batch = 0

	for b in batches:

		paths = pd.Series(b)
		allpagestext = pd.Series(b).map(lambda x: getPDFText(x))
		timestamp = time.time()

		c = pd.DataFrame({
			'Path': paths,
			'AllPagesText': allpagestext,
			'Timestamp': timestamp
			})
		outputs = pd.concat([outputs, c],ignore_index=True)
		on_batch += 1
		outputs.fillna('',inplace=True)

		if out_ext == "pkl":
			outputs.to_pickle(path_out)

		console_logTA(conf, on_batch, "")
		outputs.to_pickle(path_out)

	log_complete(conf, start_time)
	on_batch = 0
	tab_conf = config(path_out, conf['out_path'])
	writeTables(tab_conf)

def writeArchive(conf):
	path_in = conf['in_path']
	path_out = conf['out_path']
	case_max = conf['case_max']
	tot_batches = conf['tot_batches']
	batchsize = conf['batchsize']
	batches = conf['batches']
	contents = conf['contents']
	in_ext = conf['in_ext']
	out_ext = conf['out_ext']
	print_log = conf['print_log']
	warn = conf['warnings']

	if warn == False:
		warnings.filterwarnings("ignore")

	start_time = time.time()
	outputs = pd.DataFrame()
	on_batch = 0

	for b in batches:

		paths = pd.Series(b)
		allpagestext = pd.Series(b).map(lambda x: getPDFText(x))
		timestamp = time.time()

		c = pd.DataFrame({
			'Path': paths,
			'AllPagesText': allpagestext,
			'Timestamp': timestamp
			})
		outputs = pd.concat([outputs, c],ignore_index=True)
		on_batch += 1
		outputs.fillna('',inplace=True)

		if out_ext == "pkl":
			outputs.to_pickle(path_out)
		elif out_ext == "json":
			outputs.to_json(path_out)
		elif out_ext == "csv":
			outputs.to_csv(path_out,escapechar='\\')
		elif out_ext == "md":
			outputs.to_markdown(path_out)
		elif out_ext == "txt":
			outputs.to_string(path_out)
		elif out_ext == "dta":
			outputs.to_stata(path_out)
		console_log(conf, on_batch, "")
	log_complete(conf, start_time)
	on_batch = 0

def writeTables(conf):
	batches = conf['batches']
	path_in = conf['in_path']
	path_out = conf['out_path']
	case_max = conf['case_max']
	tot_batches = conf['tot_batches']
	batchsize = conf['batchsize']
	in_ext = conf['in_ext']
	out_ext = conf['out_ext']
	print_log = conf['print_log']
	warn = conf['warnings']
	contents = conf['contents']
	batches = conf['batches']
	if warn == False:
		warnings.filterwarnings("ignore")
	start_time = time.time()
	on_batch = 0
	outputs = pd.DataFrame()

	fees = pd.DataFrame({'CaseNumber': '', 'Code': '', 'Payor': '', 'AmtDue': '', 'AmtPaid': '', 'Balance': '', 'AmtHold': ''},index=[0])
	charges = pd.DataFrame({'CaseNumber': '', 'Num': '', 'Code': '', 'Felony': '', 'Conviction': '', 'CERV': '', 'Pardon': '', 'Permanent': '', 'Disposition': '', 'CourtActionDate': '', 'CourtAction': '', 'Cite': '', 'TypeDescription': '', 'Category': '', 'Description': ''},index=[0]) # charges = pd.DataFrame() # why is this here
	for i, c in enumerate(batches):
		b = pd.DataFrame()
		b['AllPagesText'] = pd.Series(c).map(lambda x: getPDFText(x))
		b['CaseInfoOutputs'] = b['AllPagesText'].map(lambda x: getCaseInfo(x))
		b['CaseNumber'] = b['CaseInfoOutputs'].map(lambda x: x[0])
		b['Name'] = b['CaseInfoOutputs'].map(lambda x: x[1])
		b['Alias'] = b['CaseInfoOutputs'].map(lambda x: x[2])
		b['DOB'] = b['CaseInfoOutputs'].map(lambda x: x[3])
		b['Race'] = b['CaseInfoOutputs'].map(lambda x: x[4])
		b['Sex'] = b['CaseInfoOutputs'].map(lambda x: x[5])
		b['Address'] = b['CaseInfoOutputs'].map(lambda x: x[6])
		b['Phone'] = b['CaseInfoOutputs'].map(lambda x: x[7])
		b['ChargesOutputs'] = b.index.map(lambda x: getCharges(b.loc[x].AllPagesText, b.loc[x].CaseNumber))
		b['Convictions'] = b['ChargesOutputs'].map(lambda x: x[0])
		b['DispositionCharges'] = b['ChargesOutputs'].map(lambda x: x[1])
		b['FilingCharges'] = b['ChargesOutputs'].map(lambda x: x[2])
		b['CERVConvictions'] = b['ChargesOutputs'].map(lambda x: x[3])
		b['PardonConvictions'] = b['ChargesOutputs'].map(lambda x: x[4])
		b['PermanentConvictions'] = b['ChargesOutputs'].map(lambda x: x[5])
		b['ConvictionCount'] = b['ChargesOutputs'].map(lambda x: x[6])
		b['ChargeCount'] = b['ChargesOutputs'].map(lambda x: x[7])
		b['CERVChargeCount'] = b['ChargesOutputs'].map(lambda x: x[8])
		b['PardonChargeCount'] = b['ChargesOutputs'].map(lambda x: x[9])
		b['PermanentChargeCount'] = b['ChargesOutputs'].map(lambda x: x[10])
		b['CERVConvictionCount'] = b['ChargesOutputs'].map(lambda x: x[11])
		b['PardonConvictionCount'] = b['ChargesOutputs'].map(lambda x: x[12])
		b['PermanentConvictionCount'] = b['ChargesOutputs'].map(lambda x: x[13])
		b['ChargeCodes'] = b['ChargesOutputs'].map(lambda x: x[14])
		b['ConvictionCodes'] = b['ChargesOutputs'].map(lambda x: x[15])
		b['FeeOutputs'] = b.index.map(lambda x: getFeeSheet(b.loc[x].AllPagesText, b.loc[x].CaseNumber))
		b['TotalAmtDue'] = b['FeeOutputs'].map(lambda x: x[0])
		b['TotalBalance'] = b['FeeOutputs'].map(lambda x: x[1])
		b['TotalD999'] = b['FeeOutputs'].map(lambda x: x[2])
		b['FeeCodesOwed'] = b['FeeOutputs'].map(lambda x: x[3])
		b['FeeCodes'] = b['FeeOutputs'].map(lambda x: x[4])
		b['FeeSheet'] = b['FeeOutputs'].map(lambda x: x[5])


		feesheets = b['FeeOutputs'].map(lambda x: x[6]) # -> pd.Series(df, df, df)
		feesheets = feesheets.dropna() # drop empty 
		feesheets = feesheets.tolist() # convert to list -> [df, df, df]
		feesheets = pd.concat(feesheets,axis=0,ignore_index=True) # add all dfs in batch -> df
		fees = pd.concat([fees, feesheets],axis=0,ignore_index=True)
		fees['AmtDue'] = fees['AmtDue'].map(lambda x: pd.to_numeric(x,'ignore'))
		fees['AmtPaid'] = fees['AmtPaid'].map(lambda x: pd.to_numeric(x,'ignore'))
		fees['Balance'] = fees['Balance'].map(lambda x: pd.to_numeric(x,'ignore'))
		fees['AmtHold'] = fees['AmtHold'].map(lambda x: pd.to_numeric(x,'ignore'))


		chargetabs = b['ChargesOutputs'].map(lambda x: x[17])
		chargetabs = chargetabs.dropna()
		chargetabs = chargetabs.tolist()
		chargetabs = pd.concat(chargetabs,axis=0,ignore_index=True)
		charges = pd.concat([charges, chargetabs],axis=0,ignore_index=True)
		console_log(conf, on_batch, chargetabs.to_string())

		b['ChargesTable'] = b['ChargesOutputs'].map(lambda x: x[-1])
		b['TotalD999'] = b['TotalD999'].map(lambda x: pd.to_numeric(x,'ignore'))
		b['Phone'] =  b['Phone'].map(lambda x: pd.to_numeric(x,'ignore'))
		b['TotalAmtDue'] = b['TotalAmtDue'].map(lambda x: pd.to_numeric(x,'ignore'))
		b['TotalBalance'] = b['TotalBalance'].map(lambda x: pd.to_numeric(x,'ignore'))
		b.drop(columns=['AllPagesText','CaseInfoOutputs','ChargesOutputs','FeeOutputs','TotalD999','ChargesTable','FeeSheet'],inplace=True)
		outputs = pd.concat([outputs, b],ignore_index=True)
		
		outputs.fillna('',inplace=True)
		charges.fillna('',inplace=True)
		fees.fillna('',inplace=True)

		# write 
		if out_ext == "xls":
			with pd.ExcelWriter(path_out) as writer:
				outputs.to_excel(writer, sheet_name="cases-table")
				fees.to_excel(writer, sheet_name="fees-table")
				charges.to_excel(writer, sheet_name="charges-table")
		elif out_ext == "pkl":
			outputs.to_pickle(path_out)
		elif out_ext == "json":
			outputs.to_json(path_out)
		elif out_ext == "csv":
			outputs.to_csv(path_out,escapechar='\\')
		elif out_ext == "md":
			outputs.to_markdown(path_out)
		elif out_ext == "txt":
			outputs.to_string(path_out)
		elif out_ext == "dta":
			outputs.to_stata(path_out)
		else:
			raise Exception("Output file extension not supported! Please output to .xls, .pkl, .json, or .csv")
		on_batch += 1
		console_log(conf, on_batch,'')
	log_complete(conf, start_time)
	on_batch = 0

# CASE METHODS 

def getPDFText(path: str) -> str:
	text = ""
	pdf = pypdf.PdfReader(path)
	for pg in pdf.pages:
		text += pg.extract_text()
	return text

def getCaseInfo(text: str):
	case_num = ""
	name = ""
	alias = ""
	race = ""
	sex = ""
	address = ""
	dob = ""
	phone = ""

	try:
		county: str = re.search(r'(?:County\: )(\d{2})(?:Case)', str(text)).group(1).strip()
		case_num: str = county + "-" + re.search(r'(\w{2}\-\d{4}-\d{6}.\d{2})', str(text)).group(1).strip() 
	except (IndexError, AttributeError):
		pass
 
	if bool(re.search(r'(?a)(VS\.|V\.{1})(.+)(Case)*', text, re.MULTILINE)) == True:
		name = re.search(r'(?a)(VS\.|V\.{1})(.+)(Case)*', text, re.MULTILINE).group(2).replace("Case Number:","").strip()
	else:
		if bool(re.search(r'(?:DOB)(.+)(?:Name)', text, re.MULTILINE)) == True:
			name = re.search(r'(?:DOB)(.+)(?:Name)', text, re.MULTILINE).group(1).replace(":","").replace("Case Number:","").strip()
	if bool(re.search(r'(SSN).{5,75}?(Alias)',text, re.MULTILINE)) == True:
		alias = re.search(r'(SSN)(.{5,75})(Alias)?', text, re.MULTILINE).group(2).replace(":","").replace("Alias 1","").strip()
	else:
		pass
	try:
		dob: str = re.search(r'(\d{2}/\d{2}/\d{4})(?:.{0,5}DOB\:)', str(text), re.DOTALL).group(1)
		phone: str = re.search(r'(?:Phone\:)(.*?)(?:Country)', str(text), re.DOTALL).group(1).strip()
		if len(phone) < 7:
			phone = ""
		if len(phone) > 10 and phone[-3:] == "000":
			phone = phone[0:9]
	except (IndexError, AttributeError):
		dob = ""
		phone = ""
	try:
		racesex = re.search(r'(B|W|H|A)\/(F|M)(?:Alias|XXX)', str(text))
		race = racesex.group(1).strip()
		sex = racesex.group(2).strip()
	except (IndexError, AttributeError):
		pass
	try:
		street_addr = re.search(r'(Address 1\:)(.+)', str(text), re.MULTILINE).group(2).strip()
	except (IndexError, AttributeError):
		street_addr = ""
	try:
		zip_code = re.search(r'(Zip\: )(.+)', str(text), re.MULTILINE).group(2).strip()	
	except (IndexError, AttributeError):
		zip_code = ""
	try:
		city = re.search(r'(City\: )(.*)(State\: )(.*)', str(text), re.MULTILINE).group(2).strip()
	except (IndexError, AttributeError):
		city = ""
	try:
		state = re.search(r'(?:City\: ).*(?:State\: ).*', str(text), re.MULTILINE).group(4).strip()
	except (IndexError, AttributeError):
		state = ""
	
	address = street_addr + " " + city + ", " + state + " " + zip_code
	case = [case_num, name, alias, dob, race, sex, address, phone]
	return case

def getFeeSheet(text: str, cnum: str):
	actives = re.findall(r'(ACTIVE.*\$.*)', str(text))
	if len(actives) == 0:
		return [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
	else:
		rind = range(0, len(actives)+1)
		try:
			trowraw = re.findall(r'(Total.*\$.*)', str(text), re.MULTILINE)[0]
			totalrow = re.sub(r'[^0-9|\.|\s|\$]', "", trowraw)
			if len(totalrow.split("$")[-1])>5:
				totalrow = totalrow.split(" . ")[0]
			tbal = totalrow.split("$")[3].strip().replace("$","").replace(",","").replace(" ","")
			tdue = totalrow.split("$")[1].strip().replace("$","").replace(",","").replace(" ","")
			tpaid = totalrow.split("$")[2].strip().replace("$","").replace(",","").replace(" ","")
			thold = totalrow.split("$")[4].strip().replace("$","").replace(",","").replace(" ","")
		except IndexError:
			totalrow = ""
			tbal = ""
			tdue = ""
			tpaid = ""
			thold = ""
		fees = pd.Series(actives,dtype=str)
		fees_noalpha = fees.map(lambda x: re.sub(r'[^0-9|\.|\s|\$]', "", x))
		srows = fees.map(lambda x: x.strip().split(" "))
		drows = fees_noalpha.map(lambda x: x.replace(",","").split("$"))
		coderows = srows.map(lambda x: str(x[5]).strip() if len(x)>5 else "")
		payorrows = srows.map(lambda x: str(x[6]).strip() if len(x)>6 else "")
		amtduerows = drows.map(lambda x: str(x[1]).strip() if len(x)>1 else "")
		amtpaidrows = drows.map(lambda x: str(x[2]).strip() if len(x)>2 else "")
		balancerows = drows.map(lambda x: str(x[-1]).strip() if len(x)>5 else "")
		amtholdrows = drows.map(lambda x: str(x[3]).strip() if len(x)>5 else "")
		amtholdrows = amtholdrows.map(lambda x: x.split(" ")[0].strip() if " " in x else x)
		istotalrow = fees.map(lambda x: False if bool(re.search(r'(ACTIVE)',x)) else True)

		feesheet = pd.DataFrame({
			'CaseNumber': cnum,
			'Total': '',
			'Code': coderows.tolist(),
			'Payor': payorrows.tolist(),
			'AmtDue': amtduerows.tolist(),
			'AmtPaid': amtpaidrows.tolist(),
			'Balance': balancerows.tolist(),
			'AmtHold': amtholdrows.tolist()
			})

		totalrdf = {
			'Total': 'TOTAL',
			'CaseNumber': cnum,
			'Code': '',
			'Payor': '',
			'AmtDue': tdue,
			'AmtPaid': tpaid,
			'Balance': tbal,
			'AmtHold': thold
		}


		feesheet = feesheet.append(totalrdf, ignore_index=True)

		try:
			d999 = feesheet[feesheet['Code']=='D999']['Balance']
		except (TypeError, IndexError):
			d999 = ""

		owe_codes = " ".join(feesheet['Code'][feesheet.Balance.str.len() > 0])
		codes = " ".join(feesheet['Code'])
		allrows = actives
		allrows.append(totalrow)
		allrowstr = "\n".join(allrows)
		return [tdue, tbal, d999, owe_codes, codes, allrowstr, feesheet]

def getCharges(text: str, cnum: str):
	# get all charges matches
	ch = re.findall(r'(\d{3}\s{1}.{1,100}?.{3}-.{3}-.{3}.{10,75})', str(text), re.MULTILINE)
	c = []
	for a in ch:
		b = str(a).replace("Sentences","").replace("Sentence 1","").replace("SentencesSentence 1","").replace("Sentence","").replace("Financial","")
		if b[-2:] == " 1" or b[-2:] == " 0":
			b = b.replace(" 1","").replace(" 0","").strip()
		if ":" in b:
			continue
		c.append(re.sub(r'[a-z]*','', b))
	cind = range(0, len(c))
	charges = pd.DataFrame({'Charges': c,'parentheses':'','decimals':''},index=cind)
	charges['CaseNumber'] = charges.index.map(lambda x: cnum)
	# find table fields
	split_charges = charges['Charges'].map(lambda x: x.split(" "))
	charges['Num'] = split_charges.map(lambda x: x[0].strip())
	charges['Code'] = split_charges.map(lambda x: x[1].strip()[0:4])
	charges['Felony'] = charges['Charges'].map(lambda x: bool(re.search(r'FELONY',x)))
	charges['Conviction'] = charges['Charges'].map(lambda x: bool(re.search(r'GUILTY|CONVICTED',x)))
	charges['VRRexception'] = charges['Charges'].map(lambda x: bool(re.search(r'(A ATT|ATTEMPT|S SOLICIT|CONSP)',x)))
	charges['CERVCode'] = charges['Code'].map(lambda x: bool(re.search(r'(OSUA|EGUA|MAN1|MAN2|MANS|ASS1|ASS2|KID1|KID2|HUT1|HUT2|BUR1|BUR2|TOP1|TOP2|TPCS|TPCD|TPC1|TET2|TOD2|ROB1|ROB2|ROB3|FOR1|FOR2|FR2D|MIOB|TRAK|TRAG|VDRU|VDRY|TRAO|TRFT|TRMA|TROP|CHAB|WABC|ACHA|ACAL)', x)))
	charges['PardonCode'] = charges['Code'].map(lambda x: bool(re.search(r'(RAP1|RAP2|SOD1|SOD2|STSA|SXA1|SXA2|ECHI|SX12|CSSC|FTCS|MURD|MRDI|MURR|FMUR|PMIO|POBM|MIPR|POMA|INCE)', x)))
	charges['PermanentCode'] = charges['Code'].map(lambda x: bool(re.search(r'(CM\d\d|CMUR)', x)))
	charges['CERV'] = charges.index.map(lambda x: charges['CERVCode'][x] == True and charges['VRRexception'][x] == False and charges['Felony'][x] == True)
	charges['Pardon'] = charges.index.map(lambda x: charges['PardonCode'][x] == True and charges['VRRexception'][x] == False and charges['Felony'][x] == True)
	charges['Permanent'] = charges.index.map(lambda x: charges['PermanentCode'][x] == True and charges['VRRexception'][x] == False and charges['Felony'][x] == True)
	charges['Disposition'] = charges['Charges'].map(lambda x: bool(re.search(r'\d{2}/\d{2}/\d{4}', x)))
	charges['CourtActionDate'] = charges['Charges'].map(lambda x: re.search(r'\d{2}/\d{2}/\d{4}', x).group() if bool(re.search(r'\d{2}/\d{2}/\d{4}', x)) else "")
	charges['CourtAction'] = charges['Charges'].map(lambda x: re.search(r'(BOUND|GUILTY PLEA|PROBATION|WAIVED|DISMISSED|TIME LAPSED|NOL PROSS|CONVICTED|INDICTED|OTHER|DISMISSED|FORFEITURE|TRANSFER|REMANDED|PROBATION|ACQUITTED|WITHDRAWN|PETITION|PRETRIAL|COND\. FORF\.)', x).group() if bool(re.search(r'(BOUND|GUILTY PLEA|PROBATION|WAIVED|DISMISSED|TIME LAPSED|NOL PROSS|CONVICTED|INDICTED|OTHER|DISMISSED|FORFEITURE|TRANSFER|REMANDED|PROBATION|ACQUITTED|WITHDRAWN|PETITION|PRETRIAL|COND\. FORF\.)', x)) else "")

	try:
		charges['Cite'] = charges['Charges'].map(lambda x: re.search(r'([^\s]{3}-[^\s]{3}-[^\s]{3}[^s]{0,3}?\)*)', x).group())
	except (AttributeError, IndexError):
		try:
			charges['Cite'] = charges['Charges'].map(lambda x: re.search(r'(.{3}-.{3}-.{3})',x).group())
		except (AttributeError, IndexError):
			pass
	try:
		charges['parentheses'] = charges['Charges'].map(lambda x: re.search(r'(\([A-Z]\))', x).group())
		charges['Cite'] = charges['Cite'] + charges['parentheses']
	except (AttributeError, IndexError):
		pass
	try:
		charges['decimals'] = charges['Charges'].map(lambda x: re.search(r'(\.[0-9])', x).group())
		charges['Cite'] = charges['Cite'] + charges['decimals']
	except (AttributeError, IndexError):
		pass

	charges['TypeDescription'] = charges['Charges'].map(lambda x: re.search(r'(BOND|FELONY|MISDEMEANOR|OTHER|TRAFFIC|VIOLATION)', x).group() if bool(re.search(r'(BOND|FELONY|MISDEMEANOR|OTHER|TRAFFIC|VIOLATION)', x)) else "")
	charges['Category'] = charges['Charges'].map(lambda x: re.search(r'(ALCOHOL|BOND|CONSERVATION|DOCKET|DRUG|GOVERNMENT|HEALTH|MUNICIPAL|OTHER|PERSONAL|PROPERTY|SEX|TRAFFIC)', x).group() if bool(re.search(r'(ALCOHOL|BOND|CONSERVATION|DOCKET|DRUG|GOVERNMENT|HEALTH|MUNICIPAL|OTHER|PERSONAL|PROPERTY|SEX|TRAFFIC)', x)) else "")
	charges['Description'] = charges['Charges'].map(lambda x: x[9:-1])
	charges['Description'] = charges['Description'].str.split(r'([^s]{3}-.{3}-.{3})', regex=True)
	charges['Description'] = charges['Description'].map(lambda x: x[2].strip() if bool(re.search(r'(\d{2}/\d{2}/\d{4})|\#|MISDEMEANOR|WAIVED|DISMISSED|CONVICTED|PROSS', x[0])) else ascii(x[0]).strip())
	charges['Description'] = charges['Description'].map(lambda x: x.replace("\'","").strip())
	charges.drop(columns=['PardonCode','PermanentCode','CERVCode','VRRexception','parentheses','decimals'], inplace=True)

	# counts
	conviction_ct = charges[charges.Conviction == True].shape[0]
	charge_ct = charges.shape[0]
	cerv_ct = charges[charges.CERV == True].shape[0]
	pardon_ct = charges[charges.Pardon == True].shape[0]
	perm_ct = charges[charges.Permanent == True].shape[0]
	conv_cerv_ct = charges[charges.CERV == True][charges.Conviction == True].shape[0]
	conv_pardon_ct = charges[charges.Pardon == True][charges.Conviction == True].shape[0]
	conv_perm_ct = charges[charges.Permanent == True][charges.Conviction == True].shape[0]

	# summary strings
	convictions = "; ".join(charges[charges.Conviction == True]['Charges'].tolist())
	conv_codes = " ".join(charges[charges.Conviction == True]['Code'].tolist())
	charge_codes = " ".join(charges[charges.Disposition == True]['Code'].tolist())
	dcharges = "; ".join(charges[charges.Disposition == True]['Charges'].tolist())
	fcharges = "; ".join(charges[charges.Disposition == False]['Charges'].tolist())
	cerv_convictions = "; ".join(charges[charges.CERV == True][charges.Conviction == True]['Charges'].tolist())
	pardon_convictions = "; ".join(charges[charges.Pardon == True][charges.Conviction == True]['Charges'].tolist())
	perm_convictions = "; ".join(charges[charges.Permanent == True][charges.Conviction == True]['Charges'].tolist())

	allcharge = "; ".join(charges['Charges'])
	if charges.shape[0] == 0:
		charges = np.nan

	return [convictions, dcharges, fcharges, cerv_convictions, pardon_convictions, perm_convictions, conviction_ct, charge_ct, cerv_ct, pardon_ct, perm_ct, conv_cerv_ct, conv_pardon_ct, conv_perm_ct, charge_codes, conv_codes, allcharge, charges]

# LOG METHODS

def log_complete(conf, start_time):
	path_in = conf['in_path']
	path_out = conf['out_path']
	case_max = conf['case_max']
	bsize = conf['batchsize']
	completion_time = time.time()
	elapsed = completion_time - start_time
	cases_per_sec = case_max/elapsed
	print(f'''
    ___    __                          __         
   /   |  / /___ __________  _________/ /__  _____
  / /| | / / __ `/ ___/ __ \\/ ___/ __  / _ \\/ ___/
 / ___ |/ / /_/ / /__/ /_/ / /  / /_/ /  __/ /    
/_/  |_/_/\\__,_/\\___/\\____/_/   \\__,_/\\___/_/     
																																										
	
	ALACORDER beta 6.6.4
	by Sam Robson	

	Searched {path_in} 
	Wrote to {path_out} 

	TASK SUCCEEDED ({case_max}/{case_max} cases)
	Completed export in {elapsed:.2f} seconds ({cases_per_sec:.2f}/sec)

''') 

def console_log(conf, on_batch: int, to_str: str):
	path_in = conf['in_path']
	path_out = conf['out_path']
	case_max = conf['case_max']
	bsize = conf['batchsize']
	plog = conf['print_log']
	if plog == True:
		print(to_str)
		print(f'''\n\n
	    ___    __                          __         
	   /   |  / /___ __________  _________/ /__  _____
	  / /| | / / __ `/ ___/ __ \\/ ___/ __  / _ \\/ ___/
	 / ___ |/ / /_/ / /__/ /_/ / /  / /_/ /  __/ /    
	/_/  |_/_/\\__,_/\\___/\\____/_/   \\__,_/\\___/_/     
																																											
		
		ALACORDER beta 6.6.4
		by Sam Robson	

		Searching {path_in} 
		Writing to {path_out} 

		Exported {on_batch*bsize} of {case_max}...
		Parsing case details into dataframe...

	''') 

	if plog == False:
		print(f'''\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
		    ___    __                          __         
		   /   |  / /___ __________  _________/ /__  _____
		  / /| | / / __ `/ ___/ __ \\/ ___/ __  / _ \\/ ___/
		 / ___ |/ / /_/ / /__/ /_/ / /  / /_/ /  __/ /    
		/_/  |_/_/\\__,_/\\___/\\____/_/   \\__,_/\\___/_/     
																																												
			
			ALACORDER beta 6.6.4
			by Sam Robson	

			Searching {path_in} 
			Writing to {path_out} 

			Exported {on_batch*bsize} of {case_max}...
			Parsing case details into dataframe...
		''') 

def console_log_txt(conf, on_batch: int, to_str: str):
	path_in = conf['in_path']
	path_out = conf['out_path']
	case_max = conf['case_max']
	bsize = conf['batchsize']
	plog = conf['print_log']
	if plog == True:
		print(to_str)
		print(f'''\n\n
	    ___    __                          __         
	   /   |  / /___ __________  _________/ /__  _____
	  / /| | / / __ `/ ___/ __ \\/ ___/ __  / _ \\/ ___/
	 / ___ |/ / /_/ / /__/ /_/ / /  / /_/ /  __/ /    
	/_/  |_/_/\\__,_/\\___/\\____/_/   \\__,_/\\___/_/     
																																											
		
		ALACORDER beta 6.6.4
		by Sam Robson	

		Searching {path_in} 
		Writing to {path_out} 

		Text extracted from {on_batch*bsize} of {case_max}...
		Extracting text from case directory

	''') 

	if plog == False:
		print(f'''\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n
		    ___    __                          __         
		   /   |  / /___ __________  _________/ /__  _____
		  / /| | / / __ `/ ___/ __ \\/ ___/ __  / _ \\/ ___/
		 / ___ |/ / /_/ / /__/ /_/ / /  / /_/ /  __/ /    
		/_/  |_/_/\\__,_/\\___/\\____/_/   \\__,_/\\___/_/     
																																												
			
			ALACORDER beta 6.6.4
			by Sam Robson	

			Searching {path_in} 
			Writing to {path_out} 

			Text extracted from {on_batch*bsize} of {case_max}...
			Extracting text from case directory
		''') 

