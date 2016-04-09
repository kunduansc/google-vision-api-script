# google-vision-api-script
```
usage: process_snaps.py [-h] [--out OUTPUT] input_path
```

The `input_path` can be a path to a image or video file or a folder containing a bunch of them. 

Please see the `requirement.txt` file for packages you need installed before Google visionAPI can run.

You need to have `ffmpeg` installed to run this script if video processing is required. It samples the video every 1 sec to extract an image and run vision api on that image.

Look in the `test` folder for an example run.
