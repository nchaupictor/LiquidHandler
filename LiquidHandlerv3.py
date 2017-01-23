#----------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------
#                                 Liquid Handler Routine v3
#                          Date created: 23/11/2016 #Author: N Chau
#Added features: Host raspberry pi as webserver through flask, GUI controlled through server
#----------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------
#SETUP
import RPi.GPIO as GPIO
import time
from datetime import datetime
import serial
from flask import Flask,render_template,request,redirect,Response,jsonify
from camera import VideoCamera
import cv2

app = Flask(__name__)


#Open serial port between RPi and Arduino
ser = serial.Serial(
	port = "/dev/ttyACM0",
	baudrate = 250000,
	timeout = 1
)

#Set up GPIO pin for E axis endstop
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11,GPIO.IN)

#----------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------
#COORDINATES
offsetX = -3
offsetY = 8.5#12.5
#Tip Rack
tipX = 4.5 #-offsetX #4.95
tipY = 117 - offsetY
tipZ = 75
tipGap = 9.25

#Sample Rack
sampleX = 2 -offsetX
sampleY = 218.5 - offsetY #218.5
sampleGap = 9
samplePick = 49

#Return Tip Rack
returnX = 1 -offsetX
returnY = 260.5 - offsetY
returnZ = 67
returnGap = 9

#Reservoir 
reserveX = 117 -offsetX
reserveY = 210 +14
reservePick = 70
reserveGap = 14 #17.25

washY = 210 -offsetY
conjGY = washY + 28 -offsetY
detY = washY + 50 -offsetY
conjMY = washY + 40 -offsetY
subY = washY + 70 -offsetY

#Waste Liquid 
wasteLX = 117 - offsetX
wasteLY = 110
wasteLZ = 20

#Waste Tips
wasteTX = 117 -offsetX
wasteTY = 0
wasteTZ = 40

#Slide
slideX = 234 -offsetX
slideY = 152.25 -offsetY #150.5
slideYDis = 154.25 -offsetY
slideZ = 43.5
slideGap = 10.2
slideAspZ = 47.75#48
#Gap between slide modules
moduleGap = 0

#Global variables
count = 0
message = ""
submessage = ""
string =""
incubationTime = 0
skip = 0
t0 = 0.0
slideNum = 0
tipEnd = "No"
progressPercent = 0
tipCount = 0
listCount = -1
#----------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------
#FUNCTIONS 
#Sending Marlin G-code commands to Arduino through serial 
def serialSend(command):
	ser.write(command + "\r\n") #Command string
	out = '' #Clear buffer
	time.sleep(1)
	while ser.inWaiting() > 0: #Read buffer
		out += ser.read(1)
	if out != '':
		print ">>" + out 
	print command
#-----------------------------------------------------------------------------------------
#Picking up Tip
def pickTip (X,Y,Z,count):
	global submessage
	global tipEnd
	global tipCount
	submessage = "Picking tips..."
	tipCount = count
	if count == 12: #Reached the end of tip box
		#tipEnd = True
		while tipEnd == "No":
			try: #Move pipette to ejection area 
				string = stringFormat(wasteTX,wasteTY,None,None,2500)
				serialSend(string)
				serialSend("G1 Z0 F900")
				serialSend("G4 S10")
				print("Please change tip box, press Ctrl + C to resume")
				time.sleep(20)
			except KeyboardInterrupt:
				print("Resuming...")
				tipEnd = False
				count = 0
		count = 0
	tipCount = count 
	tipEnd = "No"

	Y = Y - count * tipGap
	string = stringFormat(X,Y,None,None,5000)
	serialSend(string)
	string = stringFormat(None,None,60,None,900)
	serialSend(string)
	string = stringFormat(None,None,Z,None,400)
	serialSend(string)
	#serialSend("G1 Z75 F200")
	serialSend("G1 Z4 F900")
	serialSend("G28 Z")
	#time.sleep(1)
	count += 1
	return count 
