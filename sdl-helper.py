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
from azure.mgmt.resourcegraph import ResourceGraphClient  
from azure.mgmt.resourcegraph.models import QueryRequest  


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
    prompt = f"Prompt 1: You are a Microsoft Azure security engineer doing threat model analysis to identify and mitigate risk. Given the following text:\n{text}\n please find the relevant Azure Services and only print them out. \n"    
    
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

def get_security_recommendations(service):  
    # Authenticate with Azure  
    credential = DefaultAzureCredential()  
    resource_graph_client = ResourceGraphClient(credential)  
  
    # Create a query to get security recommendations for the given service  
    query = f"""  
    securityresources  
    | where type == 'microsoft.security/assessments'  
    | where properties.displayName == '{service}'  
    | project properties.displayName, properties.status.code, properties.metadata.severity  
    """  
    print('BELOW IS THE QUERY')  
    print(query)  
    query_request = QueryRequest(  
        subscriptions=[os.environ["AZURE_SUBSCRIPTION_ID"]],  
        query=query  
    )  
  
    # Execute the query  
    results = resource_graph_client.resources(query_request)  
    print('BELOW IS THE RESULTS')  
    print(results.data)  
      
    # Process the results  
    recommendations = []  
    for item in results.data:  
        print('BELOW IS THE ITEM')  
        print(item)  
        recommendations.append({  
            "Service": item["properties"]["displayName"],  
            "Status": item["properties"]["status"]["code"],  
            "Severity": item["properties"]["metadata"]["severity"]  
        })  
  
    return recommendations  

from azure.mgmt.resourcegraph import ResourceGraphClient  
from azure.mgmt.resourcegraph.models import QueryRequest  
from azure.identity import DefaultAzureCredential  
  
def check_service_in_assessments(service):  
    # Authenticate with Azure  
    credential = DefaultAzureCredential()  
    resource_graph_client = ResourceGraphClient(credential)  
      
    # Query to get all distinct displayNames in the security assessments  
    query = """  
    securityresources  
    | where type == 'microsoft.security/assessments'  
    | distinct properties.displayName  
    """  
      
    query_request = QueryRequest(  
        subscriptions=[os.environ["AZURE_SUBSCRIPTION_ID"]],  
        query=query  
    )  
  
    # Execute the query  
    results = resource_graph_client.resources(query_request)  
      
    # Check if the service is in the results  
    for item in results.data:  
        if item['properties']['displayName'] == service:  
            return True  
  
    return False  

def get_all_security_assessments():  
    # Authenticate with Azure  
    credential = DefaultAzureCredential()  
    resource_graph_client = ResourceGraphClient(credential)  
      
    # Query to get all security assessments  
    query = """  
    securityresources  
    | where type == 'microsoft.security/assessments'  
    | project properties.displayName  
    """  
  
    query_request = QueryRequest(  
        subscriptions=[os.environ["AZURE_SUBSCRIPTION_ID"]],  
        query=query  
    )  
  
    # Execute the query  
    results = resource_graph_client.resources(query_request)  
  
    # Print out the results to see their structure  
    print(results.data)  
  
    # Extract the displayNames from the results  
    display_names = [item['properties']['displayName'] for item in results.data if 'properties' in item and 'displayName' in item['properties']]  
    return display_names  

  
def main():        
    computervision_client = authenticate(computerVisionApiEndpoint, computerVisionApiKey)        
    extracted_text = extract_text_from_image(computervision_client, imageFilePath)        
    print(extracted_text)       
  
    # Split the services string into individual services  
    service_list = generate_list_of_services(extracted_text, openai_endpoint, openai_api_key, openai_api_version, deployment)    
    individual_services = [service.strip() for service in service_list[0].split(',')]  
  
    # Get all security assessments  
    all_assessments = get_all_security_assessments()  
  
    all_recommendations = []    
    for service in individual_services:    
        if service in all_assessments:  
            print(f"Getting recommendations for {service}")  
            recommendations = get_security_recommendations(service)    
            all_recommendations.extend(recommendations)  
        else:  
            print(f"No assessments found for {service}")  
  
    print('BELOW ARE ALL THE RECOMMENDATIONS')    
    print(all_recommendations)    
  
if __name__ == "__main__":        
    main()   
