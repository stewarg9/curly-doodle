from __future__ import print_function
import pickle
import requests
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import shutil
import json


from datetime import date
from datetime import timedelta

#import pprint


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

	#print(config_data)

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

	print('Downloading ', filename, item_dict['mediaMetadata']['creationTime'][0:10])# , ' (', download_url, ')...')

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
		# print(response.raw)
		shutil.copyfileobj(response.raw, out_file)	





# Build a formatted date dictionary for the search query. 
def date_to_dict(the_date):
	
	#print(the_date)
	
	the_dict = dict()
	the_dict["day"] = the_date.day
	the_dict["month"] = the_date.month
	the_dict["year"] = the_date.year

	return the_dict




# Build a filter object, for the search. 
# 
# Format: 
#{
#    "filters": {
#        "dateFilter": {
#            "ranges": [
#                {
#                    "endDate": {"day": 31, "month": 12,"year": 2019},
#                    "startDate": {"day": 1,"month": 1, "year": 2019}
#                }
#            ]
#        }
#    },
#    "pageSize": 25
#}	
#~ def build_filter(start_date, end_date, page_size = 250):
	
	#~ start_date_dict = date_to_dict(start_date)
	#~ end_date_dict = date_to_dict(end_date)
		
	#~ search_dict = {}
	
	#~ search_dict["filters"] = {}
	#~ search_dict["filters"]["dateFilter"] = {}
	#~ search_dict["filters"]["dateFilter"]["ranges"] = []

	#~ search_hash = {"endDate" : end_date_dict, "startDate" : start_date_dict } 
	
	#~ search_dict["filters"]["dateFilter"]["ranges"].append(search_hash)
	
	#~ search_dict["pageSize"] = page_size
	
	#~ print(search_dict)



def build_filter(date, page_size = 100):
	
	date_dict = date_to_dict(date)
		
	search_dict = {}
	
	search_dict["filters"] = {}
	search_dict["filters"]["dateFilter"] = {}
	search_dict["filters"]["dateFilter"]["dates"] = []

	
	
	search_dict["filters"]["dateFilter"]["dates"].append(date_dict)
	
	search_dict["pageSize"] = page_size

	#print(search_dict)
	
	return search_dict
	




# Search the Google Photo Library, using a pre-configured data filter. 
# Filter exists as a separate JSON file. 
def search_date_range(service):

	# Read the last sync date from the config file; use this as the start date. 
	last_sync_date_parts = config_data["last_sync_date"].split("-")
	start_date = date(int(last_sync_date_parts[0]), int(last_sync_date_parts[1]), int(last_sync_date_parts[2]))

	# Single day offset... 
	day = timedelta(days=1)
	end_date = date.today() - day

	results = list()

	while start_date < end_date:

		print("start date: ", start_date, " end date:", start_date + day)

		# Build the filter object, including date range. 
		filter = build_filter(start_date)
		
		page_token = None

		while True:
			try:

				if page_token:
					filter['pageToken'] = page_token

				picture_page = service.mediaItems().search(body=filter).execute()

				items = picture_page.get('mediaItems', [])
				
				if not items:
					print('No items found.')
					
				else:
					
					print ("Found ", len(items), " items!")
					
					for item in items:
						
						create_date= item['mediaMetadata']['creationTime'][0:10]
						
						#print(create_date)
						
						results.append(create_date)
						download_file(service, item)	


				# Google  API shows our items in multiple pages when the number of files exceed page sizein json file
				page_token = picture_page.get('nextPageToken')

				if not page_token:
					break

			except Exception as error:
				print('An error has occurred:', error)				
				if item is not None: 
					print('File name: ', item['filename'])
				break

		# Increment the start date and reset. 
		start_date += day
		results = list(set(results))


	print("Yo!")
	if len(results) > 0:
		
		# Show the list of dates we've returned photos for. 
		print(results)

		# Update the config file to reflect the "new" sync date.... 
		config_data["last_sync_date"] = end_date.isoformat()
		
		# Save the last sync date back to the master config file. 
		with open(CONFIG_DIR + "/app_config.json", "w") as json_data_file:
			json.dump(config_data, json_data_file, indent=4, sort_keys=True)		
			
			




