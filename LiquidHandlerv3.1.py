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
import csv

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
#Read in coordinates.csv and store them into variables
varName = []
coords = []
with open('coordinates.csv', 'r') as f:
    reader = csv.reader(f, delimiter=',')
    for row in reader:
        varName.append(row[0])
        coords.append(float(row[1]))

d = dict(zip(varName,coords))
#Convert dict objects back into variable names
for key,val in d.items():
    exec(key + '=val')

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
marlinOut = ''
coordX = 0
coordY = 0
coordZ = 0
activeTab = ""
#----------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------
#FUNCTIONS 
#Sending Marlin G-code commands to Arduino through serial 
def serialSend(command):
    global out
    global coordX
    global coordY
    global coordZ
    ser.write(command + "\r\n") #Command string
    out = '' #Clear buffer
    time.sleep(1)
    while ser.inWaiting() > 0: #Read buffer
        out += ser.read(1)
    if out != '':
        print (">>" + out)
        #time.sleep(1)
        if command == 'M114':
            marlinOut = out
            coordX = float(marlinOut[marlinOut.find('X')+2:marlinOut.find('X')+6])
            coordY = float(marlinOut[marlinOut.find('Y')+2:marlinOut.find('Y')+6])
            coordZ = float(marlinOut[marlinOut.find('Z')+2:marlinOut.find('Z')+6])
            print(coordX,coordY,coordZ)
    print (command)
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
	string = stringFormat(None,None,60,None,900) #60
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
	string = stringFormat(None,None,72.75,None,400)
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
	string = stringFormat(None,None,35,None,900) #36.25
	serialSend(string)
	
	#time.sleep(1)
	if firstFlag == 0:
		string = stringFormat(None,None,None,7.75,900)
		serialSend(string)
	else:
		string = stringFormat(None,None,None,15.5-7.75*(count % 2 +1),900)
		serialSend(string)
	#serialSend("G1 E0 F200")
	serialSend("G1 Z20 F700")
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
					moduleGap += 6.65
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
					moduleGap += 6.65
				aspirate(slideX,slideY,j,2800,0)
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
					moduleGap += 6.65
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
					moduleGap += 6.65
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
	serialSend("G1 E21 F400") 
	serialSend("G1 E3 F900")
	serialSend("G1 Z2 F900")
	homeE()
	time.sleep(1)
	serialSend("G28 Z")
	#time.sleep(1)
#-----------------------------------------------------------------------------------------
#Home E axis 
def homeE ():
	#time.sleep(1)
	Eend = 1 #E axis endstop status
	try:
		while Eend:
			if GPIO.input(11):
				print ("HIGH")
				serialSend("G1 E2 F900") #Lower E by 2mm after switch closed
				serialSend("G90")
				Eend = 0
			else:
				print ("LOW")
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
	f.write("Pictor Liquid Handler Log\n\n")
	f.write(cTime + "\n")

	print ("Initialisation...")
	message = "Initialisation..."
	serialSend("M114")
	#Initialise and maintain heater at 40deg
	serialSend("M140 S40 R40")
	print ("Heater ON")
	message = "Heater ON"
	#Turn on fan 
	serialSend("M106")
	print ("Fan ON")
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
	print ("Homing...")
	message = "Homing..."
	serialSend("G28 Z") #Home Z first to avoid collisions 
	serialSend("G28 XY")

	#Home E
	homeE()
	print ("Homing COMPLETE")
	message = "Homing COMPLETE"


