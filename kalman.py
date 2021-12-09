# -*- coding: utf-8 -*-
"""Applies a Kalman filter and returns current state x,y,theta as a 3*1 np.array
Inputs:
    - state = np.array([x_k-1,y_k-1,theta_k-1]) is the state at step k-1. theta is in rad.
    - Sigma is the 3*3 np.array which corresponds to the covariance matrix of the states
    - motorspeed = [speedR, speedL] is the motor.target which is given to Thymio at step k (units unknown)
    - history = [state_(k-N), state_(k-(N-1)), ..., state(k-1)] where N is the horizon chosen for keeping the history
    - camera = [(x,y), theta, is_working] is the position of thymio given by vision. 
    is_working is a boolean that indicates whether the camera faced an issue.
    - Ts is the sampling time in seconds

Outputs:
    updated versions of state, Sigma, history at step k
"""
import numpy as np
import math
from scipy.interpolate import interp1d

STD_WHEELSPEED = 20         #std dev. for actual vs. expected linear speed of wheels, in pixels
STD_MEASURE_COORDS = 20     #in pixels
STD_MEASURE_THETA = 0.01

THRESHOLD_DISTANCE = 80     #in pixels
THRESHOLD_THETA = 0.8

POS_CORRECTION_FACTOR = 3
ANGLE_CORRECTION_FACTOR = 3.6


def kalmanfilter(state,Sigma,motorspeed,history, camera, Ts, meters_to_pixels, AXLE_LENGTH):
    #Main function to be used
    
    #convert thymio motorspeed to linear speed (calibration)
    motorspeed = calibrate_motorspeed(motorspeed, meters_to_pixels)
    
    #predict next step
    state, Sigma, history = predict(state, Sigma, motorspeed, history, Ts, AXLE_LENGTH)
    state[2][0] = (state[2][0]+math.pi)%(2*math.pi) - math.pi  #put it in [-pi,pi]
    
    if camera[2] == True:
        #if the vision is available, proceed to update
        state, Sigma = update(state, Sigma, motorspeed, history, camera)
        state[2][0] = (state[2][0]+math.pi)%(2*math.pi) - math.pi  #put it in [-pi,pi]
    
    return state, Sigma, history


def predict(state, Sigma, motorspeed, history, Ts, AXLE_LENGTH):
    #equations:
        #x_k = Ax_(k-1) + f(Ts, theta_k)*[vright, vleft]
        #y_k = Cx_k
    #note: f is linearized to obtain B
    
    #initialize Q (noise due to wheels) and A
    Q = np.random.normal(0.0, STD_WHEELSPEED, (2,1))
    A = np.array([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])    
    
    #obtain B
    theta_new = state[2] + ANGLE_CORRECTION_FACTOR*Ts*(motorspeed[0]-motorspeed[1])/(2*AXLE_LENGTH) #only used to calculate B
    B = 0.5*np.array([[POS_CORRECTION_FACTOR*math.cos(theta_new),POS_CORRECTION_FACTOR*math.cos(theta_new)],\
                      [-POS_CORRECTION_FACTOR*math.sin(theta_new),-POS_CORRECTION_FACTOR*math.sin(theta_new)],\
                          [ANGLE_CORRECTION_FACTOR*1/AXLE_LENGTH, -ANGLE_CORRECTION_FACTOR*1/AXLE_LENGTH]])
    
    #update history and state (note: @ is the matrix multiplication)
    history = np.roll(history, -1, 0)
    history[-1] = np.reshape(state,(1,3))
    state = A @ state + Ts*B @ motorspeed
    
    #update Sigma, matrix of covariance
    process_noise = np.diag([(B @ Q) [0][0], (B@Q) [1][0], (B@Q) [2][0]])
    Sigma = (A.T @ Sigma @ A.T) + process_noise
    
    return state,Sigma,history


