#!/usr/bin/env python

import argparse
import base64

from PIL import Image
from PIL import ImageDraw

from googleapiclient import discovery
import httplib2
from oauth2client.client import GoogleCredentials


import pprint
import os
import json
import subprocess
import glob

import django
from django.template import loader, Template, Context
from django.conf import settings
from time import sleep
import multiprocessing

settings.configure(TEMPLATE_DIRS=('/home/sushobhan.nayak/scripts//templates',))
django.setup()

# Task feature dictionaries
MAX_RESULTS = 10
features = {}
#features['face_detection'] = {'type': 'FACE_DETECTION', 'maxResults': MAX_RESULTS}
features['landmark_detection'] = {'type': 'LANDMARK_DETECTION', 'maxResults': MAX_RESULTS}
features['logo_detection'] = {'type': 'LOGO_DETECTION', 'maxResults': MAX_RESULTS}
features['label_detection'] = {'type': 'LABEL_DETECTION', 'maxResults': MAX_RESULTS}
features['ocr'] = {'type': 'TEXT_DETECTION', 'maxResults': MAX_RESULTS}
features['safe_search'] = {'type': 'SAFE_SEARCH_DETECTION', 'maxResults': MAX_RESULTS}
features['properties'] = {'type': 'IMAGE_PROPERTIES', 'maxResults': MAX_RESULTS}



# [START get_vision_service]
DISCOVERY_URL='https://{api}.googleapis.com/$discovery/rest?version={apiVersion}'


def get_vision_service():
    credentials = GoogleCredentials.get_application_default()
    return discovery.build('vision', 'v1', credentials=credentials,
                           discoveryServiceUrl=DISCOVERY_URL)
# [END get_vision_service]

# [START highlight_faces]
def highlight_faces(image, faces, output_filename):
    """Draws a polygon around the faces, then saves to output_filename.

    Args:
      image: a file containing the image with the faces.
      faces: a list of faces found in the file. This should be in the format
          returned by the Vision API.
      output_filename: the name of the image file to be created, where the faces
          have polygons drawn around them.
    """
    image.seek(0)
    im = Image.open(image)
    draw = ImageDraw.Draw(im)

    if faces:
        for face in faces:
            box = [(v.get('x', 0.0), v.get('y', 0.0)) for v in face['fdBoundingPoly']['vertices']]
            draw.line(box + [box[0]], width=5, fill='#00ff00')

    del draw
    im.save(output_filename)
# [END highlight_faces]


def draw_rectangle(draw, response, item_str, color='#00ff00', index_str='boundingPoly'):
    items = response['responses'][0].get(item_str, None)
    if items:
        for item in items:
            box = [(v.get('x', 0.0), v.get('y', 0.0)) for v in item[index_str]['vertices']]
            draw.line(box + [box[0]], width=5, fill=color)
    
def highlight_image(image, response, output_folder, tasks):
    image.seek(0)
    im = Image.open(image)
    im.save(output_folder + '/original_image.jpg')
    draw = ImageDraw.Draw(im)

    #if 'all' in tasks or 'face_detection' in tasks:
     #   draw_rectangle(draw, response, 'faceAnnotations', '#00ff00', 'fdBoundingPoly')
    if 'all' in tasks or 'landmark_detection' in tasks:
        draw_rectangle(draw, response, 'landmarkAnnotations', '#7cedff')
    if 'all' in tasks or 'logo_detection' in tasks:
        draw_rectangle(draw, response, 'logoAnnotations', '#ff00ff')
    if 'all' in tasks or 'ocr' in tasks:
        draw_rectangle(draw, response, 'textAnnotations', '#0000ff')

    del draw
    im.save(output_folder + '/edited_image.jpg')


def update_data(data, key, key_string, response):
    try:
        data[key] = [x['description'] for x in response['responses'][0].get(key_string, [])]
    except:
        pass

def log_metadata(response, output_folder):
    json.dump(response, open(output_folder + '/result.json', 'w'))
    data = {}
    update_data(data, 'labels', 'labelAnnotations', response)
    #data['faces'] = len(response['responses'][0].get('faceAnnotations', []))
    update_data(data, 'landmarks', 'landmarkAnnotations', response)
    update_data(data, 'logos', 'logoAnnotations', response)
    try:
        data['primary_text'] = [x['description'] for x in response['responses'][0].get('textAnnotations', [{'description':''}])][0]
    except:
        pass
    json.dump(data, open(output_folder + '/selective.json', 'w'))