#----------------------------------------------------------------------------------------
	#MAIN PHASE
	#User input for number of slide and modules
	message = "Enter the number of slides"
	while slideNum == 0:
		print ("Enter number of slides: ")
		time.sleep(1)
	time.sleep(0.5)
	message = str(slideNum) + " slides selected"
	progressPercent = 1
	listCount +=1
	#numSlide = 2
	#numSlide = int(raw_input("Enter the number of slides: "))
	#print "Number of slides selected: %d" %(numSlide)

	#if numSlide == 1:
		#numMod = int(raw_input("Enter the number of modules: "))
		#print "Number of modules selected: %d" %(numMod)
	#count = wash(3,1,count)
	#Loop through main program
	#Dispense samples
	#count = 12
	print("Dispensing Samples...")
	for i in xrange(2*slideNum):
		if (i != 0 and i % 2 == 0 ):
			moduleGap += 6.65
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
			moduleGap += 6.65
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
	#Dispense ConjG , Det , Sub
	for k in xrange(3):
		listCount += 1;
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
				moduleGap += 6.65
			vol = 15.5
			speed = 900
			if slideNum == 1 or (slideNum == 3 and j == 4):
				vol = 7.75
			if j % 4 == 0:
				pickFluid(reserveX,conjGY+(reserveGap*k),vol)
				speed = 5000
			dispense(slideX,slideYDis,j,speed,vol,1)

		homeE() #Home E as sometimes it loses its zero position
		moduleGap = 0
		progressPercent += 10
		listCount += 1;

		if k == 2: #5 minute incubation for substrate 
			IncubationTime = incubation(300) 
			progressPercent += 5
			listCount += 1;
		else:
			IncubationTime = incubation(1800)
			progressPercent += 5
			listCount += 1;

		#for j in xrange(0,2*slideNum,2)		
		print("Aspirating %d..." %(k+1))
		speed = 900
		for j in xrange(2*slideNum):
			if (j != 0 and j % 2 == 0):
				moduleGap += 6.65
			aspirate(slideX,slideY,j,speed,1)
			speed = 900
			if (j != 0 and j % 2 - 1 == 0):
				dispose(wasteLX,wasteLY)
				serialSend("G1 Z10 F900")	
				speed = 5000
		moduleGap = 0
		eject(wasteTX,wasteTY,0)

		progressPercent += 10
		listCount += 1;

		if k == 2: #Wash once for substrate
			submessage = "Final Wash"
			print("Final Wash")
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
	print ("Heater OFF")

	#Turn off fan 
	serialSend("M107")
	message = "Fan OFF"
	print ("Fan OFF")

	#Home XYZ
	serialSend("G28 Z")
	serialSend("G28 XY")

	#Home E 
	homeE()
	message = "Homing COMPLETE"
	print ("Homing COMPLETE")


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
#------------------------------------------------------------------------------------------          
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
#------------------------------------------------------------------------------------------
#Check for button states of main program
@app.route("/calibration/Home")
def calibHome():
    serialSend("G28 Z")
    serialSend("G28 X Y")
    time.sleep(0.5)
    print('Calib Home Pressed')
    serialSend("M114")
    #marlinOut = out
        #Get current coordinates and display onto calibration html\
    return redirect('/calibration')

@app.route("/calibration/Left")
def calibLeft():
    serialSend("G91")
    serialSend("G1 X10 F900")
    time.sleep(0.25)
    serialSend("G90")
    print("Calib Left Pressed")
    serialSend("M114")
    return redirect('/calibration')

@app.route("/calibration/Right")
def calibRight():
    serialSend("G91")
    serialSend("G1 X-10 F900")
    time.sleep(0.25)
    serialSend("G90")
    print("Calib Right Pressed")
    serialSend("M114")
    return redirect('/calibration')

@app.route("/calibration/Forward")
def calibForward():
    serialSend("G91")
    serialSend("G1 Y10 F900")
    time.sleep(0.25)
    serialSend("G90")
    print("Calib Forward Pressed")
    serialSend("M114")
    return redirect('/calibration')

@app.route("/calibration/Backward")
def calibBackward():
    serialSend("G91")
    serialSend("G1 Y-10 F900")
    time.sleep(0.25)
    serialSend("G90")
    print("Calib Backward Pressed")
    serialSend("M114")
    return redirect('/calibration')

