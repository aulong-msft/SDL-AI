import os  
import openai  
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from azure.core.credentials import AzureKeyCredential  
from msrest.authentication import CognitiveServicesCredentials  
from azure.search.documents import SearchClient
from dotenv import load_dotenv  
import os  
from azure.identity import DefaultAzureCredential  
import requests
from msal import PublicClientApplication



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
deployment_id = os.environ["DEPLOYMENT_ID"]

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
  
#Function to generate list of services from extracted text
def generate_list_of_services(text, openai_endpoint, openai_api_key, openai_api_version, deployment):    
    recommendations = []    
    prompt = f"Prompt 1: You are a Microsoft Azure security engineer doing threat model analysis to identify and mitigate risk. Given the following text:\n{text}\n please find only Azure Services and only print them out, please change the name to the azure service if its not entirely spelled out. \n"    
    
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
  
def generate_security_recommendations(service, openai_endpoint, openai_api_key, openai_api_version, deployment, search_endpoint, search_key, search_index):        
    client = openai.AzureOpenAI(      
        azure_endpoint=openai_endpoint,      
        api_key=openai_api_key,      
        api_version=openai_api_version,      
    )  
    
    # We'll generate a prompt for each service    
    prompt = f" what are the security threats and mitigations for the following azure services: {service}"  
    # Generate the completion with Azure Search data source  
    completions_response = client.chat.completions.create(      
        model=deployment,      
        messages=[  
            {  
                "role": "system",  
                "content": "You are an Azure security engineer, You are analyzing the threat landscape for this service each service and are providing actionable threats and mitigations for each service provided."  
            },    
            {      
                "role": "user",      
                "content": prompt,      
            },      
        ],  
        extra_body={  
                "data_sources": [  
                    {  
                        "type": "azure_search",  
                        "parameters": {  
                            "endpoint": search_endpoint,  
                            "index_name": search_index,  
                            "authentication": {  
                            "type": "api_key",  
                            "key": search_key  
                        }  
                        }  
                    }  
                ],
                "max_tokens": 100,  #The maximum number of tokens to generate (default is 2048).
                "temperature": 0.5, #Controls the "creativity" of the generated text. Higher values result in more diverse output (default is 1).
                "top_p": 1.0, #Controls the probability of selecting the next token based on its score (default is 1).
                "frequency_penalty": 0.0, #Controls the penalty applied to tokens based on their frequency in the training data (default is 0).
                "presence_penalty": 0.0, #Controls the penalty applied to tokens that are already present in the text (default is 0).
            }  
        )  
  
    completion = completions_response.choices[0].message.content    
  
    if "The requested information is not available in the retrieved data" in completion:  
        # Generate the completion without Azure Search data source  
        completions_response = client.chat.completions.create(      
            model=deployment,      
            messages=[
                {  
                "role": "system",  
                "content": "You are an Azure security engineer, You are analyzing the threat landscape for this service each service and are providing actionable threats and mitigations for each service provided."  
                },        
                {
                    "role": "user",      
                    "content": f"what are the security threats and mitigations for the following azure services:  {service}?",      
                },      
            ]  
        )  
  
        completion = completions_response.choices[0].message.content    
  
    print(f"Chatbot: {completion}")        
    
    return completion   

def setup_byod(deployment_id: str) -> None:
    """Sets up the OpenAI Python SDK to use your own data for the chat endpoint.

    :param deployment_id: The deployment ID for the model to use with your own data.

    To remove this configuration, simply set openai.requestssession to None.
    """

    class BringYourOwnDataAdapter(requests.adapters.HTTPAdapter):

        def send(self, request, **kwargs):
            request.url = f"{openai_endpoint}/openai/deployments/{deployment_id}/extensions/chat/completions?api-version={openai.api_version}"
            return super().send(request, **kwargs)

    session = requests.Session()

    # Mount a custom adapter which will use the extensions endpoint for any call using the given `deployment_id`
    session.mount(
        prefix=f"{openai_endpoint}/openai/deployments/{deployment_id}",
        adapter=BringYourOwnDataAdapter()
    )

    openai.requestssession = session


def main():    
  
    #setup BYOD with Azure Search          
    setup_byod(deployment_id)  
  
    #Call the Computer Vision functions to read an image with OCR and pass it to OpenAI to get an intell  
    computervision_client = authenticate(computerVisionApiEndpoint, computerVisionApiKey)            
    extracted_text = extract_text_from_image(computervision_client, imageFilePath)            
    service_list = generate_list_of_services(extracted_text, openai_endpoint, openai_api_key, openai_api_version, deployment)        
    print(service_list)      
  
    # Generate security recommendations for each service  
    security_recommendations = {}  
    for service in service_list:  
        recommendation = generate_security_recommendations(service, openai_endpoint, openai_api_key, openai_api_version, deployment, search_endpoint, search_key, search_index)  
        security_recommendations[service] = recommendation  
  
    # Print out the recommendations for each service    
    for service, recommendation in security_recommendations.items():    
        print(f" The Service: {service}")    
        print(f" The Recommendation: {recommendation}")    
    
if __name__ == "__main__":            
    main()    
  