#-----------------------------------------------------------------------------------------
#Picking up Sample
def pickSample (X,Y,count):
	global submessage
	submessage = "Picking sample..."
	Y = Y - count * sampleGap
	string = stringFormat(X,Y,None,None,5000)
	serialSend(string)
	string = stringFormat(None,None,33,None,900)
	serialSend(string)
	string = stringFormat(None,None,None,4.75,900)
	serialSend(string)
	string = stringFormat(None,None,44,None,400)
	serialSend(string)
	serialSend("G1 E0 F900")
	serialSend("G1 Z0 F900")
	#time.sleep(1)
#-----------------------------------------------------------------------------------------	
#Picking up Fluid
def pickFluid (X,Y,E):
	global submessage
	submessage = "Picking reagent..."
	string = stringFormat(X,Y,None,None,5000)
	serialSend(string)
	string = stringFormat(None,None,65,None,900)
	serialSend(string)
	string = stringFormat(None,None,None,E,900)
	serialSend(string)
	#serialSend("G1 E4.5 F200")
	#serialSend('G1 E9 F200')
	string = stringFormat(None,None,72.5,None,400)
	serialSend(string)
	serialSend("G1 E0 F900")
	serialSend("G1 Z20 F900")
	#time.sleep(1)
#-----------------------------------------------------------------------------------------
#Dispense 
def dispense (X,Y,count,F,vol,firstFlag):
	global submessage
	global moduleGap
	submessage = "Dispensing..."
	Y = Y + count * slideGap + moduleGap
	string = stringFormat(X,Y,None,None,F)
	serialSend(string)
	#time.sleep(1)
	#string = stringFormat(None,None,25,None,200)
	#serialSend(string)
	string = stringFormat(None,None,32,None,900)
	serialSend(string)
	#time.sleep(1)
	if firstFlag == 0:
		string = stringFormat(None,None,None,vol,900)
		serialSend(string)
	else:
		string = stringFormat(None,None,None,3.875*(count % 4 + 1),900)	
		serialSend(string)
	#time.sleep(1)
	serialSend("G1 E0 F900")
	#time.sleep(2)
#-----------------------------------------------------------------------------------------
#Aspirate
def aspirate (X,Y,count,F,firstFlag):
	global submessage
	global moduleGap
	submessage = "Aspirating..."
	Y = Y + count * slideGap + moduleGap
	string = stringFormat(X,Y,None,None,F)
	serialSend(string)
	#time.sleep(1)
	if (firstFlag == 0 or count % 2 == 0):
		string = stringFormat(None,None,None,15.5,900)
		serialSend(string)
	#time.sleep(1)
	#string = stringFormat(None,None,30,None,750)
	#serialSend(string)
	#time.sleep(1)
	#serialSend("G1 E9.5 F200")
	string = stringFormat(None,None,35.85,None,900) #36.25
	serialSend(string)
	
	#time.sleep(1)
	if firstFlag == 0:
		string = stringFormat(None,None,None,7.75,900)
		serialSend(string)
	else:
		string = stringFormat(None,None,None,15.5-7.75*(count % 2 +1),900)
		serialSend(string)
	#serialSend("G1 E0 F200")
	serialSend("G1 Z28 F900")
	#time.sleep(2)
