import argparse
from datetime import datetime

# -------------------- TODO: Define path and api key --------------------

# MUST create .csv and set variable to its path
#path = "/path/to/time-keeping.csv"
path = "test.csv"

# OPTIONAL if you want to use telegram as a log, insert you api key and chat-ID
BOT_TOKEN = "9876543210:ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CHAT_ID = "0123456789" 

# OPTIONAL if you work different hours please change in HH:MM:SS format
workingHours = "08:00:00"
mandatoryBreak = "01:00:00"


# -------------------- Defining format of time values --------------------

fmtDate = "%Y-%m-%d"
fmtTime = "%H:%M:%S"
fmtDT = "%Y-%m-%d %H:%M:%S"


# -------------------- CSV tools --------------------

# Write contents of csv into 2d list
def readFile():
	with open(path, newline="", encoding="utf-8") as f:
		content = []
		for entry in f:
			# strip \n and seperate by comma
			content.append(entry.removesuffix("\n").split(","))
		return content

# Overwrite CSV with data
def reWriteFile(data):
	firstLoop = True
	with open(path, "w", encoding="utf-8") as f:
		for entry in data:
			if not firstLoop:
				f.write("\n")
			f.write(f"{entry[0]},{entry[1]}")
			if len(entry) > 2:
				f.write(f",{entry[2]}")
			if len(entry) > 3:
				f.write(f",{entry[3]}")
			firstLoop = False


# -------------------- Time conversion --------------------

def seconds_to_hhmmss(seconds: float) -> str:
    is_negative = seconds < 0
    total_seconds = abs(int(seconds))
    
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    formatted_time = f"{hours:02}:{minutes:02}:{secs:02}"

    return f"-{formatted_time}" if is_negative else formatted_time

def hhmmss_to_seconds(hhmmss: str) -> int:
    is_negative = hhmmss.startswith("-")
    time_str = hhmmss.lstrip("-")
    
    parts = time_str.split(":")
    if len(parts) != 3:
        raise ValueError("unsupported format, expected HH:MM:SS")

    hours, minutes, seconds = map(int, parts)
    total_seconds = hours * 3600 + minutes * 60 + seconds

    return -total_seconds if is_negative else total_seconds


# -------------------- User abilities --------------------
	
def checkin():
	date = datetime.now().strftime(fmtDate)
	startTime = datetime.now().strftime(fmtTime)

	data = readFile()
	# Check if today is already checked in
	try:
		if data[-1][0] == str(date):
			sendMessage(f"Already checked in today at {readFile()[-1][1]}")
			return
	except:
		pass

	# If not, add current date and time as checkin
	with open(path, "a", encoding="utf-8") as f:
		if len(data) > 0:
			f.write("\n")
		f.write(str(date))
		f.write("," + str(startTime))

	sendMessage(f"Good Morning! Bal: {getBalance()}\nCheck in on {date} was {startTime}")


def deleteUnfinishedCheckin():
	data = readFile()

	# Check if last entry has a checkout
	try:
		hhmmss_to_seconds(data[-1][2]) > 0
		sendMessage(f"No unfinished entry to remove.")
		return
	
	# If not, remove it
	except:
		waste = data.pop()
		reWriteFile(data)

	sendMessage(f"Removed check in at {waste[1]}.\nBal: {getBalance()}")


def checkout():
	date = datetime.now().strftime(fmtDate)
	endTime = datetime.now().strftime(fmtTime)

	data = readFile()

	# Check if last checkin was today
	if data[-1][0] != str(date):
		sendMessage(f"Not checked in.\nLast check in on {data[-1][0]}")
		return
	
	# Check if today is allready checked out
	elif len(data[-1]) == 3:
		sendMessage(f"Already checked out today at {data[-1][2]}")
		return
	# If a break is entered
	elif len(data[-1]) == 4:

		# Check if today is allready checked out
		try:
			if hhmmss_to_seconds(data[-1][2]) > 0:
				sendMessage(f"Already checked out today at {data[-1][2]}")
		# If not, check out
		except:
			data[-1][2] = endTime
			reWriteFile(data)
			sendMessage(f"Good Bye! Bal: {getBalance()}\nCheck out was {endTime}\nTodays break was {data[-1][3]}")
		
		return

	with open(path, "a", encoding="utf-8") as f:
		f.write("," + str(endTime))
	sendMessage(f"Good Bye! Bal: {getBalance()}\nCheck out was {endTime}")


