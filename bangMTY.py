#! /usr/bin/env python

import time
import Queue
import pygame
from pygame.locals import *
import os
import wiringpi

if not pygame.font: print 'Warning, fonts disabled'
if not pygame.mixer: print 'Warning, sound disabled'


#  - GPIO: http://bit.ly/JTlFE3 (elinux.org wiki)
#          http://bit.ly/QI8sAU (wiring pi)
#          http://bit.ly/MDEJVo (wiringpi-python)

## TODO: 
#  - TWITTER: https://github.com/tweepy/tweepy
#             https://github.com/ryanmcgrath/twython
#  - GRAPHICS: http://bit.ly/96VoEC (pygame)


######### time constants
## how often to check twitter (in seconds)
TWITTER_CHECK_PERIOD = 10
## how often to check queue for new tweets to be processed (in seconds)
##     or, how much time between bang routines
QUEUE_CHECK_PERIOD = 10
## how long to keep motors on (in seconds)
MOTOR_ON_PERIOD = 0.5
## how long to wait between turning on motors (in seconds)
MOTOR_OFF_PERIOD = 0.3
## how long to keep each light on (in seconds)
LIGHT_ON_PERIOD = [0.25, 0.333]
## number of bangs per routine 
##     (this can be dynamic, based on length of tweet, for example)
NUMBER_OF_BANGS = 10

######### state machine
## different states motors can be in
(STATE_WAITING, STATE_BANGING_FORWARD, STATE_BANGING_BACK, 
 STATE_PAUSE_FORWARD, STATE_PAUSE_BACK) = range(5)
## state/time variables
currentMotorState = STATE_WAITING
bangsLeft = 0
lastTwitterCheck = time.time()
lastMotorUpdate = time.time()
currentLightState = [False, False]
lastLightUpdate = [time.time(), time.time()]

## tweet queue
tweetQueue = Queue.Queue()

######### GPIO stuff
MOTOR_PIN = [17, 18]
LIGHT_PIN = [22, 23]

os.system("gpio export "+str(MOTOR_PIN[0])+" out")
os.system("gpio export "+str(MOTOR_PIN[1])+" out")
os.system("gpio export "+str(LIGHT_PIN[0])+" out")
os.system("gpio export "+str(LIGHT_PIN[1])+" out")

gpio = wiringpi.GPIO(wiringpi.GPIO.WPI_MODE_SYS)
gpio.pinMode(MOTOR_PIN[0],gpio.OUTPUT)
gpio.pinMode(MOTOR_PIN[1],gpio.OUTPUT)
gpio.pinMode(LIGHT_PIN[0],gpio.OUTPUT)
gpio.pinMode(LIGHT_PIN[1],gpio.OUTPUT)

gpio.digitalWrite(MOTOR_PIN[0],gpio.LOW)
gpio.digitalWrite(MOTOR_PIN[1],gpio.LOW)
gpio.digitalWrite(LIGHT_PIN[0],gpio.LOW)
gpio.digitalWrite(LIGHT_PIN[1],gpio.LOW)

######### Windowing stuff
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption('Test')

background = pygame.Surface(screen.get_size())
background = background.convert()
background.fill((250, 250, 250))

screen.blit(background, (0, 0))
pygame.display.flip()

