if [ "$1" = "videoinput" ] ; then
redis-cli monitor |grep -i "xadd.*camera:0:videoinput" | pv -l --name dvmon_videoinput |grep dvmon_videoinput 
elif [ "$1" = "inferences" ] ; then
redis-cli monitor |grep -i "xadd.*camera:0:yolo" | pv -l --name dvmon_inference |grep dvmon_inference
else
    echo "Usage: streammetrics.sh videoinput|inferences"
fi
