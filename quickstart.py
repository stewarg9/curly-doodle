from __future__ import print_function
import pickle
import requests
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import shutil
import json


# This access scope grants read-only access to the authenticated user's Photo Library
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
API_SERVICE_NAME = 'photoslibrary'
API_VERSION = 'v1'

CONFIG_DIR = 'config/'
CONFIG_FILE = 'app_config.json'

config_data = None

	
def get_service():
	""" Validates credentials and returns a service handle"""
	creds = get_credentials()
	service = build(API_SERVICE_NAME, API_VERSION, credentials = creds)
	
	return service

	
def get_credentials():
	"""Gets valid user credentials from storage.
	If nothing has been stored, or if the stored credentials are invalid,
	the OAuth2 flow is completed to obtain the new credentials.
	Returns:
		Credentials, the obtained credential.
	"""

	creds = None

	if os.path.exists(CONFIG_DIR + 'token.pickle'):
		with open(CONFIG_DIR + 'token.pickle', 'rb') as token:
			creds = pickle.load(token)
		# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(CONFIG_DIR + config_data['credentials_file'], SCOPES)
			creds = flow.run_console()
	
	# Save the credentials for the next run
	with open(CONFIG_DIR + 'token.pickle', 'wb') as token:
		pickle.dump(creds, token)

	print(creds)

	return creds

	
	
def download_file(service, item_dict):

	print(config_data)

	target_dir = config_data.get('download_dir')
	
	# Validation... 
	if target_dir is None:
		raise RuntimeError('Download Dir not specified in config file!')
		
	elif not os.path.isdir(target_dir):
		raise RuntimeError('Download Dir specified in config file does not exist!')
	
	
	filename = item_dict['filename']
	base_url = item_dict['baseUrl']
	mimeType = item_dict['mimeType']

	if 'image' in mimeType:

		download_url = base_url + '=d'#-w' + orig_width + '-h' + orig_height
	elif 'video' in mimeType:

		download_url = base_url + '=dv'

	else:
		return

	print('Downloading ', filename, ' (', download_url, ')...')

	response = requests.get(download_url, stream=True)
		
	create_date= item_dict['mediaMetadata']['creationTime'][0:10]
	
	day = create_date[8:10]
	month = create_date[5:7]
	year = create_date[0:4]	
	
	
	if config_data.get("dir_structure") == None:
		raise RuntimeError('Directory Structure not specified in config file.')
		
	elif config_data.get("dir_structure") == 'Y/M/D':
	
		if not os.path.isdir(target_dir + '/' + year):
			os.mkdir(target_dir + '/' + year)
			
		if not os.path.isdir(target_dir + '/' + year + '/' + month):
			os.mkdir(target_dir + '/' + year + '/' + month)
			
		if not os.path.isdir(target_dir + '/' + year + '/' + month + '/' + day):
			os.mkdir(target_dir + '/' + year + '/' + month + '/' + day)
	
		target_path = target_dir + '/' + year + '/' + month + '/' + day
	
	elif config_data.get('dir_structure') == 'YMD':
		
		targetpath = target_dir + '/' + year +  month + day
	
	else:
	
		raise RuntimeError('Unknown Directory Structure specified in config file.')
	
	
	with open(target_path + '/' + filename, 'wb') as out_file:
		print(response.raw)
		shutil.copyfileobj(response.raw, out_file)	






# List all files in photo library.
def retrieve_all_files(api_service):
	results = []
	page_token = None

	while True:
		try:
			param = {'pageSize':'10', 'fields':"nextPageToken,mediaItems(id,mediaMetadata,filename,base_url,productUrl)"}

			if page_token:
				param['pageToken'] = page_token

			files = api_service.mediaItems().list(**param).execute()
			
			# append the files from the current result page to our list
			results.extend(files.get('mediaItems'))

			# Google  API shows our items in multiple pages when the number of files exceed 100
			page_token = files.get('nextPageToken')

			if not page_token:
				break

		except errors.HttpError as error:
			print('An error has occurred:', error)
			break


	return results



# Search the Google Photo Library, using a pre-configured data filter. 
# Filter exists as a separate JSON file. 
def search_date_range(service):

	# Look for the pre-configured search query....
	with open(CONFIG_DIR + "/search_message_body.json") as json_data_file:
		filter = json.load(json_data_file)	

	results = list()
	page_token = None

	while True:
		try:

			if page_token:
				filter['pageToken'] = page_token

			picture_page = service.mediaItems().search(body=filter).execute()

			items = picture_page.get('mediaItems', [])
			if not items:
				print('No albums found.')
			else:
				
				
				#print('Items:')
				
				for item in items:
					
					create_date= item['mediaMetadata']['creationTime'][0:10]
					
					print(create_date)
					
					results.append(create_date)
					download_file(service, item)	


			# Google  API shows our items in multiple pages when the number of files exceed page sizein json file
			page_token = picture_page.get('nextPageToken')

			print(max(results))

			if not page_token:
				break

		except errors.HttpError as error:
			print('An error has occurred:', error)
			break

	print("Yo!")
	print(results)
	if len(results) > 0:

		# We've processed something- update the start date to reflect what we've processed. 

		max_date = max(results)

		new_date = {'day' : int(max_date[8:10]), 'month' : int(max_date[5:7]), 'year' : int(max_date[0:4]) }
		
		filter['filters']['dateFilter']['ranges'][0]['startDate'] = new_date
		
		# Look for the pre-configured search query....
		with open(CONFIG_DIR + "/search_message_body.json", "w") as json_data_file:
			json.dump(filter, json_data_file, indent=4, sort_keys=True)		




def main():

	global config_data

	# Look for the pre-configured search query....
	with open(CONFIG_DIR + "/app_config.json") as json_data_file:
		config_data = json.load(json_data_file)	

	service = get_service()

	search_date_range(service)




if __name__ == '__main__':
	main()		