#-----------------------------------------------------------------------------------------
#Wash 
def wash (num,firstFlag,count):
	global message
	global tipEnd
	global tipCount
	global moduleGap

	tipCount = count
	for i in xrange(num):
		message = "Wash " + str(i + 1) +"..." 
		if (firstFlag == 1 and i == 0):
			count = pickTip(tipX,tipY,tipZ,count)
			for j in xrange(2*slideNum):
				if (j != 0 and j % 2 == 0 ):
					moduleGap += 6.7
				vol = 15.5
				speed = 900
				if slideNum == 1 or (slideNum == 3 and j == 4):
					vol = 7.75
				if j % 4 == 0:
					pickFluid(reserveX,washY,vol)
					speed = 5000
				dispense(slideX,slideYDis,j,speed,vol,1)


			moduleGap = 0 

			for j in xrange(2*slideNum):
				if j != 0:
					count = pickTip(tipX,tipY,tipZ,count)
					tipCount = count	
				if (j != 0 and j % 2 == 0 ):
					moduleGap += 6.7 
				aspirate(slideX,slideY,j,3000,0)
				dispose(wasteLX,wasteLY)
				eject(wasteTX,wasteTY,0)


			moduleGap = 0
			
		else:
			if count == 12: #Reached the end of tip box
				#tipEnd = True
				while tipEnd == "No":
					try: #Move pipette to ejection area 
						string = stringFormat(wasteTX,wasteTY,None,None,2500)
						serialSend(string)
						serialSend("G1 Z0 F900")
						serialSend("G4 S10")
						print("Please change tip box, press Ctrl + C to resume")
						time.sleep(20)
					except KeyboardInterrupt:
						print("Resuming...")
						tipEnd = False
						count = 0
				count = 0
			tipEnd = "No"
			count = pickTip(tipX,tipY,tipZ,count)
			tipCount = count
			for j in xrange(0,2*slideNum):
				vol = 15.5 #Default to 200uL
				speed = 900
				if (j != 0 and j % 2 == 0 ):
					moduleGap += 6.7
				if slideNum == 1 or (slideNum == 3 and j == 4):
					vol = 7.75
				if j % 4 == 0:
					pickFluid(reserveX,washY,vol)
					speed = 5000
				dispense(slideX,slideYDis,j,speed,vol,1)


			moduleGap = 0
			speed = 900
			for j in xrange(0,2*slideNum):
				if (j != 0 and j % 2 == 0):
					moduleGap += 6.7
				aspirate(slideX,slideY,j,speed,1)
				speed = 900
				if (j != 0 and j % 2 -1 == 0):
					dispose(wasteLX,wasteLY)
					serialSend("G1 Z10 F900")
					speed = 5000	
			moduleGap = 0

			eject(wasteTX,wasteTY,0)

	return count	
#-----------------------------------------------------------------------------------------
#Dispose 
def dispose (X,Y):
	global submessage
	submessage = "Disposing..."
	serialSend("G1 Z10 F900")
	string = stringFormat(X,Y,None,None,5000)
	serialSend(string)
	string = stringFormat(None,None,19,None,900)
	serialSend(string)
	serialSend("G1 E15 F900")
	serialSend("G1 E0 F900")
	#time.sleep(1)
#-----------------------------------------------------------------------------------------
#Eject
def eject (X,Y,count):
	global submessage
	submessage = "Ejecting tips..."
	serialSend("G1 Z10 F550")
	Y = Y - count * returnGap
	string = stringFormat(X,Y,None,None,5000)
	serialSend(string)
	string = stringFormat(None,None,40,None,900)
	serialSend(string)
	serialSend("G1 E20 F400") 
	serialSend("G1 E3 F900")
	serialSend("G1 Z2 F900")
	homeE()
	serialSend("G28 Z")
	#time.sleep(1)
#-----------------------------------------------------------------------------------------
#Home E axis 
def homeE ():
	time.sleep(1)
	Eend = 1 #E axis endstop status
	try:
		while Eend:
			if GPIO.input(11):
				print "HIGH"
				serialSend("G1 E1.5 F900") #Lower E by 2mm after switch closed
				serialSend("G90")
				Eend = 0
			else:
				print "LOW"
				serialSend("G91") #Relative Positioning
				serialSend("G1 E-1 F900") #Raise E by 2mm until switch closed
		#serialSend("M114")
		serialSend("G92 E0")
		#serialSend("M114")
		#serialSend("G1 E10 F250")
		
	except KeyboardInterrupt:
		GPIO.cleanup() 
		serialSend("M81")