@app.route("/calibration/Up")
def calibUp():
    serialSend("G91")
    serialSend("G1 Z-10 F700")
    time.sleep(0.25)
    serialSend("G90")
    print("Calib Up Pressed")
    serialSend("M114")
    return redirect('/calibration')

@app.route("/calibration/Down")
def calibDown():
    serialSend("G91")
    serialSend("G1 Z10 F700")
    time.sleep(0.25)
    serialSend("G90")
    print("Calib Down Pressed")
    serialSend("M114")
    return redirect('/calibration')   


#----------------------------------------------------------------------------------------
#URL JSON refresher  for updated string information
@app.route("/refresh")
def refresh():
	json = jsonify({'time': timer(t0), 'command': string, 'incubationTime' : incubationTime, 'message': message, 'submessage' : submessage, 'progressPercent' : (progressPercent), 'tipCount' : tipCount})
	return json	
#----------------------------------------------------------------------------------------
#URL JSON refresher  for updated string information
@app.route("/calibration/refreshCalib")
def refreshCalib():
	json = jsonify({'coordX': coordX, 'coordY': coordY, 'coordZ' : coordZ,'tipX':tipX,'tipY':tipY,'tipZ':tipZ,'sampleX':sampleX,'sampleY':sampleY,'sampleZ':samplePick,\
    'returnX':returnX,'returnY':returnY,'returnZ':returnZ,'wasteTX':wasteTX,'wasteTY':wasteTY,'wasteTZ':wasteTZ,'wasteLX':wasteLX,'wasteLY':wasteLY,'wasteLZ':wasteLZ, \
    'reserveX':reserveX,'reserveY':washY,'reserveZ':reservePick,'slideX':slideX,'slideY':slideY,'slideZ':slideZ})
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
#Form in calibration to go to XYZ Position
@app.route("/calibration/postCoord",methods = ['GET','POST'])
def calibForm():
    if request.method == 'POST':
        try:
            postX = 'X' + str(request.form['postX'])
            postY = 'Y' + str(request.form['postY'])
            postZ = 'Z' + str(request.form['postZ'])
            postF = 'F' + str(request.form['postF'])
            print(postX,postY,postZ,postF)
            poststr = 'G1' + " " + postX + " " + postY + " " + postZ + " " + postF
            print(poststr)            
        except:
            print("Error")
    serialSend(poststr)
    serialSend("M114")
    
    return redirect("/calibration")
#----------------------------------------------------------------------------------------
#Form to save new coordinates into coordinates.csv
@app.route("/calibration/saveCoord",methods = ['GET','POST'])
def calibSave():
    if request.method == 'POST':
        try:
            coordN = request.form['newCoord']
            print("return value:")
            print(coordN)
            #postY = 'Y' + str(request.form['postY'])
            #postZ = 'Z' + str(request.form['postZ'])
        except:
            print("Error")

    return redirect("/calibration")
    #----------------------------------------------------------------------------------------
@app.route("/calibration/activeTab",methods = ['POST'])
def activeTab():
    global activeTab
    if request.method == 'POST':
        try:
            activeTab = request.form['activeTab']
            print(activeTab)
            #postY = 'Y' + str(request.form['postY'])
            #postZ = 'Z' + str(request.form['postZ'])
        except:
            print("Error")

    return redirect("/calibration")
#----------------------------------------------------------------------------------------
#Return video stream back to /index from /video_feed
@app.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
    
#----------------------------------------------------------------------------------------
#Launch instructions page from nav bar
@app.route('/instructions')
def instructions():
	return render_template('instructions.html')

#----------------------------------------------------------------------------------------
#Launch calibration page from nav bar
@app.route('/calibration')
def calibration():
	return render_template('calibration.html')

#----------------------------------------------------------------------------------------
#Return to home from nav bar
@app.route('/main')
def home():
	return render_template('main.html')


if __name__ == "__main__":
	app.run(host = '0.0.0.0',port = 80,threaded = True)


#----------------------------------------------------------------------------------------
#                                      	     END
#----------------------------------------------------------------------------------------