try:
    print "WAITING"
    while True:
        ## handle events
        for event in pygame.event.get():
            if event.type == MOUSEBUTTONDOWN:
                tweetQueue.put("messaged!!!")

        ## twitter check. not needed if using streams
        if (time.time()-lastTwitterCheck > TWITTER_CHECK_PERIOD):
            # TODO: check twitter here
            # build queue
            lastTwitterCheck = time.time()
    
        ## state machine for motors
        ## if motor is idle, and there are tweets to process, start dance
        if ((currentMotorState==STATE_WAITING) and
            (time.time()-lastMotorUpdate > QUEUE_CHECK_PERIOD) and
            (not tweetQueue.empty())):
            print "BANG FWD"
            tweetText = tweetQueue.get()
            # TODO: display message?
            gpio.digitalWrite(MOTOR_PIN[0],gpio.HIGH)
            gpio.digitalWrite(MOTOR_PIN[1],gpio.LOW)
            currentMotorState=STATE_BANGING_FORWARD
            lastMotorUpdate = time.time()
            bangsLeft = NUMBER_OF_BANGS
        ## if motor0 has been on for a while, pause, then reverse direction
        elif ((currentMotorState==STATE_BANGING_FORWARD) and
              (time.time()-lastMotorUpdate > MOTOR_ON_PERIOD) and
              (bangsLeft > 0)):
            gpio.digitalWrite(MOTOR_PIN[0],gpio.LOW)
            gpio.digitalWrite(MOTOR_PIN[1],gpio.LOW)
            currentMotorState=STATE_PAUSE_BACK
            lastMotorUpdate = time.time()            
        ## if we're done pausing, proceed
        elif ((currentMotorState==STATE_PAUSE_BACK) and
              (time.time()-lastMotorUpdate > MOTOR_OFF_PERIOD) and
              (bangsLeft > 0)):
            print "BANG BACK"
            gpio.digitalWrite(MOTOR_PIN[0],gpio.LOW)
            gpio.digitalWrite(MOTOR_PIN[1],gpio.HIGH)
            currentMotorState=STATE_BANGING_BACK
            lastMotorUpdate = time.time()
            bangsLeft -= 1
        ## if motor1 has been on for a while, pause, then reverse direction
        elif ((currentMotorState==STATE_BANGING_BACK) and
              (time.time()-lastMotorUpdate > MOTOR_ON_PERIOD) and
              (bangsLeft > 0)):
            gpio.digitalWrite(MOTOR_PIN[0],gpio.LOW)
            gpio.digitalWrite(MOTOR_PIN[1],gpio.LOW)
            currentMotorState=STATE_PAUSE_FORWARD
            lastMotorUpdate = time.time()            
        ## if we're done pausing, proceed
        elif ((currentMotorState==STATE_PAUSE_FORWARD) and
              (time.time()-lastMotorUpdate > MOTOR_OFF_PERIOD) and
              (bangsLeft > 0)):
            print "BANG FWD"
            gpio.digitalWrite(MOTOR_PIN[0],gpio.HIGH)
            gpio.digitalWrite(MOTOR_PIN[1],gpio.LOW)
            currentMotorState=STATE_BANGING_FORWARD
            lastMotorUpdate = time.time()
        ## if no more bangs left
        elif((currentMotorState != STATE_WAITING) and 
             (bangsLeft <= 0) and 
             (time.time()-lastMotorUpdate > MOTOR_ON_PERIOD)):
            print "WAITING"
            gpio.digitalWrite(MOTOR_PIN[0],gpio.LOW)
            gpio.digitalWrite(MOTOR_PIN[1],gpio.LOW)
            gpio.digitalWrite(LIGHT_PIN[0],gpio.LOW)
            gpio.digitalWrite(LIGHT_PIN[1],gpio.LOW)
            currentMotorState=STATE_WAITING
            lastMotorUpdate = time.time()
    
        ## state machine for lights
        ## if banging, flicker the lights
        if (currentMotorState != STATE_WAITING):
            for i in range(0,2):
                if (time.time()-lastLightUpdate[i] > LIGHT_ON_PERIOD[i]):
                    currentLightState[i] = not currentLightState[i]
                    gpio.digitalWrite(LIGHT_PIN[i],currentLightState[i])
                    lastLightUpdate[i] = time.time()

except KeyboardInterrupt:
    print "Cleaning up GPIO"
    gpio.digitalWrite(MOTOR_PIN[0],gpio.LOW)
    gpio.digitalWrite(MOTOR_PIN[1],gpio.LOW)
    gpio.digitalWrite(LIGHT_PIN[0],gpio.LOW)
    gpio.digitalWrite(LIGHT_PIN[1],gpio.LOW)