def process_image_batch(batch_id, image_file_list, service, output_file_path, tasks=['all']):
    # Batch process input images

    batch_request = []
    for image_file in image_file_list:
        if image_file.split('.')[-1].lower() not in ['jpg', 'jpeg', 'png']:
            print "Can't operate on this file extension... Giving up"
            return
    
        max_results = 10
        with open(image_file, 'rb') as image:
            _features = []
            if 'all' in tasks:
                _features = [v for k,v in features.items()]
            else:
                for task in tasks:
                    _features.append(features[task])
            image_content = image.read()
            batch_request.append({
                'image': {
                    'content': base64.b64encode(image_content).decode('UTF-8')
                },
            'features': _features
            })
        

    request = service.images().annotate(body={'requests': batch_request})
    response = request.execute()

    # Pause for 1 second before next post
    sleep(1)

    # pprint.pprint(response)
    
    output_folder = output_file_path + '/_processed_image_' + ''.join(str(batch_id))
    
    print "Analysis results in folder: ", output_folder
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Save metadata
    log_metadata(response, output_folder)

    # Save image list
    json.dump(image_file_list, open(output_folder + '/images.json', 'w'))


def process_image(image_file, service, output_file_path, tasks=['all']):
    if image_file.split('.')[-1].lower() not in ['jpg', 'jpeg', 'png']:
        print "Can't operate on this file extension... Giving up"
        return
    max_results = 10
    with open(image_file, 'rb') as image:
        _features = []
        if 'all' in tasks:
            _features = [v for k,v in features.items()]
        else:
            for task in tasks:
                _features.append(features[task])
        image_content = image.read()
        batch_request = [{
            'image': {
                'content': base64.b64encode(image_content).decode('UTF-8')
            },
            'features': _features
        }]
        

        request = service.images().annotate(body={'requests': batch_request})
        response = request.execute()
        # pprint.pprint(response)
        
        output_folder = output_file_path + '/_processed_image_' + ''.join(image_file.split('/')[-1].split('.')[:-1])
        print "Analysis results in folder: ", output_folder
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        log_metadata(response, output_folder)
        # highlight_image(image, response, output_folder, tasks)

def extract_keyframes_pool(pool_param):
    # Pool param
    (video_file, output_file_path) = pool_param
    return extract_keyframes(video_file, output_file_path)

def extract_keyframes(video_file, output_file_path):
    # Extract keyframes and return their path as a list
    video_name = video_file.split('/')[-1].split('.')[:-1]
    output_folder = output_file_path + '/_processed_video_' + ''.join(video_name)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Sample based on keyframes
    cmd = '/home/a-kunduan/Research/3rd-party/FFmpeg_build/bin/ffmpeg -ss 0 -i ' + \
            video_file + \
            ' -q:v 2 -vf select="eq(pict_type\,PICT_TYPE_I)" -vsync 0 ' + \
            output_folder + \
            '/' + \
            ''.join(video_name) + \
            '-frame-%d.jpeg'
    print cmd
    subprocess.call(cmd, shell=True)

    # Create frame list
    image_list = []
    for path in os.listdir(output_folder):
        input_file_path = output_folder + '/' + path
        if os.path.isfile(input_file_path):
            image_list.append(input_file_path)

    return image_list


def process_video(video_file, service, output_file_path, tasks=['all']):
    # Sample video and dispatch image file. 
    video_name = video_file.split('/')[-1].split('.')[:-1]
    output_folder = output_file_path + '/_processed_video_' + ''.join(video_name)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Sample based on fps
    # cmd = 'ffmpeg -i '+ video_file + ' -vf fps=1 '+ output_folder + '/image-%d.jpeg'
    # Sample based on keyframes
    cmd = 'ffmpeg -ss 0 -i ' + video_file + ' -q:v 2 -vf select="eq(pict_type\,PICT_TYPE_I)" -vsync 0 ' + output_folder + '/' + video_name + '-frame-%d.jpeg'
    os.system(cmd)
    # subprocess.call(cmd, shell=True)

    # Create image batch
    image_batch = []
    for path in os.listdir(output_folder):
        input_file_path = output_folder + '/' + path
        if os.path.isfile(input_file_path):
            image_batch.append(input_file_path)
            # dispatch_file(input_file_path, service, output_folder)

    # Batch process frames
    process_image_batch(video_name, image_batch, service, output_folder)

    subprocess.call('cp '+video_file+ ' ' + output_folder, shell=True)

def dispatch_file(input_file_path, service, output_file_path, tasks=['all']):
    print "processing file: ", input_file_path
    file_ext = input_file_path.split('.')[-1].lower()
    if file_ext in ['jpg', 'jpeg', 'png']:
        process_image(input_file_path, service, output_file_path)
    elif file_ext in ['mp4']:
        process_video(input_file_path, service, output_file_path)
    else:
        print "Can't operate on this file extension... Giving up"

