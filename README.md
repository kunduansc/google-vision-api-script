# google-vision-api-script
```
usage: process_snaps.py [-h] [--out OUTPUT] input_path
```

The input path can be a path to a image or video file or a folder containing a bunch of them. 


You need to have **ffmpeg** installed to run this script if video processing is required. It samples the video every 0.5 sec to extract an image and run vision api on that image.