def update(state, Sigma, motorspeed, history, camera):
    
    #initialize matrices
    avg_history = np.mean(history,0)
    C = np.array([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]) #y_k = C*x_k
    R = np.diag([np.random.normal(0.0, STD_MEASURE_COORDS), \
                 np.random.normal(0.0, STD_MEASURE_COORDS), \
                 np.random.normal(0.0, STD_MEASURE_THETA)]) #measure noise
    
    #calculate updated state
    y = np.array([[camera[0][0]], [camera[0][1]], [camera[1]]])  #measured states
    innov = y - (C @ state)
    s = (C @ Sigma @ C.T) + R
    K = Sigma @ C.T @ np.linalg.inv(s) #optimal gain
    
    state_update = state + K @ innov
    
    #if the measured value is obviously wrong, then do NOT proceed to update
    posx = state_update[0][0]
    posy = state_update[1][0]
    hisx = avg_history[0][0]
    hisy = avg_history[0][1]
    
    if math.dist((posx,posy),(hisx,hisy)) < THRESHOLD_DISTANCE\
    and abs(state_update[2] - avg_history[0][2]) < THRESHOLD_THETA:
        state = state_update
        Sigma = (np.eye(3) - K@C) @ Sigma
        HISTORY_SIZE = np.size(history, 0)
        history = [np.reshape(state,(1,3))]*HISTORY_SIZE
    
    return state, Sigma

#%%
def calibrate_motorspeed(motorspeed, meters_to_pixels):
    #convert motor speed to linear speed (m/s)
    
    #measurements done in a 2.51m long corridor
    distance = 2.51                                 #length of corridor [m]
    thymio_instruction = [-300,-250,-200,-150,-100,-50,50,100,150,200,250,300]   #instruction given
    chrono = [-27,-33,-41,-54,-119,-140,140,119,54,41,33,27]                  #time to cross corridor [s]
    lin_speed = [distance/t for t in chrono]        #speed [m/s]
    

    
    #interpolate to convert instructions (motorspeed) to linear speed
    f = interp1d(thymio_instruction, lin_speed)
    
    speedRThymio = motorspeed[0]
    speedLThymio = motorspeed[1]
 
    if speedRThymio > 0 and speedLThymio >0 :
        speedRMetric = f(min(speedRThymio,300)).item()
        speedLMetric = f(min(speedLThymio,300)).item()
    elif speedRThymio < 0 and speedLThymio < 0 :
        speedRMetric = f(max(speedRThymio,-300)).item()
        speedLMetric = f(max(speedLThymio,-300)).item()
    elif speedRThymio > 0 and speedLThymio < 0 :
        speedRMetric = f(min(speedRThymio, 300)).item()
        speedLMetric = f(max(speedLThymio,-300)).item()
    else: #both 0 or speedRThymio < 0 and speedLThymio > 0
        speedRMetric = f(max(speedRThymio, -300)).item()
        speedLMetric = f(min(speedLThymio, 300)).item()

    speedRPixels = int(speedRMetric * meters_to_pixels)
    speedLPixels = int(speedLMetric * meters_to_pixels)
    
    #return a 2-by-1 np.array
    motorspeed = np.array([[speedRPixels],[speedLPixels]])
    return motorspeed







#Test: movement in straight line at 45°, camera measures x=y=theta=0 always
# meters_to_pixels = 1

# state0 = np.array([[0],[0],[45*math.pi/180]]) #3-by-1 np.array
# Sigma0 = np.diag([0.01,0.01,0.01])

# N = 15 #size of history
# history = [np.reshape(state0,(1,3))]*N

# motorspeed = [120,120] #command sent to Thymio
# camera = [(0,0),0,True] #live output of the camera
# Ts = 0.1 #sampling time

# #test it
# state, Sigma, history = kalmanfilter(state0,Sigma0,motorspeed,history, camera, Ts, meters_to_pixels)
# iter = 1
# print("Iteration {}".format(iter))
# print("State {}".format(state))
# print("Sigma {}".format(Sigma))
# #print("History {}".format(history))
# print("\n \n")
# for k in range(5):
#     state, Sigma, history = kalmanfilter(state,Sigma,motorspeed,history, camera, Ts, meters_to_pixels)
#     iter += 1
#     print("Iteration {}".format(iter))
#     print("State {}".format(state))
#     print("Sigma {}".format(Sigma))
#     #print("History {}".format(history))
#     print("\n \n")