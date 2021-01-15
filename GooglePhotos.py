#!/home/osmc/envs/google/bin/python3

from __future__ import print_function
import pickle
import requests
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import shutil
import json

import argparse

from datetime import date
from datetime import timedelta

#import pprint

from sleepingbunny import GoogleMail as gm


class GooglePhotos:


	# This access scope grants read-only access to the authenticated user's Photo Library
	SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
	API_SERVICE_NAME = 'photoslibrary'
	API_VERSION = 'v1'

	CONFIG_FILE_NAME = 'app_config.json'
	TOKEN_FILE_NAME = 'token.pickle'

	

	def __init__(self, user_name):

		self.config_dir = "config_" + user_name
		
		main_base = os.path.dirname(__file__)
		self.config_dir_name = os.path.join(main_base, self.config_dir)
		self.config_file = os.path.join(self.config_dir_name, self.CONFIG_FILE_NAME)	
				
		# check for config file... 
		if not os.path.isfile(self.config_file):
			print("Error: config file (" + self.config_file + ") not found. ")
			print("creating template config file...")
			self.create_config_file()
			exit()
			

		# Look for the pre-configured search query....
		with open(self.config_file) as json_data_file:
			self.config_data = json.load(json_data_file)	

		print("Using config:", self.config_data)		

		self.token_file = os.path.join(self.config_dir_name, self.TOKEN_FILE_NAME)			
		self.credentials_file = os.path.join(self.config_dir_name, self.config_data['credentials_file'])		
		
		self.get_service()

		self.processed_file_list = list()

		
	def get_service(self):
		""" Validates credentials and returns a service handle"""
		self.get_credentials()
		self.service= build(self.API_SERVICE_NAME, self.API_VERSION, credentials = self.creds)
		

		
	def get_credentials(self):
		"""Gets valid user credentials from storage.
		If nothing has been stored, or if the stored credentials are invalid,
		the OAuth2 flow is completed to obtain the new credentials.
		Returns:
			Credentials, the obtained credential.
		"""

		self.creds = None

		if os.path.exists(self.token_file):
			with open(self.token_file, 'rb') as token:
				self.creds = pickle.load(token)
			# If there are no (valid) credentials available, let the user log in.
		if not self.creds or not self.creds.valid:
			if self.creds and self.creds.expired and self.creds.refresh_token:
				self.creds.refresh(Request())
			else:
				flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, self.SCOPES)
				self.creds = flow.run_console()
		
		# Save the credentials for the next run
		with open(self.token_file, 'wb') as token:
			pickle.dump(self.creds, token)


		
		
	def download_file(self, item_dict):

		#print(self.config_data)

		target_dir = self.config_data.get('download_dir')
		
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
		
		self.processed_file_list.append('Downloading ' + filename + " " + item_dict['mediaMetadata']['creationTime'][0:10])  #+ ' (' + download_url + ')...')
		
		response = requests.get(download_url, stream=True)
			
		create_date= item_dict['mediaMetadata']['creationTime'][0:10]
		
		day = create_date[8:10]
		month = create_date[5:7]
		year = create_date[0:4]	
		
		
		if self.config_data.get("dir_structure") == None:
			raise RuntimeError('Directory Structure not specified in config file.')
			
		elif self.config_data.get("dir_structure") == 'Y/M/D':
		
			if not os.path.isdir(target_dir + '/' + year):
				os.mkdir(target_dir + '/' + year)
				
			if not os.path.isdir(target_dir + '/' + year + '/' + month):
				os.mkdir(target_dir + '/' + year + '/' + month)
				
			if not os.path.isdir(target_dir + '/' + year + '/' + month + '/' + day):
				os.mkdir(target_dir + '/' + year + '/' + month + '/' + day)
		
			target_path = target_dir + '/' + year + '/' + month + '/' + day
		
		elif self.config_data.get('dir_structure') == 'YMD':
			
			targetpath = target_dir + '/' + year +  month + day
		
		else:
		
			raise RuntimeError('Unknown Directory Structure specified in config file.')
		
		
		with open(target_path + '/' + filename, 'wb') as out_file:
			# print(response.raw)
			shutil.copyfileobj(response.raw, out_file)	





	# Build a formatted date dictionary for the search query. 
	def date_to_dict(self, the_date):
		
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



	def build_filter(self, date, page_size = 100):
		
		date_dict = self.date_to_dict(date)
			
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
	def search_date_range(self):

		self.processed_file_list.append('last sync date: ' + self.config_data['last_sync_date'])
		
		
		# Read the last sync date from the config file; use this as the start date. 
		last_sync_date_parts = self.config_data["last_sync_date"].split("-")
		start_date = date(int(last_sync_date_parts[0]), int(last_sync_date_parts[1]), int(last_sync_date_parts[2]))

		# Single day offset... 
		day = timedelta(days=1)
		end_date = date.today() - day

		results = list()

		while start_date < end_date:

			print("start date: ", start_date, " end date:", start_date + day)
			self.processed_file_list.append('start date: ' + start_date.isoformat() + '; end date: ' + (start_date + day).isoformat())
			
			
			# Build the filter object, including date range. 
			filter = self.build_filter(start_date)
			
			page_token = None

			while True:
				try:

					if page_token:
						filter['pageToken'] = page_token

					picture_page = self.service.mediaItems().search(body=filter).execute()

					items = picture_page.get('mediaItems', [])
					
					if not items:
						print('No items found.')
						
					else:
						
						print ("Found ", len(items), " items!")
						
						for item in items:
							
							create_date= item['mediaMetadata']['creationTime'][0:10]
							
							#print(create_date)
							
							results.append(create_date)
							self.download_file(item)	


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
							
			max_val = max(results)
			max_val_parts = max_val.split('-')

			max_date = date(int(max_val_parts[0]), int(max_val_parts[1]), int(max_val_parts[2]))

			# Update the config file to reflect the "new" sync date.... 
			self.config_data["last_sync_date"] = max_date.isoformat()

			self.processed_file_list.append('new max date: ' + max_date.isoformat())
			
			# Save the last sync date back to the master config file. 
			with open(self.config_file, "w") as json_data_file:
				json.dump(self.config_data, json_data_file, indent=4, sort_keys=True)		


			mailer = gm.GoogleMail()

			msg = mailer.create_message('stewarg9@yahoo.co.uk',"Test Email",("\n").join(self.processed_file_list))			
			
			mailer.send_message(msg, user_id = 'me')			



	# If the app config file doesn't exist, create a sample one, for the user to complete... 
	def create_config_file():
		
		config_data = dict()
		
		config_data["credentials_file"] = "/path/to/file"
		config_data["download_dir"] = "/path/to/dir"
		config_data["dir_structure"] = "Y/M/D"
		config_data["last_sync_date"] = "2010-01-01"
		
		# Save the last sync date back to the master config file. 
		with open(self.config_file, "w") as json_data_file:
			json.dump(config_data, json_data_file, indent=4, sort_keys=True)		


				
def main(user_name):


	photos = GooglePhotos(user_name=user_name)

	photos.search_date_range()



if __name__ == '__main__':

	parser = argparse.ArgumentParser()

	parser.add_argument("-u", "--user_name", help="user to extract photos for", default="gareth")

	args = parser.parse_args()   
	
	main(args.user_name)		