#------------------------------------------------------------------------------------------
#G-Code string formatter
def stringFormat (X = None,Y = None,Z = None, E = None,F = None): #Overload last variable for single Z and F commands
	global string 
	if Z is None and E is None:
		tempX = " X" + str(X)
		tempY = " Y" + str(Y)
		tempF = " F" + str(F)
		string = "G1" + tempX + tempY + tempF
	elif X is None and Y is None and E is None:
		tempZ = " Z" + str(Z)
		tempF = " F" + str(F)
		string = "G1" + tempZ + tempF
	elif X is None and Y is None and Z is None:
		tempE = " E" + str(E)
		tempF = " F" + str(F)
		string = "G1" + tempE + tempF		
	else:
		print("Incorrect String Syntax")

	time.sleep(2)
	return string
#------------------------------------------------------------------------------------------
#Incubation 
def incubation(seconds):
	global submessage
	global skip
	serialSend("G1 Z20 F750")
	serialSend("G4 S3")
	time.sleep(5)
	submessage = "Incubating..."
	#a = raw_input('Press any key to start incubation')
	#Incubate 30 minutes or keypress
	try:
		incubationTime = seconds/60
		print("%d Minute Incubation (or Ctrl + C to skip)" % incubationTime)
		for j in xrange(seconds,0,-1):
			s = str(j) + "s"
			get_incubationTime(j)
			#print("\r{0}".format(j)),
			print(s)
			time.sleep(1)
			if skip == 1:
				skip = 0 
				break
		#return incubationTime
		get_incubationTime(0)
	except KeyboardInterrupt:
		print("Incubation Skipped")
#----------------------------------------------------------------------------------------
#Main Program 
def runProgram():
	global count
	count = 0
	global message
	global submessage
	global progressPercent
	global moduleGap
	global listCount
	#INITIALISATION PHASE

	#Open File 
	cTime = str(datetime.now())
	Timestr = cTime[0:10]

	f = open(Timestr + str(".txt"),"a+")
	f.write("Pictor Liquid Handler Log\n")
	f.write(cTime + "\n")

	print "Initialisation..."
	message = "Initialisation..."
	serialSend("M114")
	#Initialise and maintain heater at 40deg
	serialSend("M140 S40 R40")
	print "Heater ON"
	message = "Heater ON"
	#Turn on fan 
	serialSend("M106")
	print "Fan ON"
	message = "Fan ON"

	#Set jerk 
	serialSend("M205 X10")
	#serialSend("M204 T2000") #Default Acceleration
	#serialSend("M203 X3000 Y3000 Z1000 E1000") #Feed Rate
	#serialSend("M210 Z900") #Homing Feed Rate

	#Start camera
	#cam = cv2.VideoCapture(0)
	#img = cam.read()

	#cv2.namedWindow("camera", cv2.CV_WINDOW_AUTOSIZE)
	#cv2.imshow("camera",img)

	#Home XYZ 
	print "Homing..."
	message = "Homing..."
	serialSend("G28 Z") #Home Z first to avoid collisions 
	serialSend("G28 XY")

	#Home E
	homeE()
	print "Homing COMPLETE"
	message = "Homing COMPLETE"
	progressPercent = 1
	listCount +=1

