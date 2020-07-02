from django.http import HttpResponseBadRequest, HttpResponseServerError
import tensorflow
import keras
import json
import base64
import time
from datetime import date, datetime
import os
from imageai.Detection import ObjectDetection


def check_dirs(dirs):# function to check if the passed directories exist else create them
    for dir in dirs:
        if(not os.path.isdir(dir)):
            os.mkdir(dir)
    
def get_config(file_name):#function to get the config file else return exception
    try:
        json_config = json.load(open(file_name))
        return json_config
    except FileNotFoundError as error:
        raise HttpResponseServerError('File Not Found')

#function to load model from the model)path with the given detection_speed
def load_model(model_path , detection_speed):
    detector = ObjectDetection()
    detector.setModelTypeAsYOLOv3()
    detector.setModelPath(model_path)
    detector.loadModel(detection_speed=detection_speed)

    return detector

#function to detect objects from the image at image_path
def Detection(json_config, detector, objects, image_path, minimum_probability, unique_id):
    curr_date = str(date.today())#get the current date and time
    curr_time = str(datetime.now().strftime("%H-%M-%S"))

    #get the path to upload and detected directories 
    detected_dir = json_config['default_parameters']['detected_directory']
    upload_dir = json_config['default_parameters']['upload_directory']
    
    #get path to sub directories in uploads and detected named as per the current data 
    input_dir = upload_dir + curr_date + '/'
    output_dir =  detected_dir + curr_date + '/'

    #check for the existence of the above sub directories
    check_dirs([detected_dir, input_dir, output_dir])

    #getting path for the input and output images 
    input_path = input_dir + image_path
    output_path = output_dir + image_path

    if len(objects)!=0: #if objects are passed in request use custom detector
        custom = detector.CustomObjects() 

        for item in objects: #updating the dictionary to detect for passed objects 
            custom[item]='valid'

        try : #detect custom objects
            detections = detector.detectCustomObjectsFromImage(custom_objects = custom, input_image= input_path, output_image_path= output_path,minimum_percentage_probability=minimum_probability, thread_safe=True)
        except Exception as error:
            logger(error, unique_id)
            raise HttpResponseBadRequest('Error - {}'.format(error))
    else : # if no objects are passed(empty list) detect all 80 objects possible by the model

        try:
            detections = detector.detectObjectsFromImage(input_image= input_path, output_image_path= output_path,minimum_percentage_probability=minimum_probability, thread_safe=True)
        except Exception as error:
            logger(error, unique_id)
            raise HttpResponseBadRequest('Error - {}'.format(error))  

    #delete_image(input_path)
    return detections

def upload_image(json_config, image_file, image_name, image_type, unique_id):

    curr_date = str(date.today())
    curr_time = str(datetime.now().strftime("%H-%M-%S"))

    uploaded_dir = json_config['default_parameters']['upload_directory']

    input_dir = uploaded_dir + curr_date + '/'

    check_dirs([uploaded_dir, input_dir])

    #storing name of image to be uploaded in name_date_time.image_type format 
    image_path = image_name + '_' + curr_date + '_' + curr_time + "." + image_type

    try: #converting the base64 image received to jpeg/png image
        with open(input_dir + image_path, "wb") as fh:
            fh.write(base64.b64decode(image_file))
    except Exception as error:
        logger(error, unique_id)
        raise HttpResponseBadRequest('Error - {}'.format(error))
    return image_path

def delete_image(input_path): #function to delete image
    if(os.path.exists(input_path)):
        os.remove(input_path)
         
#function to extract image related values from request
def handle_image_request(json_body, unique_id):
    image_file = json_body.get('image')
    image_name = json_body.get('image_name')
    image_type = json_body.get('image_type')

    #check if the data type of request values is valid for our purpose
    if not isinstance(image_file, str) or not isinstance(image_name, str) or not isinstance(image_type, str) :
        logger('Error - Invalid Request', unique_id)
        raise HttpResponseBadRequest('Error - Invalid Request')

    return image_name, image_type, image_file

#function to handle other request values
def handle_user_request(json_body, json_config):
    #assigning default values in case objects, min probability and detection speed haven't been specified
    objects = json_body.get('objects') if json_body.get('objects')!=None else json_config['default_objects']
    minimum_probability = json_body.get('minimum_probability') if json_body.get('minimum_probability')!=None else json_config['default_parameters']['default_probability']
    detection_speed = json_body.get('detection_speed') if json_body.get('detection_speed')!=None else json_config['default_parameters']['default_speed']
    unique_id = json_body.get('id')

    #check if the data type of request values is valid for our purpose
    if not isinstance(objects, list) or not isinstance(minimum_probability, int) and not isinstance(minimum_probability, float) or not isinstance(detection_speed, str) or not isinstance(unique_id, str) :
        logger('Error - Invalid Request', unique_id)
        raise HttpResponseBadRequest('Error - Invalid Request')

    return objects, minimum_probability, detection_speed, unique_id
    
#function to write error logs to the error.log file
def logger(error, unique_id):
    #write the errors in error.log file in time_unique_id_error format
    with open("error.log","a+") as log:
        curr_date = str(date.today())
        curr_time = str(datetime.now().strftime("%H-%M-%S"))
        log_time = curr_date + '_' + curr_time 
        log.write('\n'+log_time + unique_id + '-' + str(error))