# Generator to loop through all albums
def getAlbums(session, appCreatedOnly=False):

    params = {
            'excludeNonAppCreatedData': appCreatedOnly
    }

    while True:

        albums = session.get('https://photoslibrary.googleapis.com/v1/albums', params=params).json()

        logging.debug("Server response: {}".format(albums))

        if 'albums' in albums:

            for a in albums["albums"]:
                yield a

            if 'nextPageToken' in albums:
                params["pageToken"] = albums["nextPageToken"]
            else:
                return

        else:
            return





def create_or_retrieve_album(session, album_title):

# Find albums created by this app to see if one matches album_title

    for a in getAlbums(session, True):
        if a["title"].lower() == album_title.lower():
            album_id = a["id"]
            logging.info("Uploading into EXISTING photo album -- \'{0}\'".format(album_title))
            return album_id

# No matches, create new album

    create_album_body = json.dumps({"album":{"title": album_title}})
    #print(create_album_body)
    resp = session.post('https://photoslibrary.googleapis.com/v1/albums', create_album_body).json()

    logging.debug("Server response: {}".format(resp))

    if "id" in resp:
        logging.info("Uploading into NEW photo album -- \'{0}\'".format(album_title))
        return resp['id']
    else:
        logging.error("Could not find or create photo album '\{0}\'. Server Response: {1}".format(album_title, resp))
        return None






def upload_photos(session, photo_file_list, album_name):

    album_id = create_or_retrieve_album(session, album_name) if album_name else None

    # interrupt upload if an upload was requested but could not be created
    if album_name and not album_id:
        return

    session.headers["Content-type"] = "application/octet-stream"
    session.headers["X-Goog-Upload-Protocol"] = "raw"

    for photo_file_name in photo_file_list:

            try:
                photo_file = open(photo_file_name, mode='rb')
                photo_bytes = photo_file.read()
            except OSError as err:
                logging.error("Could not read file \'{0}\' -- {1}".format(photo_file_name, err))
                continue

            session.headers["X-Goog-Upload-File-Name"] = os.path.basename(photo_file_name)

            logging.info("Uploading photo -- \'{}\'".format(photo_file_name))

            upload_token = session.post('https://photoslibrary.googleapis.com/v1/uploads', photo_bytes)

            if (upload_token.status_code == 200) and (upload_token.content):

                create_body = json.dumps({"albumId":album_id, "newMediaItems":[{"description":"","simpleMediaItem":{"uploadToken":upload_token.content.decode()}}]}, indent=4)

                resp = session.post('https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate', create_body).json()

                logging.debug("Server response: {}".format(resp))

                if "newMediaItemResults" in resp:
                    status = resp["newMediaItemResults"][0]["status"]
                    if status.get("code") and (status.get("code") > 0):
                        logging.error("Could not add \'{0}\' to library -- {1}".format(os.path.basename(photo_file_name), status["message"]))
                    else:
                        logging.info("Added \'{}\' to library and album \'{}\' ".format(os.path.basename(photo_file_name), album_name))
                else:
                    logging.error("Could not add \'{0}\' to library. Server Response -- {1}".format(os.path.basename(photo_file_name), resp))

            else:
                logging.error("Could not upload \'{0}\'. Server Response - {1}".format(os.path.basename(photo_file_name), upload_token))

    try:
        del(session.headers["Content-type"])
        del(session.headers["X-Goog-Upload-Protocol"])
        del(session.headers["X-Goog-Upload-File-Name"])
    except KeyError:
        pass


def main():


	global config_data

	if not os.path.isfile(CONFIG_DIR + "/app_config.json"):
		print("Error: config file (" + CONFIG_DIR + "/app_config.json) not found. ")
		print("creating template config file...")
		create_config_file()
		exit()
		

	# Look for the pre-configured search query....
	with open(CONFIG_DIR + "/app_config.json") as json_data_file:
		config_data = json.load(json_data_file)	

	print("Using config:", config_data)

	service = get_service()

	search_date_range(service)




# If the app config file doesn't exist, create a sample one, for the user to complete... 
def create_config_file():
	
	config_data = dict()
	
	config_data["credentials_file"] = "/path/to/file"
	config_data["download_dir"] = "/path/to/dir"
	config_data["dir_structure"] = "Y/M/D"
	config_data["last_sync_date"] = "2010-01-01"
	
	# Save the last sync date back to the master config file. 
	with open(CONFIG_DIR + "/app_config.json", "w") as json_data_file:
		json.dump(config_data, json_data_file, indent=4, sort_keys=True)		




if __name__ == '__main__':
	main()		