def process_html(folder_path):
    block_template = loader.get_template('block.html')
    block_html = []

    video_folders = glob.glob(folder_path + '/_processed_video_*')
    image_folders = glob.glob(folder_path + '/_processed_image_*')
    print "Creating html with processed video and image folders: "
    print video_folders
    print image_folders

    for video_folder in video_folders:
        is_adult = False
        video_folder = os.path.abspath(video_folder)
        file_name = video_folder.split('_processed_video_')[-1]
        tags = "" if not os.path.isfile(video_folder + '/tags.data') else open(video_folder + '/tags.data').readline()
        query_media = [video_folder + '/' + file_name + '.mp4', 'mp4', tags]
        match_media_list = []
        images = glob.glob(video_folder + '/_processed_image_*')
        for image in images:
            if image.split('-')[-1] not in ['1', '4', '7']:
                continue
            data = json.load(open(image + '/selective.json'))
            data_dict = {}
            if 'primary_text' in data and len(data['primary_text']) > 0:
                data_dict['text: '] = data['primary_text'].encode('ascii', 'ignore')
            if 'logos' in data and len(data['logos']) > 0:
                data_dict['logo: '] = str(data['logos']) 
            if 'landmarks' in data and len(data['landmarks']) > 0:
                data_dict['landmarks: '] = str(data['landmarks']) 
            if 'labels' in data and len(data['labels']) > 0:
                data_dict['labels: '] = str(data['labels']) 
            all_data = json.load(open(image + '/all.json'))
            if 'safeSearchAnnotation' in all_data['responses'][0]:
                data_dict['safeSearchAnnotation'] = str(all_data['responses'][0]['safeSearchAnnotation'])
                if all_data['responses'][0]['safeSearchAnnotation']['adult'] == 'POSSIBLE':
                    is_adult = True

            match_media_list.append((image+'/edited_image.jpg', 'jpg', data_dict))
        block_context = Context( {"query_media": query_media,
                                  "match_media_list": match_media_list})
        if not is_adult:
            block_html.append(block_template.render(block_context))

    for image_folder in image_folders:
        image_folder = os.path.abspath(image_folder)
        query_media = [image_folder + '/original_image.jpg', 'jpg']
        match_media_list = [(image_folder + '/edited_image.jpg', 'jpg', str(json.load(open(image_folder + '/selective.json'))))]
        block_context = Context( {"query_media": query_media,
                                  "match_media_list": match_media_list})
        block_html.append(block_template.render(block_context))

        
    with open(folder_path + '/result.html', 'w') as fw:
        fw.write('\n'.join(block_html))
            
        

def main(input_file_path, output_file_path, input_file_list=None, frame_dir=None):
    processed_videos = [x.split('/')[-1].split('_processed_video_')[-1] for x in glob.glob(output_file_path+"/_processed_video_*")]
    processed_images = [x.split('/')[-1].split('_processed_image_')[-1] for x in glob.glob(output_file_path+"/_processed_image_*")]
    service = get_vision_service()
    if os.path.isfile(input_file_path):
        dispatch_file(input_file_path, service, output_file_path)
        pass
    elif os.path.isdir(input_file_path):
        print 'processing folder: ', input_file_path
        
        input_image_list = []
        pool_arr = []

        do_extract_frames = False

        if input_file_list is not None:
            # Read file names from filelist
            with open(input_file_list) as f:
                data = f.read()
                rows = data.split('\n')

                if rows[-1] == '':
                    rows.pop()

                for row in rows:
                    input_file = input_file_path + '/' + row
                    file_ext = input_file.split('.')[-1].lower()
                    if file_ext in ['jpg', 'jpeg', 'png']:
                        input_image_list.append(input_file)
                    elif file_ext in ['mp4'] and frame_dir is not None:
                        pool_arr.append((input_file, frame_dir))
                    pass
        
        if do_extract_frames and pool_arr:
            # Multiprocess frame extraction
            pool = multiprocessing.Pool()
            results = pool.map(extract_keyframes_pool, pool_arr)
            pool.close()
            pool.join()

            # Expand image list with extracted frames
            for result in results:
                input_image_list.extend(result)
        elif (not do_extract_frames) and frame_dir is not None:
             # Assume frames are ready
             for path in os.listdir(frame_dir):
                 subdir_path = frame_dir + '/' + path
                 if os.path.isdir(subdir_path):
                     for image_name in os.listdir(subdir_path):
                         image_path = subdir_path + '/' + image_name
                         if os.path.isfile(image_path):
                             input_image_list.append(image_path)

        # Divide image list into batches
        image_batch_list = []
        batch_size = 10
        for k in range(0, len(input_image_list), batch_size):
            image_batch_list.append(input_image_list[k:min(k+batch_size , len(input_image_list))])

        batch_id = 0
        for image_batch in image_batch_list:

            # if batch_id < 17779:
            #     batch_id = batch_id + 1
            #     continue

            print image_batch
            process_image_batch(batch_id, image_batch, service, output_file_path)
            batch_id = batch_id + 1
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Detects Vision API routines on the given image or video. If it is a video, samples two images per second. ')
    parser.add_argument(
        'input_path', help='the image you\'d like to detect faces in.')
    parser.add_argument(
        '--out', dest='output', default=os.getcwd(),
        help='the name of the output file.')
    parser.add_argument(
        '--list', dest='filelist', default=None,
            )
    parser.add_argument(
        '--frames', dest='frame_dir', default=None,
            )
    parser.add_argument(
        '--html_only', dest='html_only', default=False,
        help='use this if you only want to process the outputs for html')
    args = parser.parse_args()
    
    if not (args.html_only):
        main(args.input_path, args.output, args.filelist, args.frame_dir)
    # process_html(args.output)
