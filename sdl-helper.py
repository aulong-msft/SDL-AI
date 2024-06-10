import os  
import openai  
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials
from dotenv import load_dotenv  

from array import array
import os
from PIL import Image
import sys
import time
  
# Load environment variables for Azure OpenAI
load_dotenv()  # take environment variables from .env.  
openai.api_type = "azure"  
openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"] 
openai_api_key = os.environ["AZURE_OPENAI_API_KEY"]   
deployment = os.environ["CHAT_COMPLETIONS_DEPLOYMENT_NAME"]  
openai_api_version = os.environ["API_VERSION"]  

# Load environment variables for Azure OpenAI Search
search_endpoint = os.environ["SEARCH_ENDPOINT"]  
search_key = os.environ["AZURE_SEARCH_API_KEY"]
search_index = os.environ["SEARCH_INDEX"]  

# Load environment variables for Azure Cognitive Services
computerVisionApiKey = os.environ['COMPUTER_VISION_API_KEY']  
computerVisionApiEndpoint = os.environ['COMPUTER_VISION_API_ENDPOINT']  
imageFilePath = os.environ['IMAGE_FILEPATH']  

#Function to authenticate Computer Vision OCR API
def authenticate(computerVisionApiEndpoint, computerVisionApiKey):  
    computervision_client = ComputerVisionClient(computerVisionApiEndpoint, CognitiveServicesCredentials(computerVisionApiKey))  
    return computervision_client  

#Function to extract text from image using Computer Vision OCR API    
def extract_text_from_image(computervision_client, imageFilePath):    
    with open(imageFilePath, "rb") as image_file:    
        read_results = computervision_client.read_in_stream(image_file, raw=True)    
    operation_location = read_results.headers["Operation-Location"]    
    operation_id = operation_location.split("/")[-1]    
    while True:    
        read_result = computervision_client.get_read_result(operation_id)    
        if read_result.status not in ['notStarted', 'running']:    
            break    
        time.sleep(1)    
    extracted_text = ""    
    if read_result.status == OperationStatusCodes.succeeded:    
        for text_result in read_result.analyze_result.read_results:    
            for line in text_result.lines:    
                extracted_text += line.text + "\n"    
    return extracted_text  
  
def generate_list_of_services(text, openai_endpoint, openai_api_key, openai_api_version, deployment):    
    recommendations = []    
    prompt = f"Prompt 1: You are a Microsoft Azure security engineer doing threat model analysis to identify and mitigate risk. Given the following text:\n{text}\n please find the relevant Azure Services and print them out. \n"    
    
    client = openai.AzureOpenAI(  
        azure_endpoint=openai_endpoint,  
        api_key=openai_api_key,  
        api_version=openai_api_version,  
    )  
    
    # Prompt tuning parameters    
    print(f"Input: {prompt}")    
    completions_response = client.chat.completions.create(  
        model=deployment,  
        messages=[  
            {  
                "role": "user",  
                "content": prompt,  
            },  
        ],  
    )  
    
    completion = completions_response.choices[0].message.content
    print(f"Chatbot: {completion}")    
    recommendations.append(completion)  # Add the completion to the list    
    
    return recommendations  
 
    
def main():    
    computervision_client = authenticate(computerVisionApiEndpoint, computerVisionApiKey)    
    extracted_text = extract_text_from_image(computervision_client, imageFilePath)    
    print(extracted_text)   
    recommendations = generate_list_of_services(extracted_text, openai_endpoint, openai_api_key, openai_api_version, deployment)
    print(recommendations)    
  
    
if __name__ == "__main__":    
    main()    