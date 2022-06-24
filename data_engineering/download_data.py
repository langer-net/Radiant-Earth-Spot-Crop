import os,sys
import numpy as np 
import pandas as pd
import tarfile,json
from pathlib import Path
from radiant_mlhub.client import _download as download_file
from collections import OrderedDict

os.environ['MLHUB_API_KEY'] = 'N/A'
OUTPUT_DIR = './data'

FOLDER_BASE = 'ref_south_africa_crops_competition_v1'
DOWNLOAD_S1 = False # If you set this to true then the Sentinel-1 data will be downloaded
# Select which Sentinel-2 imagery bands you'd like to download here. 
DOWNLOAD_S2 = OrderedDict({
    'B01': False,
    'B02': True, #Blue
    'B03': True, #Green
    'B04': True, #Red
    'B05': False,
    'B06': False,
    'B07': False,
    'B08': True, #NIR
    'B8A': False, #NIR2
    'B09': False,
    'B11': True, #SWIR1
    'B12': True, #SWIR2
    'CLM': True
})

# Set the directories
OUTPUT_DIR = f'{OUTPUT_DIR}/train'
os.makedirs(OUTPUT_DIR,exist_ok=True)
OUTPUT_DIR_BANDS = f'{OUTPUT_DIR}/bands-raw' 
os.makedirs(OUTPUT_DIR_BANDS,exist_ok=True)
# Change the working directory
os.chdir(f'{OUTPUT_DIR}')

# Download the data
def download_archive(archive_name):
    if os.path.exists(archive_name.replace('.tar.gz', '')):
        return
    
    print(f'Downloading {archive_name} ...')
    download_url = f'https://radiant-mlhub.s3.us-west-2.amazonaws.com/archives/{archive_name}'
    download_file(download_url, '.')
    print(f'Extracting {archive_name} ...')
    with tarfile.open(archive_name) as tfile:
        tfile.extractall()
    os.remove(archive_name)

for split in ['train']:
    # # Download the labels
    labels_archive = f'{FOLDER_BASE}_{split}_labels.tar.gz'
    download_archive(labels_archive)
    
    ##Download Sentinel-1 data
    if DOWNLOAD_S1:
        s1_archive = f'{FOLDER_BASE}_{split}_source_s1.tar.gz'
        download_archive(s1_archive)

    for band, download in DOWNLOAD_S2.items():
        if not download:
            continue
        s2_archive = f'{FOLDER_BASE}_{split}_source_s2_{band}.tar.gz'
        download_archive(s2_archive)
print('Finished downloading the data!')

# Load the data to a dataframe
def resolve_path(base, path):
    return Path(os.path.join(base, path)).resolve()
        
def load_df(collection_id):
    split = collection_id.split('_')[-2]
    collection = json.load(open(f'{collection_id}/collection.json', 'r'))
    rows = []
    item_links = []
    for link in collection['links']:
        if link['rel'] != 'item':
            continue
        item_links.append(link['href'])
        
    for item_link in item_links:
        item_path = f'{collection_id}/{item_link}'
        current_path = os.path.dirname(item_path)
        item = json.load(open(item_path, 'r'))
        tile_id = item['id'].split('_')[-1]
        for asset_key, asset in item['assets'].items():
            rows.append([
                tile_id,
                None,
                None,
                asset_key,
                str(resolve_path(current_path, asset['href']))
            ])
            
        for link in item['links']:
            if link['rel'] != 'source':
                continue
            source_item_id = link['href'].split('/')[-2]
            
            if source_item_id.find('_s1_') > 0 and not DOWNLOAD_S1:
                continue
            elif source_item_id.find('_s1_') > 0:
                for band in ['VV', 'VH']:
                    asset_path = Path(f'{FOLDER_BASE}_{split}_source_s1/{source_item_id}/{band}.tif').resolve()
                    date = '-'.join(source_item_id.split('_')[10:13])
                    
                    rows.append([
                        tile_id,
                        f'{date}T00:00:00Z',
                        's1',
                        band,
                        asset_path
                    ])
                
            if source_item_id.find('_s2_') > 0:
                for band, download in DOWNLOAD_S2.items():
                    if not download:
                        continue

                    asset_path = Path(f'{FOLDER_BASE}_{split}_source_s2_{band}/{source_item_id}_{band}.tif').resolve()
                    date = '-'.join(source_item_id.split('_')[10:13])
                    rows.append([
                        tile_id,
                        f'{date}T00:00:00Z',
                        's2',
                        band,
                        asset_path
                    ])

    return pd.DataFrame(rows, columns=['tile_id', 'datetime', 'satellite_platform', 'asset', 'file_path'])

df_train = load_df(f'{FOLDER_BASE}_train_labels')

# Save the data into a csv file
folder_path = '/Users/maxlanger/neuefische/Radiant-Earth-Spot-Crop/'
df_train['file_path'] = df_train['file_path'].str.replace(folder_path, './data/')
df_train.to_csv('train_data.csv', index=False)

# Change the working directory
os.chdir('../')