def removeLastCheckout():
	date = datetime.now().strftime(fmtDate)
	data = readFile()

	# Check if last checkin was today
	if data[-1][0] != str(date):
		sendMessage(f"No checkout to remove today.\nLast check in on {data[-1][0]}")
		return
	
	# Try to remove checkout
	try:
		checkout = data[-1][2]
		if len(data[-1]) == 4:
			data[-1][2] = ""
		else:
			data[-1].pop()

		reWriteFile(data)
			
		sendMessage(f"Revoked checkout at {checkout}.\nBal: {getBalance()}")
		return
	
	except:
		sendMessage("No checkout to remove today")


# If you take a break above the usual 60 minutes, you can add it manually
def addBreak(minutes):
	data = readFile()
	breakEntry = f",{seconds_to_hhmmss(minutes*60)}"

	with open(path, "a", encoding="utf-8") as f:

		# If break is added before checkout, add empty entry for checkout
		if len(data[-1]) == 2:
			f.write(f",{breakEntry}")
			sendMessage(f"Added a break of {minutes} minutes")

		# If break is added after checkout, add break
		elif len(data[-1]) == 3:
			f.write(breakEntry)
			sendMessage(f"Added a break of {minutes} minutes")
		
		# If there is allready a break entered, add the current break to it
		elif len(data[-1]) == 4:
			breakEntry = seconds_to_hhmmss(hhmmss_to_seconds(data[-1][3]) + (minutes * 60))
			data[-1][3] = breakEntry
			reWriteFile(data)
			sendMessage(f"Added a break of {minutes} minutes, for a total of {data[-1][3]}")
		
		# If none of the options above apply, the CSV must be checked manualy 
		else:
			sendMessage("Could not apply break time to most recent entry.\nPlease review your .csv!")


# -------------------- Calculate overtime --------------------

# Return overtime
def getBalance() -> str:

	absolutBalance = 0

	# Daily workload + mandatory break in hours
	dailyLoad = hhmmss_to_seconds(workingHours) + hhmmss_to_seconds(mandatoryBreak)

	for entry in readFile():

		# Try to calculate balance
		try:
			# Get start and end timestamp in relative unix format
			tStart = hhmmss_to_seconds(entry[1])
			tEnd = hhmmss_to_seconds(entry[2])

			# Calculate balance of entry
			entryBalance = tEnd - tStart -dailyLoad

			# Try to subtract additional break
			try:
				breakTime = hhmmss_to_seconds(entry[3])
				entryBalance -= breakTime
			except:
				pass

			# Add balance of entry to ansolute Balance
			absolutBalance += entryBalance

		# If balance can't be calculated, ignore entry
		except:
			pass

	return seconds_to_hhmmss(absolutBalance)


# -------------------- Handle Arguments --------------------

def main():
	# Create ArgumentParser
	parser = argparse.ArgumentParser(description="ZeEr is a tool for automized time tracking")

	# Add flags for environment
	parser.add_argument('-t', action='store_true', help='Send output to Telegram')

	# Add flags for functions
	parser.add_argument('-i', action='store_true', help='Check in')
	parser.add_argument('-o', action='store_true', help='Check out')
	parser.add_argument('-d', action='store_true', help='Delete unfinished entry')
	parser.add_argument('-r', action='store_true', help='Revoke check out')
	parser.add_argument('-b', type=int, help='Enter additional break time in minutes')

	# Parse arguments
	args = parser.parse_args()

	# Set Telegram or StdOut
	global sendMessage
	if args.t:
		import requests

		def sendMessage(message):
			url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
			payload = {"chat_id": CHAT_ID, "text": message}

			response = requests.post(url, data=payload)
			print(response.json())
	else:
		def sendMessage(message):
			print(message)


	# Evaluation
	if args.i:
		checkin()
	elif args.o:
		checkout()
	elif args.r:
		removeLastCheckout()
	elif args.d:
		deleteUnfinishedCheckin()
	elif args.b:
		addBreak(args.b)
	else:
	    sendMessage("Please add argument when calling the script to specify action. See --help for options")
		

if __name__ == "__main__":
    main()