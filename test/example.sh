rm -rf _processed_video_*
rm -rf _processed_image_*
time python ../process_snaps.py .
echo "Result is in result.html"