#----------------------------------------------------------------------------------------
	#MAIN PHASE
	#User input for number of slide and modules
	message = "Enter the number of slides"
	while slideNum == 0:
		print "Enter number of slides: "
		time.sleep(1)
	time.sleep(0.5)
	message = str(slideNum) + " slides selected"
	#numSlide = 2
	#numSlide = int(raw_input("Enter the number of slides: "))
	#print "Number of slides selected: %d" %(numSlide)

	#if numSlide == 1:
		#numMod = int(raw_input("Enter the number of modules: "))
		#print "Number of modules selected: %d" %(numMod)

	#Loop through main program
	#Dispense samples
	#count = 12
	print("Dispensing Samples...")
	for i in xrange(2*slideNum):
		if (i != 0 and i % 2 == 0 ):
			moduleGap += 6.7
		message = "Step 1.0 - Dispensing Sample " + str(i + 1)
		pickTip(tipX,tipY,tipZ,i)
		#pickTip(tipX,tipY,tipZ,12)
		pickSample(sampleX,sampleY,i)
		dispense(slideX,slideYDis,i,5000,4.75,0)
		count += 1
		#eject(returnX,returnY,i) 
		eject(tipX,tipY,i)

	moduleGap = 0
	#30 minute incubation
	progressPercent = 5
	listCount += 1;
	incubationTime = incubation(1800)
	progressPercent = 10
	listCount += 1;

	print("Aspirating Samples...")
	#Aspirate and dispose tips 
	for i in xrange(2*slideNum):
		if (i != 0 and i % 2 == 0 ):
			moduleGap += 6.7
		message = "Step 1.0 - Aspirating Sample " + str(i + 1)
		#pickTip(returnX,returnY,returnZ,i)
		pickTip(tipX,tipY,tipZ,i)
		aspirate(slideX,slideY,i,5000,0)
		dispose(wasteLX,wasteLY)
		eject(wasteTX,wasteTY,0)

	moduleGap = 0
	progressPercent = 15
	listCount += 1;
	print("Washing Samples...")
	#Wash , first wash flag set to 1
	count = wash(3,1,count)
	print("Count:  %d" % count)
	progressPercent = 20
	listCount += 1;

	#Dispense ConjG , Det , Sub
	for k in xrange(3):
		if k == 0:
			message = "Step 2.0 - Dispensing ConjG"
		elif k == 1: 
			message = "Step 3.0 - Dispensing Det"
		else:
			message = "Step 4.0 - Dispensing Sub"
		print("Dispensing %d..." %(k+1))
		
		count = pickTip(tipX,tipY,tipZ,count)
		for j in xrange(2*slideNum):
			if (j != 0 and j % 2 == 0 ):
				moduleGap += 6.7
			vol = 15.5
			speed = 900
			if slideNum == 1 or (slideNum == 3 and j == 4):
				vol = 7.75
			if j % 4 == 0:
				pickFluid(reserveX,conjGY+(reserveGap*k),vol)
				speed = 5000
			dispense(slideX,slideYDis,j,speed,vol,1)


		moduleGap = 0
		progressPercent += 10
		listCount += 1;

		if k == 2: #5 minute incubation for substrate 
			IncubationTime = incubation(300) 
			progressPercent += 10
			listCount += 1;
		else:
			IncubationTime = incubation(1800)
			progressPercent += 10
			listCount += 1;

		#for j in xrange(0,2*slideNum,2)		
		print("Aspirating %d..." %(k+1))
		speed = 900
		for j in xrange(2*slideNum):
			if (j != 0 and j % 2 == 0):
				moduleGap += 6.7
			aspirate(slideX,slideY,j,speed,1)
			speed = 900
			if (j != 0 and j % 2 - 1 == 0):
				dispose(wasteLX,wasteLY)
				serialSend("G1 Z10 F900")	
				speed = 5000
		moduleGap = 0
		eject(wasteTX,wasteTY,0)


		if k == 2: #Wash once for substrate
			submessage = "Final Wash"
			print("Final Wash")
			progressPercent += 10
			listCount += 1;
			count = wash(1,0,count)
		else:
			print("Washing %d..." %(k+1))
			count =	wash(3,0,count)

	message = "Final Incubation"
	print("Final Incubation")
	progressPercent += 5
	listCount += 1;
	IncubationTime = incubation(1800)

	progressPercent = 100
	
	#submessage = ""
	submessage = "Assay Complete"
	print("Assay Complete")
	                                                                                                                                                                                                                                                                                                                                                      
	cTime = str(datetime.now())
	f.write(cTime)
	f.close
#----------------------------------------------------------------------------------------
	#SHUTDOWN PHASE

	#Turn off heater
	serialSend("M140 S0")
	message = "Heater OFF"
	print "Heater OFF"

	#Turn off fan 
	serialSend("M107")
	message = "Fan OFF"
	print "Fan OFF"

	#Home XYZ
	serialSend("G28 Z")
	serialSend("G28 XY")

	#Home E 
	homeE()
	message = "Homing COMPLETE"
	print "Homing COMPLETE"


#------------------------------------------------------------------------------------------
#Server side functions
#Initialise timer 
def timer(init):
	current = time.time()
	elapsed = current - init 
	elapsed = round(elapsed,1)
	return elapsed
#------------------------------------------------------------------------------------------
#Extract incubation countdown timer
def get_incubationTime(s):
	global incubationTime
	incubationTime = s 
	return incubationTime

#------------------------------------------------------------------------------------------
#URL State Checker 
@app.route("/")
def index():
	template_data = {
		'time' : timer(t0),
		'command' : string,
		'incubationTime' : (incubationTime),
		'message' : message,
		'submessage' : submessage,
		'progressPercent' : (progressPercent)
	}
	return render_template('main.html',**template_data)
#Initialise USB (Izone) Camera Feed
def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
#Check for button states of main program
@app.route("/<state>")
def startProgram(state = None):
	if state == 'Start': 
		global t0
		t0 = time.time() #Start timing
		runProgram()
		#serialSend("M106")
		time.sleep(0.5)
		return redirect('/')
	if state == 'Stop':
		global message
		print("STOP PRESSED")
		message = "EMERGENCY STOP"
		serialSend("M112") #Emergency Stop 
		ser.reset_input_buffer() #Flush buffer 
		time.sleep(0.5)
		return redirect('/')
	if state == 'Skip': 
		global skip
		global incubationTime
		skip = 1 
		print("INCUBATION SKIPPED")
		incubationTime = 0
		time.sleep(0.5)
		return redirect('/')
		
	#template_data = {
		#'title' : state,
		#'time' : timer(t0),
		#'command' : string,
		#'incubationTime' : (incubationTime),
		#'message' : message,
		#'submessage' : submessage,
        #'progressPercent' : (progressPercent)
	#}
	#return render_template('main.html', **template_data)
#----------------------------------------------------------------------------------------
#URL JSON refresher  for updated string information
@app.route("/refresh")
def refresh():
	json = jsonify({'time': timer(t0), 'command': string, 'incubationTime' : incubationTime, 'message': message, 'submessage' : submessage, 'progressPercent' : (progressPercent), 'tipCount' : tipCount})
	return json	
#----------------------------------------------------------------------------------------
#URL JSON refresher for progress bar 
@app.route("/progress", methods = ['GET'])
def progress():
	progJ = progressPercent
	listC = listCount
	return jsonify(progJ=progJ,listC = listC)
#----------------------------------------------------------------------------------------
#Form for slide number submission
@app.route("/slide",methods = ['GET','POST'])
def slideform():
	global slideNum
	if request.method == "POST":
		try:
			text = request.form['text']
			slideNum = int(text)
			print(slideNum)
			message = text + " slides selected"
		except:
			print("Cannot obtain form data")
	return redirect("/")

#----------------------------------------------------------------------------------------
#Form for tip box change 
@app.route("/tip",methods = ['GET','POST'])
def tipform():
	global tipEnd 
	if request.method == "POST":
		try:
			text = request.form['tipChange']
			tipEnd = text
			print("Tip Status: ")
			print(tipEnd)
		except:
			print("Cannot obtain form data")
	return redirect("/")

#----------------------------------------------------------------------------------------
#Return video stream back to /index from /video_feed
@app.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    
#----------------------------------------------------------------------------------------
if __name__ == "__main__":
	app.run(host = '0.0.0.0',port = 80,threaded = True)


#----------------------------------------------------------------------------------------
#                                      	     END
#----------------------------------------------------------------------------------------
